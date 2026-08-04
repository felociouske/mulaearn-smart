from rest_framework import generics, permissions

from .models import get_unlocked_profiles_for
from .serializers import ChatProfileSerializer


class UnlockedProfilesView(generics.ListAPIView):
    """
    GET /api/chat-profiles/unlocked/
    The list a logged-in user sees at /chatting — only the profiles their
    current plan tier has unlocked (N lowest-paying, ascending).
    """
    serializer_class = ChatProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return get_unlocked_profiles_for(self.request.user)