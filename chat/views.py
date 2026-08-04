from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from chat_profiles.models import ChatProfile, get_unlocked_profiles_for
from .models import ChatSession, ChatMessage
from .serializers import ChatSessionSerializer, ChatMessageSerializer


class MySessionsView(generics.ListAPIView):
    """GET /api/chats/sessions/ — all of the caller's chat sessions, most recent first."""
    serializer_class = ChatSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChatSession.objects.filter(user=self.request.user).select_related("chat_profile").prefetch_related("messages")


class SessionDetailView(generics.RetrieveAPIView):
    """
    GET /api/chats/sessions/<id>/
    Used by the chat UI to poll for new messages (including staff replies
    sent through the admin) without refetching every session the user has.
    """
    serializer_class = ChatSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "session_id"

    def get_queryset(self):
        return ChatSession.objects.filter(user=self.request.user).select_related("chat_profile").prefetch_related("messages")


class StartOrResumeSessionView(APIView):
    """
    POST /api/chats/profiles/<profile_id>/start/
    Starts a new session, or returns the existing active one — enforces
    that the profile is actually unlocked for the caller's plan tier
    (blocks a user from chatting a profile they haven't paid to access,
    even if they guess the ID).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, profile_id):
        unlocked_ids = set(get_unlocked_profiles_for(request.user).values_list("id", flat=True))
        if profile_id not in unlocked_ids:
            raise PermissionDenied("This chat profile isn't unlocked on your current plan.")

        profile = ChatProfile.objects.get(pk=profile_id)
        session, _ = ChatSession.objects.get_or_create(user=request.user, chat_profile=profile, is_active=True)
        return Response(ChatSessionSerializer(session).data)


class SendMessageView(APIView):
    """
    POST /api/chats/sessions/<session_id>/messages/  {"content": "..."}
    Only the session's owner can post as sender=user; credits
    account_balance instantly per message (if the profile's
    rate_per_message_kes is configured — see ChatProfile note).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        try:
            session = ChatSession.objects.get(pk=session_id, user=request.user, is_active=True)
        except ChatSession.DoesNotExist:
            raise PermissionDenied("No active session with that id for this user.")

        content = request.data.get("content", "").strip()
        if not content:
            raise ValidationError({"content": "This field may not be blank."})

        message = ChatMessage.objects.create(session=session, sender=ChatMessage.Sender.USER, content=content)
        message.credit_sender_if_applicable()
        return Response(ChatMessageSerializer(message).data, status=201)