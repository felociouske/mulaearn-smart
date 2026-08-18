from django.urls import path

from .views import BluepayCallbackView

urlpatterns = [
    path("callback/", BluepayCallbackView.as_view(), name="bluepay-callback"),
]