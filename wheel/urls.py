from django.urls import path

from .views import SpinWheelView, WheelHistoryView, WheelStatusView

urlpatterns = [
    path("status/", WheelStatusView.as_view(), name="wheel-status"),
    path("spin/", SpinWheelView.as_view(), name="wheel-spin"),
    path("history/", WheelHistoryView.as_view(), name="wheel-history"),
]