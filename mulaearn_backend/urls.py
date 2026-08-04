from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/accounts/", include("accounts.urls")),
    path("api/activation/", include("activation.urls")),
    path("api/wallets/", include("wallets.urls")),
    path("api/plans/", include("plans.urls")),
    path("api/chat-profiles/", include("chat_profiles.urls")),
    path("api/chats/", include("chat.urls")),
    path("api/surveys/", include("surveys.urls")),
    path("api/wheel/", include("wheel.urls")),
    path("api/reviews/", include("reviews.urls")),
    path("api/payments/", include("payment.urls")),
    path("api/referrals/", include("referrals.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)