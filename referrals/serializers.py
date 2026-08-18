from django.db.models import Sum
from rest_framework import serializers

from .models import ReferralCommission


class ReferredUserSerializer(serializers.Serializer):
    """
    What a referrer sees about someone who signed up under their link.
    Email/phone are shown in full (unmasked) so the referrer can
    recognize and, if needed, follow up with the people they referred.
    """
    id = serializers.IntegerField()
    email = serializers.EmailField()
    phone_number = serializers.CharField()
    date_joined = serializers.DateTimeField()
    is_activated = serializers.BooleanField()
    commission_earned = serializers.SerializerMethodField()

    def get_commission_earned(self, user):
        # Sum of every ReferralCommission this specific referred user has
        # generated for the requesting referrer — across BOTH sources
        # (their activation and any plan purchases) — 0 if neither has
        # happened yet.
        from decimal import Decimal

        total = ReferralCommission.objects.filter(
            referrer=self.context["referrer"], referred_user=user
        ).aggregate(total=Sum("amount"))["total"]
        return str((total or Decimal("0.00")).quantize(Decimal("0.01")))


class ReferralCommissionSerializer(serializers.ModelSerializer):
    referred_username = serializers.CharField(source="referred_user.username", read_only=True)
    source_display = serializers.CharField(source="get_source_display", read_only=True)

    class Meta:
        model = ReferralCommission
        fields = ["id", "referred_username", "source", "source_display", "amount", "created_at"]
        read_only_fields = fields