from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from bluepay import client as bluepay_client
from bluepay.client import BluepayError

from .models import ActivationStatus, ActivationSubmission, GROUP_MODEL, KenyaPaymentGateway, group_for_country
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


class InitiateActivationBluepayPushView(APIView):
    """
    POST /api/activation/bluepay/initiate/
    Creates a PENDING ActivationSubmission tagged to Kenya's active
    automatic gateway row, THEN triggers a BluePay STK push — the
    submission is created before the push fires (not after) specifically
    so its own id is available to build the account_reference BluePay
    needs to correlate the eventual webhook back to it. Mirrors
    payment.views.InitiateDepositBluepayPushView (same create-then-push
    order, same error handling shape) — keep the two in sync if either
    changes.

    Activation isn't granted at this point — is_activated only flips
    once BluepayCallbackView (bluepay/views.py) calls submission.approve()
    after BluePay's webhook confirms the payment.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user

        if user.is_activated:
            raise DRFValidationError({"detail": ["Your account is already activated."]})

        country = user.country
        if not country:
            raise DRFValidationError({"detail": ["Set your country before activating your account."]})

        if ActivationSubmission.objects.filter(user=user, status=ActivationStatus.PENDING).exists():
            raise DRFValidationError({"detail": ["You already have a pending activation submission awaiting review."]})

        if not user.phone_number:
            raise DRFValidationError({"detail": ["No phone number on file — add one before activating."]})

        # BluePay/M-Pesa is Kenya-only for now, same constraint the
        # deposit STK flow has — this assumes the caller is in Kenya,
        # which the gateway lookup below enforces implicitly (an empty
        # queryset for any other country falls through to the "not
        # available" error rather than silently succeeding).
        gateway = (
            KenyaPaymentGateway.objects.filter(country_id=country.id, is_automatic=True, is_active=True)
            .order_by("order")
            .first()
        )
        if not gateway:
            raise DRFValidationError({"detail": ["Instant activation isn't available right now — use the manual option below."]})

        submission = ActivationSubmission.objects.create(
            user=user,
            gateway=gateway,
            gateway_group=gateway.group,
            gateway_display_name=gateway.display_name,
            amount=country.activation_fee,
            currency_code=country.currency_code,
        )

        try:
            result = bluepay_client.initiate_stk_push(
                phone_number=user.phone_number,
                amount=country.activation_fee,
                account_reference=f"BP-{submission.id}",
            )
        except BluepayError as e:
            # Push never left our server, so there's nothing for a
            # webhook to resolve later — mark it rejected immediately
            # rather than leaving a PENDING row that can never complete
            # (which would also permanently block the user from trying
            # again, since SubmitActivationView/this view both refuse a
            # second attempt while one is PENDING).
            submission.status = ActivationStatus.REJECTED
            submission.admin_notes = f"BluePay STK push failed: {e}"
            submission.save(update_fields=["status", "admin_notes"])
            raise DRFValidationError({"detail": [f"Couldn't start the M-Pesa prompt: {e}"]})

        submission.bluepay_stk_request_id = str(result["stk_request_id"])
        submission.bluepay_checkout_request_id = result["checkout_request_id"]
        submission.save(update_fields=["bluepay_stk_request_id", "bluepay_checkout_request_id"])

        return Response({
            "submission_id": submission.id,
            "checkout_request_id": result["checkout_request_id"],
            "message": "Check your phone and enter your M-Pesa PIN to complete activation.",
        }, status=202)


class ActivationSubmissionStatusView(generics.RetrieveAPIView):
    """
    GET /api/activation/submissions/<id>/status/
    Poll this after InitiateActivationBluepayPushView while waiting for
    BluePay's webhook — mirrors payment.views.DepositStatusView. Scoped
    to the caller's own submissions so one user can't poll another's
    activation status by guessing ids.
    """
    serializer_class = ActivationSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ActivationSubmission.objects.filter(user=self.request.user)