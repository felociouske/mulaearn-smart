from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class GatewayGroup(models.TextChoices):
    KENYA = "kenya", "Kenya"
    UGANDA_TANZANIA = "uganda_tanzania", "Uganda / Tanzania"
    GHANA_NIGERIA = "ghana_nigeria", "Ghana / Nigeria (Eversend)"
    OTHER = "other", "Other countries"


# Which GatewayGroup a Country.code falls into. Edit ONLY this dict when a
# new country needs wiring up — every view/serializer below reads from
# here, so a country not listed here automatically falls into OTHER.
COUNTRY_CODE_TO_GROUP = {
    "KE": GatewayGroup.KENYA,
    "UG": GatewayGroup.UGANDA_TANZANIA,
    "TZ": GatewayGroup.UGANDA_TANZANIA,
    "GH": GatewayGroup.GHANA_NIGERIA,
    "NG": GatewayGroup.GHANA_NIGERIA,
}


def group_for_country(country):
    """None if the user has no country set; OTHER for anything unlisted above."""
    if not country:
        return None
    return COUNTRY_CODE_TO_GROUP.get(country.code, GatewayGroup.OTHER)


class PaymentGateway(models.Model):
    """
    Shared base row for every country-group table below. Uses Django
    multi-table inheritance: each subclass gets its OWN table (with only
    the fields that group actually needs) PLUS a guaranteed row here in
    the shared `activation_paymentgateway` table.

    This is what lets ActivationSubmission.gateway and
    DepositRequest.gateway each be a SINGLE ForeignKey that can point at
    a Kenya, Uganda/Tanzania, Ghana/Nigeria, or Other row interchangeably
    — real referential integrity, no GenericForeignKey, no four separate
    nullable FKs to keep in sync.

    Don't instantiate this directly — always create one of the four
    concrete subclasses further down this file.
    """
    country = models.ForeignKey("accounts.Country", on_delete=models.CASCADE, related_name="payment_gateways")
    group = models.CharField(max_length=20, choices=GatewayGroup.choices, editable=False)
    display_name = models.CharField(
        max_length=100,
        help_text="Shown as the option label, e.g. 'Pay via M-Pesa Till (Instant)'.",
    )
    description = models.TextField(
        help_text=(
            "The full payment guide shown to the user — on BOTH the activation page and "
            "the deposit page. One field, one source of truth: edit it here and both "
            "pages update together, so they can never drift out of sync."
        )
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Off = hidden from users entirely. A country with zero active rows shows a 'Coming soon' message on the frontend.",
    )
    order = models.PositiveIntegerField(
        default=0, help_text="Lower numbers show first when a country has more than one option."
    )

    class Meta:
        ordering = ["country", "order"]

    def __str__(self):
        return f"{self.country.name} — {self.display_name}"

    def save(self, *args, **kwargs):
        # Auto-stamp `group` from whichever concrete subclass is being
        # saved (each defines a GROUP class attribute below) so admin
        # list_filter/list_display on `group` works without every
        # subclass repeating this assignment.
        if not self.group:
            self.group = getattr(self, "GROUP", GatewayGroup.OTHER)
        super().save(*args, **kwargs)


class KenyaPaymentGateway(PaymentGateway):
    """
    Kenya normally has two active rows: one manual (till number,
    admin-approved after proof is submitted) and one automatic (Daraja
    STK push, instant). Both are meant to be is_active=True — if the
    automatic row is currently showing "Coming soon" on the frontend,
    that's controlled by THIS row's is_active flag; flip it in admin,
    no deploy needed.
    """
    GROUP = GatewayGroup.KENYA

    is_automatic = models.BooleanField(
        default=False,
        help_text="On = Daraja STK push (instant, no proof needed). Off = manual till, admin-approved after the user submits proof.",
    )
    till_number = models.CharField(max_length=20, blank=True)
    paybill_number = models.CharField(max_length=20, blank=True)
    account_reference = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = "Kenya payment method"
        verbose_name_plural = "Kenya payment methods"


class UgandaTanzaniaPaymentGateway(PaymentGateway):
    """MTN/Airtel-style manual transfer — just who to send to; the how-to lives in `description`."""
    GROUP = GatewayGroup.UGANDA_TANZANIA

    recipient_name = models.CharField(max_length=100)
    recipient_phone = models.CharField(max_length=20)

    class Meta:
        verbose_name = "Uganda/Tanzania payment method"
        verbose_name_plural = "Uganda/Tanzania payment methods"


class GhanaNigeriaPaymentGateway(PaymentGateway):
    """
    Eversend only. Deliberately no recipient_phone field — the payout
    destination is fully explained inside `description` (the step-by-step
    guide), identified by the link + recipient_name rather than a phone
    number field of its own.
    """
    GROUP = GatewayGroup.GHANA_NIGERIA

    eversend_link = models.URLField(help_text="Your Eversend payment link, e.g. https://eversend.me/pay/yourhandle")
    recipient_name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Ghana/Nigeria payment method (Eversend)"
        verbose_name_plural = "Ghana/Nigeria payment methods (Eversend)"


class OtherPaymentGateway(PaymentGateway):
    """Catch-all for any country not explicitly Kenya / Uganda / Tanzania / Ghana / Nigeria."""
    GROUP = GatewayGroup.OTHER

    recipient_name = models.CharField(max_length=100)
    recipient_phone = models.CharField(max_length=20)

    class Meta:
        verbose_name = "Other country payment method"
        verbose_name_plural = "Other country payment methods"


# Single dict driving every "which model/serializer applies to this
# country" decision across views.py — see group_for_country() above.
GROUP_MODEL = {
    GatewayGroup.KENYA: KenyaPaymentGateway,
    GatewayGroup.UGANDA_TANZANIA: UgandaTanzaniaPaymentGateway,
    GatewayGroup.GHANA_NIGERIA: GhanaNigeriaPaymentGateway,
    GatewayGroup.OTHER: OtherPaymentGateway,
}


class ActivationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class ActivationSubmission(models.Model):
    """
    One row per activation-payment attempt. Manual submissions sit
    PENDING until an admin approves them (approve() flips
    User.is_activated). The Kenya-automatic (Daraja) option can still be
    approved manually from admin like any other submission until the STK
    push callback for activation specifically is wired up.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activation_submissions")
    gateway = models.ForeignKey(
        PaymentGateway, on_delete=models.SET_NULL, null=True, blank=True, related_name="activation_submissions_set"
    )
    # Snapshots of the gateway at submission time — survive the gateway
    # row later being edited or deleted, same pattern as
    # payment.DepositRequest snapshotting currency_code.
    gateway_group = models.CharField(max_length=20, choices=GatewayGroup.choices, blank=True)
    gateway_display_name = models.CharField(max_length=100, blank=True)

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency_code = models.CharField(max_length=5)

    reference_code = models.CharField(
        max_length=100, blank=True, help_text="M-Pesa code / transaction reference the user submitted."
    )
    proof_message = models.TextField(blank=True)

    # Automatic (Daraja) fields — unused until the STK push callback for
    # activation specifically is built.
    daraja_checkout_request_id = models.CharField(max_length=100, blank=True)
    daraja_receipt_number = models.CharField(max_length=100, blank=True)

    # Automatic (Daraja) fields — left in place but unused now that
    # automatic activation goes through BluePay instead (see the
    # bluepay_* fields below). Kept for history on any old rows and as
    # an easy rollback path, not because anything still writes to them.
    daraja_checkout_request_id = models.CharField(max_length=100, blank=True)
    daraja_receipt_number = models.CharField(max_length=100, blank=True)

    # Automatic (BluePay) fields — populated by InitiateActivationBluepayPushView
    # (activation/views.py) when the STK push is sent; bluepay_receipt_number
    # and the actual approve()/reject() call come from BluepayCallbackView
    # (bluepay/views.py) once BluePay's webhook confirms the payment.
    bluepay_checkout_request_id = models.CharField(max_length=100, blank=True)
    bluepay_stk_request_id = models.CharField(max_length=100, blank=True)
    bluepay_receipt_number = models.CharField(max_length=100, blank=True)

    status = models.CharField(max_length=10, choices=ActivationStatus.choices, default=ActivationStatus.PENDING)
    admin_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="activations_reviewed"
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