from django.urls import path

from .views import MySessionsView, SessionDetailView, StartOrResumeSessionView, SendMessageView

urlpatterns = [
    path("sessions/", MySessionsView.as_view(), name="my-sessions"),
    path("sessions/<int:session_id>/", SessionDetailView.as_view(), name="session-detail"),
    path("profiles/<int:profile_id>/start/", StartOrResumeSessionView.as_view(), name="start-session"),
    path("sessions/<int:session_id>/messages/", SendMessageView.as_view(), name="send-message"),
]