from rest_framework import generics, permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification, NotificationType
from .serializers import NotificationSerializer


class NotificationPagination(PageNumberPagination):
    # Own pagination class so this app behaves the same regardless of what
    # DEFAULT_PAGINATION_CLASS the rest of the project uses (or doesn't).
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def _mine(request):
    """The caller's own, non-expired notifications. Every view starts from this — one user can never touch another's."""
    return Notification.objects.active().filter(user=request.user)


class NotificationListView(generics.ListAPIView):
    """
    GET /api/notifications/?type=survey,wheel&unread=true&page=2
    Newest first. `type` accepts a comma-separated list so the frontend can
    filter by a whole group (e.g. all "earnings") in one request.
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = NotificationPagination

    def get_queryset(self):
        qs = _mine(self.request)

        types = self.request.query_params.get("type")
        if types:
            valid = set(NotificationType.values)
            wanted = [t for t in types.split(",") if t in valid]  # ignore junk instead of erroring
            qs = qs.filter(type__in=wanted)

        if self.request.query_params.get("unread", "").lower() in ("1", "true", "yes"):
            qs = qs.filter(is_read=False)
        return qs


class UnreadCountView(APIView):
    """GET /api/notifications/unread-count/ -> {"unread_count": 3} — what the bell badge shows."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({"unread_count": _mine(request).filter(is_read=False).count()})


class MarkReadView(APIView):
    """POST /api/notifications/<id>/read/"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        # 404 (not 403) for other people's ids: don't reveal that an id exists.
        notification = generics.get_object_or_404(_mine(request), pk=pk)
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data)


class MarkAllReadView(APIView):
    """POST /api/notifications/mark-all-read/"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        updated = _mine(request).filter(is_read=False).update(is_read=True)
        return Response({"marked_read": updated, "unread_count": 0})


class NotificationDeleteView(generics.DestroyAPIView):
    """DELETE /api/notifications/<id>/"""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return _mine(self.request)