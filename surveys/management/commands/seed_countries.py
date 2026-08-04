from decimal import Decimal

from django.core.management.base import BaseCommand

from accounts.models import Country

# Exchange rate and activation fee below are PLACEHOLDERS — especially the
# exchange rate, which needs periodic manual updates (FX rates move).
# 129.40 KES/USD was the approximate mid-market rate as of when this was
# written; check a current rate and update it in /admin/ (Countries) —
# no code change needed, Country.exchange_rate_to_kes is just a field.
OTHER_BUCKET_EXCHANGE_RATE_TO_KES = Decimal("129.40")
OTHER_BUCKET_ACTIVATION_FEE_USD = Decimal("15.00")


class Command(BaseCommand):
    help = (
        "Seeds Kenya and an international 'Other' catch-all bucket (USD) if they don't "
        "already exist. Safe to re-run — uses get_or_create, never overwrites an existing "
        "row's fields (e.g. if you've already edited the exchange rate in admin, re-running "
        "this won't reset it)."
    )

    def handle(self, *args, **options):
        kenya, created = Country.objects.get_or_create(
            code="KE",
            defaults=dict(
                name="Kenya",
                currency_code="KES",
                currency_symbol="KSh",
                exchange_rate_to_kes=Decimal("1.0"),
                is_international_bucket=False,
                activation_fee=Decimal("0.00"),  # PLACEHOLDER — set the real activation fee in admin
            ),
        )
        self.stdout.write(f"{'Created' if created else 'Already exists'}: {kenya}")

        other, created = Country.objects.get_or_create(
            code="OTHER",
            defaults=dict(
                name="Other (International)",
                currency_code="USD",
                currency_symbol="$",
                exchange_rate_to_kes=OTHER_BUCKET_EXCHANGE_RATE_TO_KES,
                is_international_bucket=True,
                activation_fee=OTHER_BUCKET_ACTIVATION_FEE_USD,
            ),
        )
        self.stdout.write(f"{'Created' if created else 'Already exists'}: {other}")

        self.stdout.write(self.style.SUCCESS(
            "\nDone. IMPORTANT: the 'Other' bucket's exchange rate is a snapshot, not a live "
            "feed — FX rates move, so check and update it periodically in /admin/ (Countries). "
            "Same goes for both activation fees, which are placeholders."
        ))