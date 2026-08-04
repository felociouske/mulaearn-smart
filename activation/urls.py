from django.urls import path

from .views import MyActivationGatewaysView, MyActivationSubmissionsView, SubmitActivationView

urlpatterns = [
    path("gateways/", MyActivationGatewaysView.as_view(), name="activation-gateways"),
    path("submissions/", MyActivationSubmissionsView.as_view(), name="activation-submissions"),
    path("submit/", SubmitActivationView.as_view(), name="activation-submit"),
]
