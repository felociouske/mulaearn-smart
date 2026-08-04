from django.urls import path

from .views import UnlockedProfilesView

urlpatterns = [
    path("unlocked/", UnlockedProfilesView.as_view(), name="unlocked-profiles"),
]