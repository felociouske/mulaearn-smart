from decimal import Decimal

from django.conf import settings
from django.db import models, transaction
from django.core.exceptions import ValidationError


class Wallet(models.Model):
    """
    One wallet per user, holding the four balances you described:

      - deposit_balance : money the user has deposited (used to buy/upgrade plans)
      - account_balance  : earnings from chats + minor tasks (surveys, videos, etc.)
      - yield_balance     : referral commission earnings
      - total_yield_earned: LIFETIME sum of every credit ever earned (chat + tasks +
                            referrals). This never decreases, even when the user
                            withdraws — it's the "Total Yield" display stat, not a
                            spendable balance.

    All four columns live on the same row (not four separate wallet rows) so a
    single Transaction can be written per event without needing cross-row locks
    most of the time.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet")

    deposit_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    account_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    yield_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_yield_earned = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet<{self.user.username}>"

    # --- Balance mutation helpers -----------------------------------------
    # Every balance change MUST go through one of these, never by editing
    # deposit_balance/account_balance/yield_balance directly elsewhere in the
    # codebase. That's what guarantees a Transaction row exists for every
    # single KES that moves, which you'll need for support disputes
    # ("why haven't I been paid?" is literally in your FAQ list).

    @transaction.atomic
    def credit(self, wallet_type, amount, transaction_type, description="", related_object=None):
        """
        Add `amount` to the given wallet_type ("deposit", "account", or "yield")
        and record a Transaction. Earning-type credits also bump
        total_yield_earned; deposits do not (a deposit isn't something you
        "earned" from the site).
        """
        if amount <= 0:
            raise ValidationError("Credit amount must be positive — use debit() to remove funds.")

        # select_for_update locks this wallet's row until the transaction commits,
        # so two simultaneous chat messages (or a chat message + a withdrawal
        # request) can't read-modify-write the same balance and lose an update.
        wallet = Wallet.objects.select_for_update().get(pk=self.pk)

        field_name = _wallet_field(wallet_type)
        setattr(wallet, field_name, getattr(wallet, field_name) + amount)

        if transaction_type in Transaction.EARNING_TYPES:
            wallet.total_yield_earned += amount

        wallet.save(update_fields=[field_name, "total_yield_earned", "updated_at"])

        Transaction.objects.create(
            wallet=wallet,
            wallet_type=wallet_type,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=getattr(wallet, field_name),
            description=description,
        )

        self.refresh_from_db()
        return wallet

    @transaction.atomic
    def debit(self, wallet_type, amount, transaction_type, description=""):
        """
        Remove `amount` from the given wallet_type. Raises ValidationError
        instead of allowing a negative balance — e.g. a withdrawal request
        for more than the user has must be rejected at this layer, not just
        at the API layer, so it's impossible to bypass by calling this
        method directly from the admin or a management command.
        """
        if amount <= 0:
            raise ValidationError("Debit amount must be positive.")

        wallet = Wallet.objects.select_for_update().get(pk=self.pk)
        field_name = _wallet_field(wallet_type)
        current = getattr(wallet, field_name)

        if current < amount:
            raise ValidationError(
                f"Insufficient {wallet_type} balance: has {current}, tried to debit {amount}."
            )

        setattr(wallet, field_name, current - amount)
        wallet.save(update_fields=[field_name, "updated_at"])

        Transaction.objects.create(
            wallet=wallet,
            wallet_type=wallet_type,
            transaction_type=transaction_type,
            amount=-amount,  # stored negative so a wallet's transaction history sums to its balance
            balance_after=getattr(wallet, field_name),
            description=description,
        )

        self.refresh_from_db()
        return wallet


def _wallet_field(wallet_type):
    mapping = {
        "deposit": "deposit_balance",
        "account": "account_balance",
        "yield": "yield_balance",
    }
    if wallet_type not in mapping:
        raise ValidationError(f"Unknown wallet_type '{wallet_type}'. Must be one of {list(mapping)}.")
    return mapping[wallet_type]


class Transaction(models.Model):
    """
    Immutable ledger row — one per credit or debit, ever. This is the audit
    trail behind every balance, and it's what "Total Yield" and every
    "why haven't I been paid" support question gets answered from.
    """

    class WalletType(models.TextChoices):
        DEPOSIT = "deposit", "Deposit Wallet"
        ACCOUNT = "account", "Account Balance"
        YIELD = "yield", "Yield Wallet"

    class TransactionType(models.TextChoices):
        DEPOSIT_MANUAL = "deposit_manual", "Manual deposit (admin-approved)"
        DEPOSIT_AUTOMATIC = "deposit_automatic", "Automatic deposit (Daraja)"
        WITHDRAWAL = "withdrawal", "Withdrawal"
        CHAT_EARNING = "chat_earning", "Chat earning"
        SURVEY_EARNING = "survey_earning", "Survey earning"
        WHEEL_EARNING = "wheel_earning", "Wheel spin earning"
        APP_REVIEW_EARNING = "app_review_earning", "App review earning"
        MOVIE_REVIEW_EARNING = "movie_review_earning", "Movie review earning"
        REFERRAL_COMMISSION = "referral_commission", "Referral commission"
        PLAN_PURCHASE = "plan_purchase", "Plan purchase"
        ADMIN_ADJUSTMENT = "admin_adjustment", "Admin adjustment"
        LOAN_PLAN_PURCHASE = "loan_plan_purchase", "Loan plan purchase"
        LOAN_DISBURSEMENT = "loan_disbursement", "Loan disbursement"
        REFUND = "refund", "Refund"

    # Credits that count toward the lifetime "Total Yield" figure. Deposits,
    # withdrawals, plan purchases, refunds, and admin adjustments do NOT —
    # those move money in/out but aren't something the user "earned".
    EARNING_TYPES = {
        TransactionType.CHAT_EARNING,
        TransactionType.SURVEY_EARNING,
        TransactionType.WHEEL_EARNING,
        TransactionType.APP_REVIEW_EARNING,
        TransactionType.MOVIE_REVIEW_EARNING,
        TransactionType.REFERRAL_COMMISSION,
    }

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")
    wallet_type = models.CharField(max_length=10, choices=WalletType.choices)
    transaction_type = models.CharField(max_length=25, choices=TransactionType.choices)
    # Positive for credits, negative for debits — so summing this column
    # for a wallet_type always reconciles to that balance.
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.wallet.user.username} | {self.get_transaction_type_display()} | {self.amount}"