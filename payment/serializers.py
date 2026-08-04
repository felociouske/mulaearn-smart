from rest_framework import serializers

from .models import DepositRequest, WithdrawalRequest


class DepositRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepositRequest
        fields = ["id", "method", "amount", "currency_code", "proof_message", "status", "created_at"]
        # method is read-only — CreateDepositRequestView always forces it to
        # PaymentMethod.MANUAL server-side (this serializer is only used for
        # the manual-proof flow; the Daraja STK push endpoint creates its
        # own DepositRequest directly with method=AUTOMATIC_DARAJA). Since
        # it's never actually meant to come from the client, requiring it
        # as input just broke every manual submission with a confusing
        # "this field is required" error the frontend never sent.
        read_only_fields = ["id", "method", "status", "created_at"]


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