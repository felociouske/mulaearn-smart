from rest_framework import serializers

from activation.models import PaymentGateway
from .models import DepositRequest, WithdrawalRequest


class DepositRequestSerializer(serializers.ModelSerializer):
    # Client sends gateway_id for manual deposits (which of their
    # country's active payment methods they used) — required for manual,
    # ignored for the Daraja STK flow (that path creates its own
    # DepositRequest directly in InitiateDepositSTKPushView, not through
    # this serializer's create path).
    gateway_id = serializers.PrimaryKeyRelatedField(
        queryset=PaymentGateway.objects.filter(is_active=True), source="gateway",
        write_only=True, required=False, allow_null=True,
    )

    class Meta:
        model = DepositRequest
        fields = [
            "id", "method", "amount", "currency_code", "gateway_id",
            "gateway_group", "gateway_display_name", "proof_message", "status", "created_at",
        ]
        # method is read-only — CreateDepositRequestView always forces it to
        # PaymentMethod.MANUAL server-side; the Daraja STK push endpoint
        # creates its own DepositRequest directly with method=AUTOMATIC_DARAJA.
        read_only_fields = ["id", "method", "gateway_group", "gateway_display_name", "status", "created_at"]


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalRequest
        fields = ["id", "wallet_type", "amount", "currency_code", "destination_details", "status", "created_at"]
        # destination_details is read-only here — it's set server-side from
        # the user's registered phone_number in CreateWithdrawalRequestView,
        # never accepted from the client. Changing where withdrawals go
        # is a "contact customer care" action, not a form field, precisely
        # so a compromised session/tampered request can't redirect payouts.
        read_only_fields = ["id", "status", "created_at", "destination_details"]