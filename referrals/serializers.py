from django.db.models import Sum
from rest_framework import serializers

from .models import ReferralCommission


def _mask_email(email):
    if not email or "@" not in email:
        return email
    local, _, domain = email.partition("@")
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}{'*' * max(len(local) - len(visible), 2)}@{domain}"


def _mask_phone(phone):
    if not phone or len(phone) < 6:
        return phone
    return f"{phone[:4]}{'*' * (len(phone) - 7)}{phone[-3:]}"


class ReferredUserSerializer(serializers.Serializer):
    """
    What a referrer sees about someone who signed up under their link.
    Email/phone are DELIBERATELY MASKED (e.g. "jo***@gmail.com",
    "0712***678") rather than shown in full — a referred user agreed to
    join the platform, not to have their raw contact details handed to
    another user they may have only shared a link with once. Masked
    values are still enough to recognize who signed up without enabling
    a referrer to directly contact/spam them outside the platform.
    """
    id = serializers.IntegerField()
    email_masked = serializers.SerializerMethodField()
    phone_masked = serializers.SerializerMethodField()
    date_joined = serializers.DateTimeField()
    is_activated = serializers.BooleanField()
    commission_earned = serializers.SerializerMethodField()

    def get_email_masked(self, user):
        return _mask_email(user.email)

    def get_phone_masked(self, user):
        return _mask_phone(user.phone_number)

    def get_commission_earned(self, user):
        # Sum of every ReferralCommission this specific referred user has
        # generated for the requesting referrer — 0 if they haven't
        # purchased a plan yet (signing up alone earns nothing).
        from decimal import Decimal

        total = ReferralCommission.objects.filter(
            referrer=self.context["referrer"], referred_user=user
        ).aggregate(total=Sum("amount"))["total"]
        return str((total or Decimal("0.00")).quantize(Decimal("0.01")))


class ReferralCommissionSerializer(serializers.ModelSerializer):
    referred_username = serializers.CharField(source="referred_user.username", read_only=True)

    class Meta:
        model = ReferralCommission
        fields = ["id", "referred_username", "amount", "created_at"]
        read_only_fields = fields