from decimal import Decimal

from django.core.management.base import BaseCommand

from accounts.models import Country
from activation.models import GatewayMethodType, PaymentGateway

# (code, name, currency_code, currency_symbol, exchange_rate_to_kes, activation_fee_placeholder)
# activation_fee is a PLACEHOLDER — edit real amounts in admin (Country list, activation_fee is list_editable).
COUNTRIES = [
    ("KE", "Kenya", "KES", "KSh", Decimal("1.0"), Decimal("300.00")),
    ("UG", "Uganda", "UGX", "USh", Decimal("0.037"), Decimal("15000.00")),
    ("TZ", "Tanzania", "TZS", "TSh", Decimal("0.054"), Decimal("10000.00")),
    ("NG", "Nigeria", "NGN", "₦", Decimal("0.085"), Decimal("2500.00")),
    ("GH", "Ghana", "GHS", "GH₵", Decimal("8.5"), Decimal("35.00")),
]

# (country_code, method_type, display_name, is_automatic, extra_fields, instructions)
GATEWAYS = [
    (
        "KE", GatewayMethodType.KENYA_TILL_AUTOMATIC, "Pay via M-Pesa (Instant)", True,
        {"till_number": "000000"},
        "1. Enter your M-Pesa PIN when prompted.\n2. Confirm the STK push on your phone.\n3. Your account activates automatically once payment is confirmed.",
    ),
    (
        "KE", GatewayMethodType.KENYA_TILL_MANUAL, "Pay via M-Pesa Till (Manual)", False,
        {"till_number": "000000", "recipient_name": "EasyEarn"},
        "1. Go to M-Pesa > Lipa na M-Pesa > Buy Goods and Services.\n"
        "2. Enter Till Number: 000000\n"
        "3. Enter the activation amount and your M-Pesa PIN.\n"
        "4. Copy the confirmation message and submit it below along with the M-Pesa code.",
    ),
    (
        "UG", GatewayMethodType.MTN_MANUAL, "MTN Mobile Money", False,
        {"recipient_phone": "+254700000000", "recipient_name": "EasyEarn"},
        "1. Dial *165# on your MTN line.\n"
        "2. Choose Send Money > select 'To Kenya / International'.\n"
        "3. Enter +254700000000 as the recipient number.\n"
        "4. Enter the activation amount shown and confirm with your MTN PIN.\n"
        "5. Copy the transaction reference and submit it below.",
    ),
    (
        "UG", GatewayMethodType.AIRTEL_MANUAL, "Airtel Money", False,
        {"recipient_phone": "+254700000000", "recipient_name": "EasyEarn"},
        "1. Dial *185# on your Airtel line.\n"
        "2. Choose Send Money > International/Kenya transfer.\n"
        "3. Enter +254700000000 as the recipient number.\n"
        "4. Enter the activation amount and confirm with your Airtel Money PIN.\n"
        "5. Copy the transaction reference and submit it below.",
    ),
    (
        "TZ", GatewayMethodType.MTN_MANUAL, "MTN Mobile Money (Tigo/Mixx by Yas)", False,
        {"recipient_phone": "+254700000000", "recipient_name": "EasyEarn"},
        "1. Open your mobile money menu and choose Send Money > International.\n"
        "2. Enter +254700000000 as the recipient number in Kenya.\n"
        "3. Enter the activation amount and confirm with your PIN.\n"
        "4. Copy the transaction reference and submit it below.",
    ),
    (
        "TZ", GatewayMethodType.AIRTEL_MANUAL, "Airtel Money", False,
        {"recipient_phone": "+254700000000", "recipient_name": "EasyEarn"},
        "1. Dial the Airtel Money menu and choose Send Money > International/Kenya.\n"
        "2. Enter +254700000000 as the recipient number.\n"
        "3. Enter the activation amount and confirm with your PIN.\n"
        "4. Copy the transaction reference and submit it below.",
    ),
    (
        "NG", GatewayMethodType.EVERSEND_MANUAL, "Eversend", False,
        {"recipient_phone": "+254700000000", "recipient_name": "EasyEarn"},
        "1. Open the Eversend app and add/select your NGN wallet.\n"
        "2. Send the activation amount to +254700000000 (Kenya, M-Pesa payout).\n"
        "3. Copy the Eversend transaction reference and submit it below.",
    ),
    (
        "GH", GatewayMethodType.EVERSEND_MANUAL, "Eversend", False,
        {"recipient_phone": "+254700000000", "recipient_name": "EasyEarn"},
        "1. Open the Eversend app and add/select your GHS wallet.\n"
        "2. Send the activation amount to +254700000000 (Kenya, M-Pesa payout).\n"
        "3. Copy the Eversend transaction reference and submit it below.",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds Kenya/Uganda/Tanzania/Nigeria/Ghana countries (if missing) and a starter "
        "PaymentGateway row per rail described in the spec. Every number in here is a "
        "PLACEHOLDER — go edit real till numbers, phone numbers, and activation fees in "
        "admin afterward. Safe to re-run: uses get_or_create, never duplicates rows."
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

        for order, (code, method_type, display_name, is_automatic, extra, instructions) in enumerate(GATEWAYS):
            country = country_by_code.get(code) or Country.objects.filter(code=code).first()
            if not country:
                self.stdout.write(self.style.WARNING(f"Skipping {display_name}: country {code} not found."))
                continue

            gateway, created = PaymentGateway.objects.get_or_create(
                country=country,
                method_type=method_type,
                defaults={
                    "display_name": display_name,
                    "is_automatic": is_automatic,
                    "instructions": instructions,
                    "order": order,
                    **extra,
                },
            )
            verb = "Created" if created else "Already exists"
            self.stdout.write(f"  {verb}: {gateway}")

        self.stdout.write(self.style.SUCCESS(
            "\nDone. IMPORTANT: every till number, phone number, and activation_fee above is a "
            "placeholder — go update them for real in /admin/ (Countries and Payment gateways) "
            "before going live."
        ))
