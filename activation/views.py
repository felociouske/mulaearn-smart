from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ActivationStatus, ActivationSubmission, GROUP_MODEL, group_for_country
from .serializers import ActivationSubmissionSerializer, serializer_for_group


class MyActivationGatewaysView(APIView):
    """
    GET /api/activation/gateways/
    Active payment options for the caller's own country, ordered for
    display. An empty list means the country isn't wired up yet (or every
    row for it is currently inactive) — the frontend should fall back to
    a "Coming soon, contact support" message rather than an empty form.

    This is also the endpoint the DEPOSIT page calls (see payment app) —
    one query, one serializer, one description field, so activation and
    deposit can never show different text for the same payment method.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        country = request.user.country
        group = group_for_country(country)
        if not group:
            return Response([])

        model = GROUP_MODEL[group]
        serializer_class = serializer_for_group(group)
        queryset = model.objects.filter(country_id=country.id, is_active=True).order_by("order")
        return Response(serializer_class(queryset, many=True).data)


class MyActivationSubmissionsView(generics.ListAPIView):
    """GET /api/activation/submissions/ — the caller's own activation payment history."""
    serializer_class = ActivationSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ActivationSubmission.objects.filter(user=self.request.user)


class SubmitActivationView(generics.CreateAPIView):
    """
    POST /api/activation/submit/
    Body: {"gateway_id": 1, "reference_code": "QGH7...", "proof_message": "..."}

    Rejects if the user is already activated, already has a pending
    submission, or picked a gateway that doesn't belong to their own
    country (guards against a tampered gateway_id).
    """
    serializer_class = ActivationSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user

        if user.is_activated:
            raise DRFValidationError("Your account is already activated.")

        country = user.country
        if not country:
            raise DRFValidationError("Set your country before activating your account.")

        if ActivationSubmission.objects.filter(user=user, status=ActivationStatus.PENDING).exists():
            raise DRFValidationError("You already have a pending activation submission awaiting review.")

        gateway = serializer.validated_data["gateway"]
        if gateway.country_id != country.id:
            raise DRFValidationError("That payment option isn't available for your country.")

        serializer.save(
            user=user,
            gateway_group=gateway.group,
            gateway_display_name=gateway.display_name,
            amount=country.activation_fee,
            currency_code=country.currency_code,
        )