from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db import models

# Weighted outcomes: (amount_in_kes, relative_weight). Mostly small
# payouts, the top prize is rare. Weights don't need to sum to 100 —
# random.choices() normalizes them. Tune freely.
WHEEL_OUTCOMES = [
    (Decimal("5.00"), 60),
    (Decimal("10.00"), 30),
    (Decimal("30.00"), 10),
]

MAX_SPINS_PER_DAY = 3


class WheelSpin(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wheel_spins")
    date = models.DateField(default=date.today)
    amount_kes = models.DecimalField(max_digits=10, decimal_places=2)
    credited_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency_code = models.CharField(max_length=5)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} — {self.amount_kes} KES ({self.date})"