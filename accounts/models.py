import uuid
from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.db import models


class Country(models.Model):
    """
    One row per country EasyEarn supports at sign-up.

    Kept as its own model (not a hardcoded choices list) because each
    country needs its own currency AND, later, its own deposit method
    config (Daraja for Kenya, other rails for Uganda/Tanzania/etc) — a
    plain CharField choices list can't hold that extra per-country data.
    """
    name = models.CharField(max_length=50, unique=True)
    # ISO 3166-1 alpha-2 where possible (KE, UG, TZ, GH, NG). "INTL" is our
    # own catch-all code for every country not explicitly listed yet.
    code = models.CharField(max_length=5, unique=True)
    currency_code = models.CharField(max_length=5, default="KES")  # ISO 4217, e.g. KES, UGX, TZS, GHS, NGN, USD
    currency_symbol = models.CharField(max_length=5, default="KSh")
    # How many KES 1 unit of this currency is worth — e.g. if 1 UGX = 0.037
    # KES, this is 0.037. Used to convert the KES-denominated minimum
    # withdrawal into each country's local currency for display/enforcement.
    # Update these manually in admin as rates move — no live FX feed for MVP.
    exchange_rate_to_kes = models.DecimalField(max_digits=10, decimal_places=6, default=Decimal("1.0"))
    # Marks the Kenya/Uganda/Tanzania/Ghana/Nigeria rows vs the catch-all
    # "international" bucket you described — lets the frontend group them.
    is_international_bucket = models.BooleanField(default=False)

    # What a user in this country must pay to activate their account,
    # in this country's own currency (not KES-equivalent, unlike the
    # withdrawal minimum) — set directly in admin per country, e.g. a
    # different number for KES vs UGX vs NGN. 0 effectively disables the
    # activation requirement for that country (useful for testing).
    activation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        verbose_name_plural = "countries"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def convert_from_kes(self, amount_kes):
        """
        Converts a KES amount into this country's local currency using
        exchange_rate_to_kes, quantized to 2dp — the same math
        WithdrawalRequest.clean() uses for the minimum-withdrawal check.
        Centralized here so every KES-denominated payout (review rewards,
        wheel spins, survey credits) converts the same way instead of each
        app reimplementing it slightly differently.
        """
        from decimal import Decimal

        rate = self.exchange_rate_to_kes or Decimal("1.0")
        return (Decimal(amount_kes) / rate).quantize(Decimal("0.01"))

    def convert_to_kes(self, amount_local):
        """
        The inverse of convert_from_kes() — converts an amount in THIS
        country's local currency into canonical KES, using the same
        exchange_rate_to_kes. Needed by DepositRequest.approve() and
        WithdrawalRequest.approve() (payment/models.py), which store
        `amount` in local currency but credit/debit wallet balances that
        are canonical KES.
        """
        from decimal import Decimal

        rate = self.exchange_rate_to_kes or Decimal("1.0")
        return (Decimal(amount_local) * rate).quantize(Decimal("0.01"))


class User(AbstractUser):
    """
    Custom user model. Login stays username + password (we don't override
    USERNAME_FIELD); email + phone_number are additionally required at
    registration (see REQUIRED_FIELDS).
    """
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, unique=True)
    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True,
    )

    # Every user gets a short unique referral code, generated automatically
    # (see save() below) — this is what gets embedded in a user's invite link.
    referral_code = models.CharField(max_length=12, unique=True, blank=True)

    # Who invited this user, if anyone. Self-FK rather than a separate
    # Referral model, since a user can only ever be referred once — this
    # keeps "did X refer Y" a single indexed lookup instead of a join.
    referred_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referrals",
    )

    # Gates dashboard access — set to True either by ActivationSubmission.approve()
    # (see the `activation` app) after a manual/automatic payment is approved,
    # or directly by an admin via the "Manually activate" action below.
    is_activated = models.BooleanField(default=False)
    activated_at = models.DateTimeField(null=True, blank=True)

    REQUIRED_FIELDS = ["email", "phone_number"]

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = uuid.uuid4().hex[:10].upper()
        super().save(*args, **kwargs)