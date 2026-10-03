"""
Live delivery over Django Channels. Every function here swallows its own
errors on purpose: a Redis hiccup must NEVER be able to break a wallet
credit, a loan disbursement or an admin save — the notification row is
already safely in the database and the frontend falls back to fetching it.
"""
import json
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.serializers.json import DjangoJSONEncoder

logger = logging.getLogger(__name__)

BROADCAST_GROUP = "notifications_broadcast"


def user_group(user_id):
    return f"notifications_user_{user_id}"


def _send(group, message):
    layer = get_channel_layer()
    if layer is None:  # CHANNEL_LAYERS not configured — nothing to push to
        return
    async_to_sync(layer.group_send)(group, message)


def push_notification(notification):
    """Pushes one new notification (+ fresh unread count) to that user's open sockets."""
    try:
        from .models import Notification
        from .serializers import NotificationSerializer

        data = NotificationSerializer(notification).data
        # JSON round-trip turns Decimal/datetime into plain strings, which every
        # channel layer (incl. msgpack-based Redis) can carry.
        payload = json.loads(json.dumps(data, cls=DjangoJSONEncoder))
        unread = Notification.objects.active().filter(user_id=notification.user_id, is_read=False).count()
        _send(user_group(notification.user_id), {
            "type": "notification.new",  # -> NotificationConsumer.notification_new
            "notification": payload,
            "unread_count": unread,
        })
    except Exception:
        logger.exception("Failed to push notification %s", getattr(notification, "pk", None))


def push_refresh_to_everyone():
    """
    Tiny "something new arrived, refetch" nudge to every connected socket.
    Used after a fan-out to all users: cheaper than pushing N full payloads.
    """
    try:
        _send(BROADCAST_GROUP, {"type": "notification.refresh"})
    except Exception:
        logger.exception("Failed to push broadcast refresh")