"""
ASGI config for mulaearn_backend project.

Serves BOTH normal HTTP (Django/DRF) and WebSockets (notifications) from the
same process, so only one server needs to run.
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mulaearn_backend.settings")

# Must run BEFORE importing anything that touches models, otherwise Django
# raises "apps aren't loaded yet".
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from notifications.routing import websocket_urlpatterns  # noqa: E402
from notifications.ws_auth import JWTAuthMiddleware  # noqa: E402

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddleware(URLRouter(websocket_urlpatterns)),
})