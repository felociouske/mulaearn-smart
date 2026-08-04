from rest_framework import serializers

from .models import ActivationSubmission, PaymentGateway


class PaymentGatewaySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentGateway
        fields = [
            "id", "method_type", "display_name", "is_automatic",
            "till_number", "paybill_number", "account_reference",
            "recipient_name", "recipient_phone", "instructions", "order",
        ]


class ActivationSubmissionSerializer(serializers.ModelSerializer):
    # Client sends gateway_id; everything else server-derived (amount,
    # currency, method_type) so nobody can submit a fee lower than what's
    # configured for their country.
    gateway_id = serializers.PrimaryKeyRelatedField(
        queryset=PaymentGateway.objects.filter(is_active=True), source="gateway", write_only=True
    )
    gateway = PaymentGatewaySerializer(read_only=True)

    class Meta:
        model = ActivationSubmission
        fields = [
            "id", "gateway", "gateway_id", "method_type", "amount", "currency_code",
            "reference_code", "proof_message", "status", "admin_notes",
            "created_at", "reviewed_at",
        ]
        read_only_fields = [
            "id", "method_type", "amount", "currency_code", "status",
            "admin_notes", "created_at", "reviewed_at",
        ]
