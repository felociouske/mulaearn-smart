from django.urls import path

from .views import (
    MarkAllReadView,
    MarkReadView,
    NotificationDeleteView,
    NotificationListView,
    UnreadCountView,
)

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("unread-count/", UnreadCountView.as_view(), name="notification-unread-count"),
    path("mark-all-read/", MarkAllReadView.as_view(), name="notification-mark-all-read"),
    path("<int:pk>/read/", MarkReadView.as_view(), name="notification-mark-read"),
    path("<int:pk>/", NotificationDeleteView.as_view(), name="notification-delete"),
]