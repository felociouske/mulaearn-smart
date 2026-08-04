from decimal import Decimal

from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError

from wallets.models import Transaction

# Minimum withdrawal in KES-equivalent, per your instruction — this is
# converted to each country's local currency for display using
# Country.exchange_rate_to_kes, not hardcoded per-country amounts, since you
# said "should reflect for all country dashboards". No withdrawal fee.
MINIMUM_WITHDRAWAL_KES = Decimal("200.00")


class PaymentMethod(models.TextChoices):
    MANUAL = "manual", "Manual (proof submitted, admin-approved)"
    AUTOMATIC_DARAJA = "automatic_daraja", "Automatic — Safaricom Daraja"


class RequestStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class DepositRequest(models.Model):
    """
    A deposit, either:
      - manual: user submits a payment message/proof, admin reviews and
        approves, deposit_balance is credited on approval.
      - automatic_daraja: created + auto-resolved by the Daraja STK push
        callback (Kenya only, for now).
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="deposit_requests")
    method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # in the user's local currency
    currency_code = models.CharField(max_length=5)  # snapshot of Country.currency_code at request time

    # Manual-only fields
    proof_message = models.TextField(blank=True, help_text="The payment confirmation message the user submitted")

    # Automatic (Daraja) fields
    daraja_checkout_request_id = models.CharField(max_length=100, blank=True)
    daraja_receipt_number = models.CharField(max_length=100, blank=True)

    status = models.CharField(max_length=10, choices=RequestStatus.choices, default=RequestStatus.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="deposits_reviewed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} deposit {self.amount} {self.currency_code} ({self.status})"

    def approve(self, reviewed_by=None):
        """
        Approves a manual deposit and credits the user's deposit_balance.
        For automatic (Daraja) deposits, call this from the payment
        callback handler once Daraja confirms success — same credit path,
        so the ledger doesn't care which route the money came through.
        """
        from django.utils import timezone

        if self.status != RequestStatus.PENDING:
            raise ValidationError(f"Cannot approve a deposit request that is already {self.status}.")

        transaction_type = (
            Transaction.TransactionType.DEPOSIT_AUTOMATIC
            if self.method == PaymentMethod.AUTOMATIC_DARAJA
            else Transaction.TransactionType.DEPOSIT_MANUAL
        )
        self.user.wallet.credit(
            wallet_type="deposit",
            amount=self.amount,
            transaction_type=transaction_type,
            description=f"Deposit request #{self.pk}",
        )
        self.status = RequestStatus.APPROVED
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "reviewed_at"])


class WithdrawalRequest(models.Model):
    """
    A withdrawal request against account_balance and/or yield_balance.
    Enforces MINIMUM_WITHDRAWAL_KES at request time (converted to the
    user's currency) — see clean().
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="withdrawal_requests")
    # Which wallet the withdrawal draws from — account earnings or referral yield.
    wallet_type = models.CharField(
        max_length=10,
        choices=[("account", "Account Balance"), ("yield", "Yield Wallet")],
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # in the user's local currency
    currency_code = models.CharField(max_length=5)
    destination_details = models.CharField(
        max_length=255, help_text="M-Pesa number, bank details, etc. — destination for payout"
    )
    status = models.CharField(max_length=10, choices=RequestStatus.choices, default=RequestStatus.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="withdrawals_reviewed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} withdraw {self.amount} {self.currency_code} ({self.status})"

    def clean(self):
        """
        Enforces the Ksh 200 minimum, converted into whatever currency this
        request is in via Country.convert_from_kes() — e.g. for a country
        where 1 unit = 0.5 KES, the local minimum becomes 400.
        Call full_clean() (or this directly) before saving a new request.
        """
        country = self.user.country
        minimum_in_local_currency = (
            country.convert_from_kes(MINIMUM_WITHDRAWAL_KES) if country else MINIMUM_WITHDRAWAL_KES
        )

        if self.amount < minimum_in_local_currency:
            raise ValidationError(
                f"Minimum withdrawal is {minimum_in_local_currency} {self.currency_code} "
                f"(equivalent to Ksh {MINIMUM_WITHDRAWAL_KES})."
            )

    def approve(self, reviewed_by=None):
        """Debits the user's wallet and marks the request approved."""
        from django.utils import timezone

        if self.status != RequestStatus.PENDING:
            raise ValidationError(f"Cannot approve a withdrawal request that is already {self.status}.")

        self.user.wallet.debit(
            wallet_type=self.wallet_type,
            amount=self.amount,
            transaction_type=Transaction.TransactionType.WITHDRAWAL,
            description=f"Withdrawal request #{self.pk}",
        )
        self.status = RequestStatus.APPROVED
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "reviewed_at"])

    def reject(self, reviewed_by=None):
        from django.utils import timezone

        if self.status != RequestStatus.PENDING:
            raise ValidationError(f"Cannot reject a withdrawal request that is already {self.status}.")
        self.status = RequestStatus.REJECTED
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "reviewed_at"])