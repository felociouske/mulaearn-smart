from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class GatewayMethodType(models.TextChoices):
    """
    Covers every rail from the spec. Kept as one flat choices list (not a
    subclass hierarchy) since PaymentGateway rows are otherwise generic —
    the method_type just determines which fields the frontend renders
    (STK push form vs a numbered "send money to this number" guide).
    """
    KENYA_TILL_AUTOMATIC = "kenya_till_automatic", "Kenya — M-Pesa Till (Automatic / Daraja)"
    KENYA_TILL_MANUAL = "kenya_till_manual", "Kenya — M-Pesa Till (Manual)"
    MTN_MANUAL = "mtn_manual", "MTN Mobile Money (Manual, send to Kenya)"
    AIRTEL_MANUAL = "airtel_manual", "Airtel Money (Manual, send to Kenya)"
    EVERSEND_MANUAL = "eversend_manual", "Eversend (Manual)"
    OTHER_MANUAL = "other_manual", "Other (Manual)"


class PaymentGateway(models.Model):
    """
    One row per activation-payment option shown for a country. Kenya gets
    two rows (automatic + manual); Uganda/Tanzania get MTN + Airtel rows;
    Nigeria/Ghana get an Eversend row. A country with zero active rows
    here means "not wired up yet" — the frontend falls back to a
    "Coming soon, contact support" message, so covering a new country is
    just adding rows in admin, no deploy required.
    """
    country = models.ForeignKey(
        "accounts.Country", on_delete=models.CASCADE, related_name="payment_gateways"
    )
    method_type = models.CharField(max_length=25, choices=GatewayMethodType.choices)
    display_name = models.CharField(
        max_length=100,
        help_text="Shown as the option label on the activation page, e.g. 'Pay via M-Pesa Till (Instant)'.",
    )
    is_automatic = models.BooleanField(
        default=False,
        help_text="On = STK push flow (Daraja, Kenya only for now). Off = manual proof-submission flow.",
    )

    # Generic destination fields. Fill in only the ones this method needs
    # and leave the rest blank — kept generic (not one field set per rail)
    # so adding a brand-new payment rail later is still just new admin
    # rows, not a migration.
    till_number = models.CharField(max_length=20, blank=True)
    paybill_number = models.CharField(max_length=20, blank=True)
    account_reference = models.CharField(max_length=50, blank=True)
    recipient_name = models.CharField(max_length=100, blank=True)
    recipient_phone = models.CharField(max_length=20, blank=True)

    instructions = models.TextField(
        help_text=(
            "Step-by-step guide shown to the user exactly as typed here — e.g. numbered "
            "steps for an MTN/Airtel send-money-to-Kenya flow. Plain text, one step per line."
        )
    )
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(
        default=0, help_text="Lower numbers show first when a country has more than one option."
    )

    class Meta:
        ordering = ["country", "order"]

    def __str__(self):
        return f"{self.country.name} — {self.display_name}"


class ActivationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class ActivationSubmission(models.Model):
    """
    One row per activation-payment attempt.

    Manual submissions sit PENDING until an admin approves them (approve()
    flips User.is_activated). Automatic (Daraja) submissions are created
    up front and meant to be auto-resolved by an STK push callback once
    that's wired up — the daraja_* fields already exist so no migration
    is needed when that lands; for now the automatic option can still be
    approved manually from admin like any other submission.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activation_submissions"
    )
    gateway = models.ForeignKey(
        PaymentGateway, on_delete=models.SET_NULL, null=True, blank=True, related_name="submissions"
    )
    # Snapshot of gateway.method_type at submission time — survives the
    # gateway row later being edited or deleted, same pattern as
    # payment.DepositRequest snapshotting currency_code.
    method_type = models.CharField(max_length=25, choices=GatewayMethodType.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency_code = models.CharField(max_length=5)

    reference_code = models.CharField(
        max_length=100, blank=True, help_text="M-Pesa code / transaction reference the user submitted."
    )
    proof_message = models.TextField(blank=True)

    # Automatic (Daraja) fields — unused until the STK push callback is built.
    daraja_checkout_request_id = models.CharField(max_length=100, blank=True)
    daraja_receipt_number = models.CharField(max_length=100, blank=True)

    status = models.CharField(max_length=10, choices=ActivationStatus.choices, default=ActivationStatus.PENDING)
    admin_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activations_reviewed",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} activation ({self.status})"

    def clean(self):
        qs = ActivationSubmission.objects.filter(user_id=self.user_id, status=ActivationStatus.PENDING)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError("You already have a pending activation submission.")

    def approve(self, reviewed_by=None):
        from django.utils import timezone

        if self.status != ActivationStatus.PENDING:
            raise ValidationError(f"Cannot approve an activation submission that is already {self.status}.")

        self.status = ActivationStatus.APPROVED
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "reviewed_at"])

        self.user.is_activated = True
        self.user.activated_at = timezone.now()
        self.user.save(update_fields=["is_activated", "activated_at"])

    def reject(self, reviewed_by=None, notes=""):
        from django.utils import timezone

        if self.status != ActivationStatus.PENDING:
            raise ValidationError(f"Cannot reject an activation submission that is already {self.status}.")
        self.status = ActivationStatus.REJECTED
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        if notes:
            self.admin_notes = notes
        self.save(update_fields=["status", "reviewed_by", "reviewed_at", "admin_notes"])
