from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError as DRFValidationError

from .models import ActivationStatus, ActivationSubmission, PaymentGateway
from .serializers import ActivationSubmissionSerializer, PaymentGatewaySerializer


class MyActivationGatewaysView(generics.ListAPIView):
    """
    GET /api/activation/gateways/
    Active payment options for the caller's own country, ordered for
    display. An empty list means the country isn't wired up yet — the
    frontend should fall back to a "Coming soon, contact support" message
    rather than an empty form.
    """
    serializer_class = PaymentGatewaySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.country_id:
            return PaymentGateway.objects.none()
        return PaymentGateway.objects.filter(country_id=user.country_id, is_active=True)


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
            method_type=gateway.method_type,
            amount=country.activation_fee,
            currency_code=country.currency_code,
        )
