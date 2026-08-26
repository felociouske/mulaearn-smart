"""
One-time backfill for the currency-conversion bug: DepositRequest.approve()
and WithdrawalRequest.approve() used to pass `self.amount` (the LOCAL
currency amount) straight into wallet.credit()/debit() with no conversion,
so every already-APPROVED non-Kenya deposit/withdrawal moved the wallet
by the wrong, unconverted number.

This does NOT re-credit the correct amount from scratch (that would
double-count what was already applied). For each affected row it computes
the DELTA between what should have happened and what actually happened,
and applies just that delta — via wallet.credit()/debit() with
transaction_type=ADMIN_ADJUSTMENT, so it shows up in each user's ledger
as a clearly-labeled correction, not a mystery balance jump.

SAFE TO RE-RUN: before touching a row, it checks whether a Transaction
with that row's exact correction description already exists on the
wallet, and skips it if so. Running this twice does not double-apply.

USAGE:
  python manage.py fix_currency_backfill              # dry run — prints what WOULD change, touches nothing
  python manage.py fix_currency_backfill --apply       # actually applies the corrections

Dry-run is the default on purpose — this moves real money in a live
database, and a preview you can read before committing is worth the one
extra flag. Not defiance of "go ahead and write it", just do it once with
--apply when the printed report looks right.

KNOWN LIMITATION: the correction uses request.user.country — i.e. the
user's CURRENT country/exchange rate — not whatever country they were in
at the time of the original deposit/withdrawal. If a user has since
switched countries, or a country's exchange_rate_to_kes has been edited
in admin since the original request, the "corrected" amount uses
TODAY's rate, not the rate that was actually in effect back then. This
mirrors the same assumption the live approve() fix makes (there's no
per-request Country FK stored, only a currency_code string snapshot) —
it's the best available approximation, not a perfect historical
reconstruction. If your exchange rates have moved a lot since these
requests were approved, review the printed report closely before
running with --apply.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.management.base import BaseCommand
from django.db import transaction as db_transaction

from payment.models import DepositRequest, RequestStatus, WithdrawalRequest
from wallets.models import Transaction


class Command(BaseCommand):
    help = "Backfill wallet balances for deposits/withdrawals approved before the currency-conversion fix. Dry-run by default — pass --apply to actually change balances."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply", action="store_true",
            help="Actually apply the corrections. Without this flag, only a preview is printed and nothing is changed.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        mode_label = "APPLYING" if apply_changes else "DRY RUN (pass --apply to actually change balances)"
        self.stdout.write(self.style.WARNING(f"\n=== Currency backfill — {mode_label} ===\n"))

        deposit_summary = self._process_deposits(apply_changes)
        withdrawal_summary = self._process_withdrawals(apply_changes)

        self.stdout.write("\n=== Summary ===")
        for label, summary in [("Deposits", deposit_summary), ("Withdrawals", withdrawal_summary)]:
            self.stdout.write(
                f"{label}: {summary['corrected']} corrected, {summary['already_done']} already fixed "
                f"(skipped), {summary['no_change']} needed no change, {summary['skipped_no_country']} "
                f"skipped (no country on file), {summary['failed']} FAILED — see above"
            )
        if not apply_changes:
            self.stdout.write(self.style.WARNING("\nNothing was changed — this was a dry run. Re-run with --apply to commit these corrections."))
        else:
            self.stdout.write(self.style.SUCCESS("\nDone. Corrections applied and recorded as admin_adjustment transactions."))

    def _process_deposits(self, apply_changes):
        summary = {"corrected": 0, "already_done": 0, "no_change": 0, "skipped_no_country": 0, "failed": 0}
        deposits = DepositRequest.objects.filter(status=RequestStatus.APPROVED).select_related("user", "user__country")

        for deposit in deposits:
            country = deposit.user.country
            if not country:
                summary["skipped_no_country"] += 1
                continue

            # What was actually credited at the time (the bug: raw local-
            # currency number, uncoverted) vs what should have been credited.
            wrongly_applied = deposit.amount
            correct_kes = country.convert_to_kes(deposit.amount)
            delta = correct_kes - wrongly_applied

            description = f"Currency-fix backfill for deposit #{deposit.id}"

            if delta == 0:
                summary["no_change"] += 1
                continue

            if Transaction.objects.filter(wallet=deposit.user.wallet, description=description).exists():
                summary["already_done"] += 1
                continue

            self.stdout.write(
                f"  Deposit #{deposit.id} ({deposit.user.username}, {wrongly_applied} {deposit.currency_code}): "
                f"was credited {wrongly_applied} KES-worth, should have been {correct_kes} KES -> delta {delta:+}"
            )

            if apply_changes:
                try:
                    with db_transaction.atomic():
                        if delta > 0:
                            deposit.user.wallet.credit(
                                wallet_type="deposit", amount=delta,
                                transaction_type=Transaction.TransactionType.ADMIN_ADJUSTMENT,
                                description=description,
                            )
                        else:
                            deposit.user.wallet.debit(
                                wallet_type="deposit", amount=abs(delta),
                                transaction_type=Transaction.TransactionType.ADMIN_ADJUSTMENT,
                                description=description,
                            )
                    summary["corrected"] += 1
                except DjangoValidationError as e:
                    summary["failed"] += 1
                    self.stdout.write(self.style.ERROR(f"    FAILED to correct deposit #{deposit.id}: {e}"))
            else:
                summary["corrected"] += 1  # counted as "would be corrected" in dry-run

        return summary

    def _process_withdrawals(self, apply_changes):
        summary = {"corrected": 0, "already_done": 0, "no_change": 0, "skipped_no_country": 0, "failed": 0}
        withdrawals = WithdrawalRequest.objects.filter(status=RequestStatus.APPROVED).select_related("user", "user__country")

        for withdrawal in withdrawals:
            country = withdrawal.user.country
            if not country:
                summary["skipped_no_country"] += 1
                continue

            wrongly_applied = withdrawal.amount  # what was actually debited
            correct_kes = country.convert_to_kes(withdrawal.amount)
            # Withdrawals are the mirror image of deposits: if the user was
            # over-debited (wrongly_applied > correct_kes, the common case),
            # we owe them the difference back — a CREDIT. If under-debited
            # (rare), we need to debit the extra, which can fail if they've
            # since spent the balance down — see the try/except below.
            delta_to_credit_back = wrongly_applied - correct_kes

            description = f"Currency-fix backfill for withdrawal #{withdrawal.id}"

            if delta_to_credit_back == 0:
                summary["no_change"] += 1
                continue

            if Transaction.objects.filter(wallet=withdrawal.user.wallet, description=description).exists():
                summary["already_done"] += 1
                continue

            self.stdout.write(
                f"  Withdrawal #{withdrawal.id} ({withdrawal.user.username}, {wrongly_applied} {withdrawal.currency_code}): "
                f"was debited {wrongly_applied} KES-worth, should have been {correct_kes} KES -> owed back {delta_to_credit_back:+}"
            )

            if apply_changes:
                try:
                    with db_transaction.atomic():
                        if delta_to_credit_back > 0:
                            withdrawal.user.wallet.credit(
                                wallet_type=withdrawal.wallet_type, amount=delta_to_credit_back,
                                transaction_type=Transaction.TransactionType.ADMIN_ADJUSTMENT,
                                description=description,
                            )
                        else:
                            # Under-debited originally — needs an extra debit now.
                            # Can fail if the user's balance can't cover it; that's
                            # reported, not silently swallowed, since it needs a
                            # human decision (write it off? chase the user?).
                            withdrawal.user.wallet.debit(
                                wallet_type=withdrawal.wallet_type, amount=abs(delta_to_credit_back),
                                transaction_type=Transaction.TransactionType.ADMIN_ADJUSTMENT,
                                description=description,
                            )
                    summary["corrected"] += 1
                except DjangoValidationError as e:
                    summary["failed"] += 1
                    self.stdout.write(self.style.ERROR(f"    FAILED to correct withdrawal #{withdrawal.id}: {e}"))
            else:
                summary["corrected"] += 1

        return summary