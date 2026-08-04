from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, Country
from .serializers import RegisterSerializer, UserSerializer, CountrySerializer, UpdateProfileSerializer


class RegisterView(generics.CreateAPIView):
    """
    POST /api/accounts/register/
    Public endpoint — no auth required to sign up. Returns JWT tokens
    immediately on success so the frontend can log the user straight in
    without a separate login round-trip.
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=201,
        )


class MeView(APIView):
    """GET /api/accounts/me/ — the logged-in user's own profile. PATCH to edit email/phone."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UpdateProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class CountryListView(generics.ListAPIView):
    """GET /api/accounts/countries/ — public, used to populate the sign-up country dropdown."""
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = [permissions.AllowAny]