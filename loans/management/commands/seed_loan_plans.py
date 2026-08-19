from decimal import Decimal

from django.core.management.base import BaseCommand

from loans.models import LoanPlan

# Unlike plans/management/commands/seed_plans.py's placeholder numbers,
# these are your actual confirmed tiers — safe to run as-is.
LOAN_PLANS = [
    # (order, name, price_kes, min_amount, max_amount)
    (1, "MulaEarn Starter", Decimal("3500.00"), Decimal("1000.00"), Decimal("5000.00")),
    (2, "MulaEarn Beneficiary", Decimal("6800.00"), Decimal("5000.00"), Decimal("15000.00")),
    (3, "Advanced Tier 1", Decimal("13500.00"), Decimal("15000.00"), Decimal("25000.00")),
    (4, "Advanced Tier 2", Decimal("18500.00"), Decimal("25000.00"), Decimal("35000.00")),
    (5, "Advanced Tier 3", Decimal("26000.00"), Decimal("35000.00"), Decimal("50000.00")),
    (6, "Company Elite", Decimal("49000.00"), Decimal("50000.00"), Decimal("100000.00")),
]


class Command(BaseCommand):
    help = (
        "Seeds the 6 loan-plan tiers with your real confirmed pricing and "
        "ranges. Safe to re-run: uses get_or_create on `order`, never "
        "duplicates rows, and does NOT overwrite anything you've already "
        "edited in admin — only fills in rows that don't exist yet."
    )

    def handle(self, *args, **options):
        for order, name, price, min_amount, max_amount in LOAN_PLANS:
            plan, created = LoanPlan.objects.get_or_create(
                order=order,
                defaults={"name": name, "price": price, "min_amount": min_amount, "max_amount": max_amount},
            )
            verb = "Created" if created else "Already exists"
            self.stdout.write(f"  {verb}: {plan}")

        self.stdout.write(self.style.SUCCESS("\nDone. Edit repayment_period_days per tier in /admin/ if 30 days isn't right."))