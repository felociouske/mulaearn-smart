from django.conf import settings
from django.db import models

from activation.models import ActivationSubmission
from plans.models import PlanPurchase

# 70% of the referred user's plan price, credited to the referrer's yield
# wallet — per your spec, even on later upgrades (each purchase triggers
# its own 70% commission independently).
REFERRAL_COMMISSION_RATE = 0.70

# 65% of the referred user's activation fee, credited to the referrer's
# yield wallet the moment that user's activation is approved.
REFERRAL_ACTIVATION_COMMISSION_RATE = 0.65


class ReferralCommission(models.Model):
    """
    One row per commission payout — created either when a referred user
    makes a PlanPurchase, or when a referred user's account activation is
    approved. Exactly one of `plan_purchase` / `activation_submission` is
    set, matching `source`. Kept separate from the User model so a
    referrer's full commission history (and which event each payout came
    from) stays queryable and auditable.
    """

    class Source(models.TextChoices):
        PLAN_PURCHASE = "plan_purchase", "Plan purchase"
        ACTIVATION = "activation", "Account activation"

    referrer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referral_commissions")
    referred_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.PLAN_PURCHASE)
    plan_purchase = models.OneToOneField(
        PlanPurchase, on_delete=models.CASCADE, related_name="referral_commission", null=True, blank=True
    )
    activation_submission = models.OneToOneField(
        ActivationSubmission, on_delete=models.CASCADE, related_name="referral_commission", null=True, blank=True
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # KES, snapshot at time of credit
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.referrer.username} earned {self.amount} from {self.referred_user.username} ({self.get_source_display()})"