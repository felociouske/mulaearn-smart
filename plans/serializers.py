from rest_framework import serializers

from .models import Plan, PlanFeature, PlanPurchase


class PlanFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanFeature
        fields = ["id", "description", "order"]


class PlanSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    features = PlanFeatureSerializer(many=True, read_only=True)
    price_local = serializers.SerializerMethodField()
    currency_code = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = [
            "id", "category", "category_display", "name", "price", "price_local", "currency_code",
            "tier_order", "unlocked_item_count", "cashback_percentage", "features",
        ]

    def get_price_local(self, plan):
        # `price` (above) is the canonical KES price used internally — this
        # is what should actually be shown to the user, converted via the
        # same Country.convert_from_kes() every other payout uses. Falls
        # back to the raw KES price if we don't have a request/user in
        # context (e.g. admin-side serialization).
        user = getattr(self.context.get("request"), "user", None)
        country = getattr(user, "country", None)
        return str(country.convert_from_kes(plan.price)) if country else str(plan.price)

    def get_currency_code(self, plan):
        user = getattr(self.context.get("request"), "user", None)
        country = getattr(user, "country", None)
        return country.currency_code if country else "KES"


class PlanPurchaseSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)

    class Meta:
        model = PlanPurchase
        fields = ["id", "plan", "price_paid", "is_active", "purchased_at"]
        read_only_fields = fields