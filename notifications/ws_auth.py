"""
JWT authentication for WebSockets. Browsers can't set an Authorization
header on a WebSocket, so the frontend passes the SAME access token your
REST API already uses as a query param: ws://host/ws/notifications/?token=<access>
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def _get_user(raw_token):
    User = get_user_model()
    try:
        token = AccessToken(raw_token)  # verifies signature AND expiry
        user = User.objects.get(pk=token[api_settings.USER_ID_CLAIM])
    except (TokenError, User.DoesNotExist, KeyError, ValueError):
        return AnonymousUser()
    return user if user.is_active else AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query = parse_qs(scope.get("query_string", b"").decode())
        raw_token = (query.get("token") or [None])[0]
        scope["user"] = await _get_user(raw_token) if raw_token else AnonymousUser()
        return await super().__call__(scope, receive, send)