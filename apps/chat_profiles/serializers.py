from rest_framework import serializers

from .models import ChatProfile


class ChatProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatProfile
        fields = ["id", "name", "photo", "bio", "payout_amount_usd", "is_active", "is_online", "last_seen_at"]
        read_only_fields = fields
        # rate_per_message_kes intentionally excluded — that's an internal
        # payout mechanic, not something to expose to the browsing user.