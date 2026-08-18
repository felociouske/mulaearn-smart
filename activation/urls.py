from django.urls import path

from .views import (
    ActivationSubmissionStatusView,
    InitiateActivationBluepayPushView,
    MyActivationGatewaysView,
    MyActivationSubmissionsView,
    SubmitActivationView,
)

urlpatterns = [
    path("gateways/", MyActivationGatewaysView.as_view(), name="activation-gateways"),
    path("submissions/", MyActivationSubmissionsView.as_view(), name="activation-submissions"),
    path("submissions/<int:pk>/status/", ActivationSubmissionStatusView.as_view(), name="activation-submission-status"),
    path("submit/", SubmitActivationView.as_view(), name="activation-submit"),
    path("bluepay/initiate/", InitiateActivationBluepayPushView.as_view(), name="activation-bluepay-initiate"),
]