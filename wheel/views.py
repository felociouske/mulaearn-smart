import random
from datetime import date

from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsActivated
from wallets.models import Transaction

from .models import MAX_SPINS_PER_DAY, WHEEL_OUTCOMES, WheelSpin
from .serializers import WheelSpinSerializer


class WheelStatusView(APIView):
    """GET /api/wheel/status/ — how many of today's 3 spins are left."""
    permission_classes = [permissions.IsAuthenticated, IsActivated]

    def get(self, request):
        used_today = WheelSpin.objects.filter(user=request.user, date=date.today()).count()
        return Response({
            "spins_used_today": used_today,
            "spins_remaining_today": max(0, MAX_SPINS_PER_DAY - used_today),
            "max_spins_per_day": MAX_SPINS_PER_DAY,
        })


class SpinWheelView(APIView):
    """
    POST /api/wheel/spin/
    Picks a weighted random outcome from WHEEL_OUTCOMES, converts it to
    the user's local currency, credits the wallet, and records the spin.
    Enforces MAX_SPINS_PER_DAY (3) — scoped to WheelSpin rows dated today,
    so it naturally resets at midnight without a separate cron job.
    """
    permission_classes = [permissions.IsAuthenticated, IsActivated]

    def post(self, request):
        today = date.today()
        used_today = WheelSpin.objects.filter(user=request.user, date=today).count()
        if used_today >= MAX_SPINS_PER_DAY:
            raise DRFValidationError({
                "detail": [f"You've used all {MAX_SPINS_PER_DAY} spins for today. Come back tomorrow."]
            })

        amounts, weights = zip(*WHEEL_OUTCOMES)
        amount_kes = random.choices(amounts, weights=weights, k=1)[0]

        country = request.user.country
        credited_amount = country.convert_from_kes(amount_kes) if country else amount_kes
        currency_code = country.currency_code if country else "KES"

        spin = WheelSpin.objects.create(
            user=request.user,
            date=today,
            amount_kes=amount_kes,
            credited_amount=credited_amount,
            currency_code=currency_code,
        )
        request.user.wallet.credit(
            "account",
            credited_amount,
            Transaction.TransactionType.WHEEL_EARNING,
            description=f"Wheel spin: {amount_kes} KES",
        )

        return Response(
            {**WheelSpinSerializer(spin).data, "spins_remaining_today": MAX_SPINS_PER_DAY - used_today - 1},
            status=status.HTTP_201_CREATED,
        )


class WheelHistoryView(generics.ListAPIView):
    serializer_class = WheelSpinSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WheelSpin.objects.filter(user=self.request.user)