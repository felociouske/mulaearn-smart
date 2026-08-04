from decimal import Decimal

from django.core.management.base import BaseCommand

from plans.models import Plan, PlanCategory, PlanFeature

# All prices/unlock-counts/cashback numbers below are PLACEHOLDERS —
# edit real numbers in admin afterward. tier_order starts at 1 within
# each category (App-review 1..4, Movie-review 1..4, Chat 1..6).

APP_REVIEW_PLANS = [
    # (tier_order, name, price_kes, unlocked_item_count, cashback_pct, features)
    (1, "App Review Starter", Decimal("500.00"), 20, Decimal("2.00"),
     ["Unlock 20 apps to review", "2% cashback on every completed review", "Ksh 129.33 per review"]),
    (2, "App Review Plus", Decimal("900.00"), 40, Decimal("3.00"),
     ["Unlock 40 apps to review", "3% cashback on every completed review", "Priority app queue"]),
    (3, "App Review Pro", Decimal("1500.00"), 70, Decimal("4.00"),
     ["Unlock 70 apps to review", "4% cashback on every completed review", "Priority app queue"]),
    (4, "App Review Elite", Decimal("2200.00"), 100, Decimal("5.00"),
     ["Unlock 100 apps to review", "5% cashback on every completed review", "Priority support"]),
]

MOVIE_REVIEW_PLANS = [
    (1, "Movie Review Starter", Decimal("500.00"), 20, Decimal("2.00"),
     ["Unlock 20 movies to review", "2% cashback on every completed review", "Ksh 129.33 per review"]),
    (2, "Movie Review Plus", Decimal("900.00"), 40, Decimal("3.00"),
     ["Unlock 40 movies to review", "3% cashback on every completed review", "Priority movie queue"]),
    (3, "Movie Review Pro", Decimal("1500.00"), 70, Decimal("4.00"),
     ["Unlock 70 movies to review", "4% cashback on every completed review", "Priority movie queue"]),
    (4, "Movie Review Elite", Decimal("2200.00"), 100, Decimal("5.00"),
     ["Unlock 100 movies to review", "5% cashback on every completed review", "Priority support"]),
]

CHAT_PLANS = [
    (1, "Chat Plan 1", Decimal("1550.00"), 3, None,
     ["Unlock 3 chat profiles", "Chat with foreigners and earn per message"]),
    (2, "Chat Plan 2", Decimal("2400.00"), 6, None,
     ["Unlock 6 chat profiles", "Access higher-paying profiles"]),
    (3, "Chat Plan 3", Decimal("3600.00"), 10, None,
     ["Unlock 10 chat profiles", "Access higher-paying profiles"]),
    (4, "Chat Plan 4", Decimal("5500.00"), 15, None,
     ["Unlock 15 chat profiles", "Access higher-paying profiles", "Priority support"]),
    (5, "Chat Plan 5", Decimal("6500.00"), 20, None,
     ["Unlock 20 chat profiles", "Access to top-paying profiles", "Priority support"]),
    (6, "Chat Plan 6", Decimal("8000.00"), 30, None,
     ["Unlock 30 chat profiles", "Access to every active profile", "Priority support"]),
]

CATEGORY_PLAN_LISTS = [
    (PlanCategory.APP_REVIEW, APP_REVIEW_PLANS),
    (PlanCategory.MOVIE_REVIEW, MOVIE_REVIEW_PLANS),
    (PlanCategory.CHAT, CHAT_PLANS),
]


class Command(BaseCommand):
    help = (
        "Seeds 4 App-review plans, 4 Movie-review plans, and 6 Chat plans with placeholder "
        "pricing, unlock counts, cashback %, and feature bullets. Every number is a PLACEHOLDER "
        "— edit real values in admin afterward. Safe to re-run: uses get_or_create on "
        "(category, tier_order), never duplicates plans; re-running also does NOT overwrite "
        "prices/counts you've already edited in admin, only fills in missing rows."
    )

    def handle(self, *args, **options):
        for category, plan_list in CATEGORY_PLAN_LISTS:
            for tier_order, name, price, unlocked_item_count, cashback_pct, feature_lines in plan_list:
                plan, created = Plan.objects.get_or_create(
                    category=category,
                    tier_order=tier_order,
                    defaults={
                        "name": name,
                        "price": price,
                        "unlocked_item_count": unlocked_item_count,
                        "cashback_percentage": cashback_pct,
                    },
                )
                verb = "Created" if created else "Already exists"
                self.stdout.write(f"  {verb}: {plan}")

                if created:
                    for order, line in enumerate(feature_lines):
                        PlanFeature.objects.get_or_create(plan=plan, description=line, defaults={"order": order})

        self.stdout.write(self.style.SUCCESS(
            "\nDone. IMPORTANT: prices, unlock counts, cashback %, and feature text above are "
            "placeholders — go update them for real in /admin/ (Plans, with inline Plan features) "
            "before going live."
        ))