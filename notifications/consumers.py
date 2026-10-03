from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import Notification
from .push import BROADCAST_GROUP, user_group

# Custom close code the frontend watches for: "your token was bad/expired —
# refresh it, then reconnect". (4000-4999 is the app-defined range.)
CLOSE_UNAUTHORIZED = 4401


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """
    One socket per open browser tab. It joins two groups:
      - the user's private group   -> receives that user's own notifications
      - the shared broadcast group -> receives "refresh" nudges after an all-users send
    """

    async def connect(self):
        user = self.scope.get("user")
        # Accept first, THEN close on failure: closing before accept() gives the
        # browser a bare 403 with no code, so it couldn't tell "bad token" apart
        # from "server down" and would never know to refresh its token.
        await self.accept()

        if user is None or user.is_anonymous:
            await self.close(code=CLOSE_UNAUTHORIZED)
            return

        self.user_group = user_group(user.id)
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.channel_layer.group_add(BROADCAST_GROUP, self.channel_name)
        await self.send_json({"event": "connected", "unread_count": await self._unread_count(user.id)})

    async def disconnect(self, code):
        # user_group only exists if auth succeeded in connect()
        if hasattr(self, "user_group"):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)
            await self.channel_layer.group_discard(BROADCAST_GROUP, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # Keep-alive: proxies (Railway included) drop idle sockets, so the
        # client pings every ~30s and we answer.
        if content.get("action") == "ping":
            await self.send_json({"event": "pong"})

    # --- handlers: method name = group_send "type" with "." replaced by "_" ---
    async def notification_new(self, event):
        await self.send_json({
            "event": "notification",
            "notification": event["notification"],
            "unread_count": event["unread_count"],
        })

    async def notification_refresh(self, event):
        await self.send_json({"event": "refresh"})

    @database_sync_to_async
    def _unread_count(self, user_id):
        return Notification.objects.active().filter(user_id=user_id, is_read=False).count()