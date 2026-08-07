from decimal import Decimal

from django.core.management.base import BaseCommand

from accounts.models import Country
from activation.models import (
    GhanaNigeriaPaymentGateway,
    KenyaPaymentGateway,
    OtherPaymentGateway,
    UgandaTanzaniaPaymentGateway,
)

# (code, name, currency_code, currency_symbol, exchange_rate_to_kes, activation_fee_placeholder)
# activation_fee is a PLACEHOLDER — edit real amounts in admin (Country list, activation_fee is list_editable).
COUNTRIES = [
    ("KE", "Kenya", "KES", "KSh", Decimal("1.0"), Decimal("300.00")),
    ("UG", "Uganda", "UGX", "USh", Decimal("0.037"), Decimal("15000.00")),
    ("TZ", "Tanzania", "TZS", "TSh", Decimal("0.054"), Decimal("10000.00")),
    ("NG", "Nigeria", "NGN", "₦", Decimal("0.085"), Decimal("2500.00")),
    ("GH", "Ghana", "GHS", "GH₵", Decimal("8.5"), Decimal("35.00")),
]


class Command(BaseCommand):
    help = (
        "Seeds Kenya/Uganda/Tanzania/Nigeria/Ghana countries (if missing) and a starter "
        "payment-method row per rail in each of the 4 country-group models. Every "
        "number/link in here is a PLACEHOLDER — go edit real till numbers, phone numbers, "
        "the Eversend link, and activation fees in admin afterward. Safe to re-run: uses "
        "get_or_create, never duplicates rows."
    )

    def handle(self, *args, **options):
        country_by_code = {}
        for code, name, currency_code, currency_symbol, rate, fee in COUNTRIES:
            country, created = Country.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "currency_code": currency_code,
                    "currency_symbol": currency_symbol,
                    "exchange_rate_to_kes": rate,
                    "activation_fee": fee,
                    "is_international_bucket": False,
                },
            )
            country_by_code[code] = country
            self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Found'} country: {country.name}"))

        ke = country_by_code["KE"]

        # --- Kenya: both rows active by default now (automatic is no longer "coming soon") ---
        gw, created = KenyaPaymentGateway.objects.get_or_create(
            country=ke, is_automatic=True,
            defaults={
                "display_name": "Pay via M-Pesa (Instant)",
                "is_active": True,
                "order": 0,
                "till_number": "000000",
                "description": (
                    "1. Enter your M-Pesa PIN when prompted.\n"
                    "2. Confirm the STK push on your phone.\n"
                    "3. Your account activates automatically once payment is confirmed."
                ),
            },
        )
        self.stdout.write(f"  {'Created' if created else 'Already exists'}: {gw}")

        gw, created = KenyaPaymentGateway.objects.get_or_create(
            country=ke, is_automatic=False,
            defaults={
                "display_name": "Pay via M-Pesa Till (Manual)",
                "is_active": True,
                "order": 1,
                "till_number": "000000",
                "description": (
                    "1. Go to M-Pesa > Lipa na M-Pesa > Buy Goods and Services.\n"
                    "2. Enter Till Number: 000000\n"
                    "3. Enter the amount and your M-Pesa PIN.\n"
                    "4. Copy the confirmation message and submit it below along with the M-Pesa code."
                ),
            },
        )
        self.stdout.write(f"  {'Created' if created else 'Already exists'}: {gw}")

        # --- Uganda / Tanzania: recipient name + phone, one row per country ---
        for code in ("UG", "TZ"):
            country = country_by_code[code]
            gw, created = UgandaTanzaniaPaymentGateway.objects.get_or_create(
                country=country,
                defaults={
                    "display_name": "Mobile Money",
                    "is_active": True,
                    "order": 0,
                    "recipient_name": "EasyEarn",
                    "recipient_phone": "+254700000000",
                    "description": (
                        "1. Open your mobile money menu and choose Send Money > International/Kenya.\n"
                        "2. Enter +254700000000 as the recipient number.\n"
                        "3. Enter the amount and confirm with your PIN.\n"
                        "4. Copy the transaction reference and submit it below."
                    ),
                },
            )
            self.stdout.write(f"  {'Created' if created else 'Already exists'}: {gw}")

        # --- Ghana / Nigeria: Eversend link + recipient name only ---
        for code in ("GH", "NG"):
            country = country_by_code[code]
            gw, created = GhanaNigeriaPaymentGateway.objects.get_or_create(
                country=country,
                defaults={
                    "display_name": "Eversend",
                    "is_active": True,
                    "order": 0,
                    "eversend_link": "https://eversend.me/pay/PLACEHOLDER",
                    "recipient_name": "EasyEarn",
                    "description": (
                        "1. Open the Eversend link below (or the Eversend app) and select your local wallet.\n"
                        "2. Send the amount shown to EasyEarn.\n"
                        "3. Copy the Eversend transaction reference and submit it below."
                    ),
                },
            )
            self.stdout.write(f"  {'Created' if created else 'Already exists'}: {gw}")

        self.stdout.write(self.style.SUCCESS(
            "\nDone. IMPORTANT: every till number, phone number, Eversend link, and "
            "activation_fee above is a placeholder — go update them for real in /admin/ "
            "before going live. OtherPaymentGateway has no default seed rows since it "
            "covers whichever additional country you add next — create those rows in "
            "admin when you're ready."
        ))