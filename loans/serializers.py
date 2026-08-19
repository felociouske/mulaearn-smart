from rest_framework import serializers

from .models import LoanApplication, LoanPlan, LoanPlanPurchase


class LoanPlanSerializer(serializers.ModelSerializer):
    price_local = serializers.SerializerMethodField()
    currency_code = serializers.SerializerMethodField()

    class Meta:
        model = LoanPlan
        fields = [
            "id", "name", "price", "price_local", "currency_code",
            "min_amount", "max_amount", "order", "repayment_period_days",
        ]

    def get_price_local(self, plan):
        # Same conversion every other price/payout in the project uses —
        # see plans.serializers.PlanSerializer.get_price_local, which this
        # mirrors exactly.
        user = getattr(self.context.get("request"), "user", None)
        country = getattr(user, "country", None)
        return str(country.convert_from_kes(plan.price)) if country else str(plan.price)

    def get_currency_code(self, plan):
        user = getattr(self.context.get("request"), "user", None)
        country = getattr(user, "country", None)
        return country.currency_code if country else "KES"


class LoanPlanPurchaseSerializer(serializers.ModelSerializer):
    loan_plan = LoanPlanSerializer(read_only=True)

    class Meta:
        model = LoanPlanPurchase
        fields = ["id", "loan_plan", "price_paid", "purchased_at"]
        read_only_fields = fields


class LoanEligibilitySerializer(serializers.Serializer):
    """
    Not a ModelSerializer — this represents a computed answer
    (get_loan_eligibility()), not a row. has_plan=False means every other
    field is meaningless/omitted; the frontend's "plan needed, view
    plans" case keys off has_plan alone.
    """
    has_plan = serializers.BooleanField()
    loan_plan = LoanPlanSerializer(required=False)
    min_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    max_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)


class LoanApplicationSerializer(serializers.ModelSerializer):
    """
    Used both for reading history (GET /api/loans/applications/) and as
    the base for validating a new submission (SubmitLoanApplicationView
    builds the instance itself rather than calling .save() on this
    serializer directly, since amount's valid range depends on the
    caller's computed eligibility, not a static field — see
    views.SubmitLoanApplicationView for where that check actually lives).
    """
    loan_plan = LoanPlanSerializer(read_only=True)

    class Meta:
        model = LoanApplication
        fields = [
            "id", "loan_plan", "email", "phone_number", "country_name",
            "full_name", "age", "source_of_income", "repayment_method", "security",
            "amount", "amount_owed", "due_date", "repayment_status", "created_at",
        ]
        read_only_fields = [
            "id", "loan_plan", "email", "phone_number", "country_name",
            "amount_owed", "due_date", "repayment_status", "created_at",
        ]

    def validate_age(self, value):
        # No age policy was specified — 18 is the obvious floor for any
        # credit product; 100 is just a sanity ceiling against fat-finger
        # input, not a real business rule. Adjust if you have an actual
        # minimum in mind.
        if value < 18:
            raise serializers.ValidationError("You must be at least 18 to apply for a loan.")
        if value > 100:
            raise serializers.ValidationError("Enter a valid age.")
        return value

    def validate_full_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Enter your full name.")
        return value.strip()