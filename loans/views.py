from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction as db_transaction
from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsActivated
from wallets.models import Transaction

from .models import LoanApplication, LoanPlan, LoanPlanPurchase, get_loan_eligibility
from .serializers import (
    LoanApplicationSerializer,
    LoanEligibilitySerializer,
    LoanPlanPurchaseSerializer,
    LoanPlanSerializer,
)


class LoanPlanListView(generics.ListAPIView):
    """GET /api/loans/plans/ — every active loan-plan tier, cheapest-first. Mirrors plans.views.PlanListView."""
    serializer_class = LoanPlanSerializer
    permission_classes = [permissions.AllowAny]
    queryset = LoanPlan.objects.filter(is_active=True)


class PurchaseLoanPlanView(APIView):
    """
    POST /api/loans/plans/<plan_id>/purchase/
    Debits deposit_balance for the tier's price and creates a new
    LoanPlanPurchase — unlike plans.views.PurchasePlanView, nothing here
    deactivates a previous purchase, since loan-plan tiers stack (a user
    can own several; get_loan_eligibility() reads off the highest one).
    Buying a tier you already own is allowed (creates a second row) —
    harmless but pointless, since eligibility is already at that tier;
    not blocked because you didn't ask for that restriction and it isn't
    unsafe, just a wasted purchase the user made themselves.
    """
    permission_classes = [permissions.IsAuthenticated, IsActivated]

    def post(self, request, plan_id):
        try:
            loan_plan = LoanPlan.objects.get(pk=plan_id, is_active=True)
        except LoanPlan.DoesNotExist:
            return Response({"detail": "Loan plan not found."}, status=404)

        try:
            with db_transaction.atomic():
                request.user.wallet.debit(
                    wallet_type="deposit",
                    amount=loan_plan.price,
                    transaction_type=Transaction.TransactionType.LOAN_PLAN_PURCHASE,
                    description=f"Purchased {loan_plan.name}",
                )
                purchase = LoanPlanPurchase.objects.create(
                    user=request.user, loan_plan=loan_plan, price_paid=loan_plan.price
                )
        except DjangoValidationError as e:
            # Most likely cause: insufficient deposit_balance.
            raise DRFValidationError(e.messages if hasattr(e, "messages") else str(e))

        return Response(LoanPlanPurchaseSerializer(purchase, context={"request": request}).data, status=201)


class MyLoanEligibilityView(APIView):
    """
    GET /api/loans/eligibility/
    {"has_plan": false} — no loan plan purchased yet; frontend shows
    "plan needed, view plans" per your spec.
    {"has_plan": true, "loan_plan": {...}, "min_amount": ..., "max_amount": ...}
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        loan_plan = get_loan_eligibility(request.user)
        if not loan_plan:
            return Response(LoanEligibilitySerializer({"has_plan": False}).data)

        data = {
            "has_plan": True,
            "loan_plan": loan_plan,
            "min_amount": loan_plan.min_amount,
            "max_amount": loan_plan.max_amount,
        }
        # Run through LoanEligibilitySerializer (not a bare Response(dict))
        # so min_amount/max_amount get the same DecimalField string
        # formatting ("1000.00", not a raw JSON number) as every other
        # amount in the API. The nested loan_plan field automatically
        # inherits this context (DRF walks up to the root serializer for
        # it), so LoanPlanSerializer's price_local/currency_code still work.
        return Response(LoanEligibilitySerializer(data, context={"request": request}).data)


class SubmitLoanApplicationView(APIView):
    """
    POST /api/loans/apply/
    { "full_name", "age", "source_of_income", "repayment_method",
      "security", "amount" }
    email/phone_number/country_name are NOT read from the request body —
    they're snapshotted from request.user server-side (see model
    docstring for why: those are real account fields worth auto-filling,
    full_name isn't since nothing on User holds one).

    Validates `amount` against get_loan_eligibility()'s range (a
    "plan needed" error if the user owns no loan plan at all, a 400 if
    amount is outside their range), then credits account_balance for the
    full amount immediately — no approval step, no limit on repeat
    applications (an existing OWING row doesn't block a new one), exactly
    as specified.
    """
    permission_classes = [permissions.IsAuthenticated, IsActivated]

    def post(self, request):
        loan_plan = get_loan_eligibility(request.user)
        if not loan_plan:
            raise DRFValidationError({"detail": ["You need an active loan plan before applying — view plans."]})

        serializer = LoanApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        amount = serializer.validated_data["amount"]
        if amount < loan_plan.min_amount or amount > loan_plan.max_amount:
            raise DRFValidationError({
                "amount": [f"Choose an amount between {loan_plan.min_amount} and {loan_plan.max_amount} for your current plan."]
            })

        user = request.user
        with db_transaction.atomic():
            application = LoanApplication.objects.create(
                user=user,
                loan_plan=loan_plan,
                email=user.email,
                phone_number=user.phone_number,
                country_name=user.country.name if user.country else "",
                full_name=serializer.validated_data["full_name"],
                age=serializer.validated_data["age"],
                source_of_income=serializer.validated_data["source_of_income"],
                repayment_method=serializer.validated_data["repayment_method"],
                security=serializer.validated_data.get("security", ""),
                amount=amount,
            )
            user.wallet.credit(
                wallet_type="account",
                amount=amount,
                transaction_type=Transaction.TransactionType.LOAN_DISBURSEMENT,
                description=f"Loan disbursement ({loan_plan.name})",
            )

        return Response(LoanApplicationSerializer(application, context={"request": request}).data, status=201)


class MyLoanApplicationsView(generics.ListAPIView):
    """GET /api/loans/applications/ — the caller's own loan history, most recent first."""
    serializer_class = LoanApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return LoanApplication.objects.filter(user=self.request.user)