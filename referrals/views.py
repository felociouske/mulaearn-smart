from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ReferralCommission
from .serializers import ReferralCommissionSerializer, ReferredUserSerializer


class MyReferredUsersView(generics.ListAPIView):
    """
    GET /api/referrals/referred-users/
    Everyone who signed up under the caller's referral code — including
    ones who never purchased a plan (those just show 0 commission
    earned). Email/phone come back masked (see ReferredUserSerializer).
    """
    serializer_class = ReferredUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.user.referrals.all().order_by("-date_joined")

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "referrer": self.request.user}


class MyReferralCommissionsView(generics.ListAPIView):
    """GET /api/referrals/commissions/ — every commission the caller has earned from people they referred."""
    serializer_class = ReferralCommissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ReferralCommission.objects.filter(referrer=self.request.user)


class MyReferralSummaryView(APIView):
    """
    GET /api/referrals/summary/
    Quick stats for the dashboard: how many people signed up under this
    user's code, and how many of those have actually purchased a plan
    (only paying referrals earn commission).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        referred_qs = request.user.referrals.all()  # related_name from User.referred_by
        return Response(
            {
                "referral_code": request.user.referral_code,
                "total_referred_users": referred_qs.count(),
                "paying_referrals": referred_qs.filter(plan_purchases__isnull=False).distinct().count(),
                "total_commission_earned": str(request.user.wallet.yield_balance),
            }
        )