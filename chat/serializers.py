from rest_framework import serializers

from .models import ChatSession, ChatMessage
from chat_profiles.serializers import ChatProfileSerializer


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["id", "sender", "content", "amount_credited", "sent_at"]
        read_only_fields = ["id", "amount_credited", "sent_at"]


class ChatSessionSerializer(serializers.ModelSerializer):
    chat_profile = ChatProfileSerializer(read_only=True)
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatSession
        fields = ["id", "chat_profile", "is_active", "started_at", "messages"]
        read_only_fields = fields