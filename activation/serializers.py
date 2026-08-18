from rest_framework import serializers

from .models import (
    ActivationSubmission,
    GatewayGroup,
    GhanaNigeriaPaymentGateway,
    KenyaPaymentGateway,
    OtherPaymentGateway,
    PaymentGateway,
    UgandaTanzaniaPaymentGateway,
)


class KenyaPaymentGatewaySerializer(serializers.ModelSerializer):
    class Meta:
        model = KenyaPaymentGateway
        fields = [
            "id", "group", "display_name", "description",
            "is_automatic", "till_number", "paybill_number", "account_reference", "order",
        ]


class UgandaTanzaniaPaymentGatewaySerializer(serializers.ModelSerializer):
    class Meta:
        model = UgandaTanzaniaPaymentGateway
        fields = ["id", "group", "display_name", "description", "recipient_name", "recipient_phone", "order"]


class GhanaNigeriaPaymentGatewaySerializer(serializers.ModelSerializer):
    class Meta:
        model = GhanaNigeriaPaymentGateway
        fields = ["id", "group", "display_name", "description", "eversend_link", "recipient_name", "order"]


class OtherPaymentGatewaySerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherPaymentGateway
        fields = ["id", "group", "display_name", "description", "recipient_name", "recipient_phone", "order"]


# Single dict driving "which serializer applies to this group" — used by
# both activation.views and payment.views so the two apps can never
# render different fields for the same gateway.
GROUP_SERIALIZER = {
    GatewayGroup.KENYA: KenyaPaymentGatewaySerializer,
    GatewayGroup.UGANDA_TANZANIA: UgandaTanzaniaPaymentGatewaySerializer,
    GatewayGroup.GHANA_NIGERIA: GhanaNigeriaPaymentGatewaySerializer,
    GatewayGroup.OTHER: OtherPaymentGatewaySerializer,
}


def serializer_for_group(group):
    return GROUP_SERIALIZER[group]


class ActivationSubmissionSerializer(serializers.ModelSerializer):
    # Client sends gateway_id; everything else (amount, currency, the
    # gateway_group/gateway_display_name snapshot) is server-derived so
    # nobody can submit a fee lower than what's configured for their
    # country, or misattribute which rail they used.
    gateway_id = serializers.PrimaryKeyRelatedField(
        queryset=PaymentGateway.objects.filter(is_active=True), source="gateway", write_only=True
    )

    class Meta:
            model = ActivationSubmission
            fields = [
                "id", "gateway_id", "gateway_group", "gateway_display_name",
                "amount", "currency_code", "reference_code", "proof_message",
                "bluepay_receipt_number",
                "status", "admin_notes", "created_at", "reviewed_at",
            ]
            read_only_fields = [
                "id", "gateway_group", "gateway_display_name", "amount", "currency_code",
                "bluepay_receipt_number",
                "status", "admin_notes", "created_at", "reviewed_at",
            ]