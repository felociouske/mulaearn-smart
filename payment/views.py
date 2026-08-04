from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsActivated
from . import daraja
from .models import DepositRequest, WithdrawalRequest, PaymentMethod
from .serializers import DepositRequestSerializer, WithdrawalRequestSerializer


class CreateDepositRequestView(generics.CreateAPIView):
    """
    POST /api/payments/deposits/create/
    Manual deposits land here as PENDING and wait for you to approve them
    in admin (which credits deposit_balance). Automatic Daraja deposits
    will get their own callback endpoint later — not built yet, since
    that needs real Daraja credentials to test against.
    """
    serializer_class = DepositRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, method=PaymentMethod.MANUAL)


class MyDepositRequestsView(generics.ListAPIView):
    serializer_class = DepositRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DepositRequest.objects.filter(user=self.request.user)


class InitiateDepositSTKPushView(APIView):
    """
    POST /api/payments/deposits/stkpush/  { "amount": 100 }
    Creates a pending DepositRequest, triggers the till-number STK push,
    and returns immediately — the user gets a prompt on their phone to
    enter their M-Pesa PIN. The deposit isn't credited yet at this point;
    that only happens once Safaricom calls DarajaCallbackView below.
    KES only (Daraja doesn't support other currencies), so this assumes
    the caller is in Kenya — same as your Nexcribe STK integration.
    """
    permission_classes = [permissions.IsAuthenticated, IsActivated]

    def post(self, request):
        amount = request.data.get("amount")
        if not amount or int(amount) <= 0:
            raise DRFValidationError({"amount": ["Enter a whole-number amount in KES greater than 0."]})

        if not request.user.phone_number:
            raise DRFValidationError({"detail": ["No phone number on file — add one before depositing."]})

        deposit = DepositRequest.objects.create(
            user=request.user,
            method=PaymentMethod.AUTOMATIC_DARAJA,
            amount=amount,
            currency_code="KES",
        )

        try:
            result = daraja.initiate_stk_push(
                phone_number=request.user.phone_number,
                amount=amount,
                account_reference=request.user.username,
            )
        except daraja.DarajaError as e:
            deposit.status = "rejected"
            deposit.save(update_fields=["status"])
            raise DRFValidationError({"detail": [f"Couldn't start the M-Pesa prompt: {e}"]})

        deposit.daraja_checkout_request_id = result["CheckoutRequestID"]
        deposit.save(update_fields=["daraja_checkout_request_id"])

        return Response({
            "deposit_id": deposit.id,
            "checkout_request_id": result["CheckoutRequestID"],
            "message": "Check your phone and enter your M-Pesa PIN to complete the payment.",
        }, status=202)


class DepositStatusView(generics.RetrieveAPIView):
    """
    GET /api/payments/deposits/<id>/status/
    Poll this after InitiateDepositSTKPushView while waiting for the user
    to complete (or cancel) the M-Pesa prompt on their phone.
    """
    serializer_class = DepositRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DepositRequest.objects.filter(user=self.request.user)


class DarajaCallbackView(APIView):
    """
    POST /api/payments/deposits/daraja-callback/
    Safaricom calls this directly — no user auth involved, so this is
    deliberately AllowAny with no authentication classes. Always returns
    HTTP 200 with {"ResultCode": 0} regardless of what happened on our
    side; Safaricom only cares that we acknowledged receipt, and retries
    the callback repeatedly if we don't return 200 — returning an error
    status here would cause duplicate callback storms, not a fix.
    Actual failures are logged, not raised.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        import logging

        logger = logging.getLogger(__name__)

        try:
            callback = request.data["Body"]["stkCallback"]
            checkout_request_id = callback["CheckoutRequestID"]
            result_code = callback["ResultCode"]

            deposit = DepositRequest.objects.filter(
                daraja_checkout_request_id=checkout_request_id,
                status="pending",
            ).first()

            if not deposit:
                logger.warning("Daraja callback for unknown/already-resolved CheckoutRequestID: %s", checkout_request_id)
                return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

            if result_code == 0:
                items = {
                    item["Name"]: item.get("Value")
                    for item in callback.get("CallbackMetadata", {}).get("Item", [])
                }
                deposit.daraja_receipt_number = str(items.get("MpesaReceiptNumber", ""))
                deposit.save(update_fields=["daraja_receipt_number"])
                deposit.approve()
            else:
                deposit.status = "rejected"
                deposit.save(update_fields=["status"])

        except Exception:
            logger.exception("Error processing Daraja callback payload: %s", request.data)

        # Always 200 — see docstring.
        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})


class CreateWithdrawalRequestView(generics.CreateAPIView):
    """
    POST /api/payments/withdrawals/create/

    Runs two checks before saving, both surfaced as clean 400 errors
    instead of silently creating a request that can never be fulfilled:

      1. WithdrawalRequest.clean() — the Ksh 200-equivalent minimum.
      2. A live balance check against the wallet_type requested — this
         was previously MISSING, and was the root cause of "withdraw
         doesn't work": a user could request more than they had, the
         request would be accepted as "pending", and it would only fail
         (with an uncaught error that crashed the admin bulk-approve
         action) once an admin tried to approve it — by which point the
         user had already been sitting on a stuck request with no
         explanation. Now it's rejected immediately, with a clear reason,
         same as the minimum-amount check.
    """
    serializer_class = WithdrawalRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsActivated]

    def perform_create(self, serializer):
        user = self.request.user
        wallet_type = serializer.validated_data["wallet_type"]
        amount = serializer.validated_data["amount"]

        current_balance = {
            "account": user.wallet.account_balance,
            "yield": user.wallet.yield_balance,
        }.get(wallet_type)

        if current_balance is None:
            raise DRFValidationError({"wallet_type": [f"Unknown wallet_type '{wallet_type}'."]})

        if amount > current_balance:
            raise DRFValidationError({
                "amount": [
                    f"Insufficient balance — your {wallet_type} balance is "
                    f"{current_balance} {serializer.validated_data.get('currency_code', '')}, "
                    f"you requested {amount}."
                ]
            })

        if not user.phone_number:
            raise DRFValidationError({"detail": ["No phone number on file — contact customer care to set one before withdrawing."]})

        # destination_details is always the user's own registered phone
        # number — never anything the client sends (see the serializer's
        # read_only_fields comment). Changing the payout number requires
        # contacting customer care, who update phone_number directly.
        instance = serializer.save(user=user, destination_details=user.phone_number)
        try:
            instance.full_clean(exclude=["status", "reviewed_by", "reviewed_at"])
        except DjangoValidationError as e:
            instance.delete()
            raise DRFValidationError(e.message_dict if hasattr(e, "message_dict") else e.messages)


class MyWithdrawalRequestsView(generics.ListAPIView):
    serializer_class = WithdrawalRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WithdrawalRequest.objects.filter(user=self.request.user)