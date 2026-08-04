from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction as db_transaction
from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsActivated
from wallets.models import Transaction
from .models import Plan, PlanCategory, PlanPurchase
from .serializers import PlanPurchaseSerializer, PlanSerializer


class PlanListView(generics.ListAPIView):
    """
    GET /api/plans/                    — every active plan, all categories, cheapest-first within each.
    GET /api/plans/?category=chat      — just Chat plans (also app_review, movie_review).
    """
    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Plan.objects.filter(is_active=True).prefetch_related("features")
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)
        return queryset


class PurchasePlanView(APIView):
    """
    POST /api/plans/<plan_id>/purchase/
    Debits deposit_balance for the plan price, deactivates any previous
    active PlanPurchase IN THE SAME CATEGORY ONLY (buying a Chat plan
    doesn't touch an existing active App-review plan — the three
    categories are independent), and creates the new one. The referrals
    app's signal picks up the new PlanPurchase automatically and credits
    the referrer's 70% commission if applicable.
    """
    permission_classes = [permissions.IsAuthenticated, IsActivated]

    def post(self, request, plan_id):
        try:
            plan = Plan.objects.get(pk=plan_id, is_active=True)
        except Plan.DoesNotExist:
            return Response({"detail": "Plan not found."}, status=404)

        try:
            with db_transaction.atomic():
                request.user.wallet.debit(
                    wallet_type="deposit",
                    amount=plan.price,
                    transaction_type=Transaction.TransactionType.PLAN_PURCHASE,
                    description=f"Purchased {plan.name}",
                )
                PlanPurchase.objects.filter(
                    user=request.user, is_active=True, plan__category=plan.category
                ).update(is_active=False)
                purchase = PlanPurchase.objects.create(user=request.user, plan=plan, price_paid=plan.price)
        except DjangoValidationError as e:
            # Most likely cause: insufficient deposit_balance.
            raise DRFValidationError(e.messages if hasattr(e, "messages") else str(e))

        return Response(PlanPurchaseSerializer(purchase, context={"request": request}).data, status=201)


class MyActivePlansView(APIView):
    """
    GET /api/plans/me/
    The caller's active plan in EACH category (was a single plan before —
    now a user can hold one active plan per category at once):
        {"app_review": {...} | null, "movie_review": {...} | null, "chat": {...} | null}
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        purchases = PlanPurchase.objects.filter(user=request.user, is_active=True).select_related("plan")
        by_category = {choice: None for choice in PlanCategory.values}
        for purchase in purchases:
            by_category[purchase.plan.category] = PlanPurchaseSerializer(purchase, context={"request": request}).data
        return Response(by_category)