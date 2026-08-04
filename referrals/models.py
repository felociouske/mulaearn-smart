from django.conf import settings
from django.db import models

from plans.models import PlanPurchase

# 70% of the referred user's plan price, credited to the referrer's yield
# wallet — per your spec, even on later upgrades (each purchase triggers
# its own 70% commission independently).
REFERRAL_COMMISSION_RATE = 0.70


class ReferralCommission(models.Model):
    """
    One row per commission payout — created whenever a referred user makes
    a PlanPurchase. Kept separate from the User model so a referrer's full
    commission history (and which purchase each payout came from) stays
    queryable and auditable.
    """
    referrer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referral_commissions")
    referred_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    plan_purchase = models.OneToOneField(PlanPurchase, on_delete=models.CASCADE, related_name="referral_commission")
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # KES, snapshot at time of credit
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.referrer.username} earned {self.amount} from {self.referred_user.username}'s purchase"