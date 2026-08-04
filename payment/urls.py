from django.urls import path

from .views import (
    CreateDepositRequestView, MyDepositRequestsView,
    InitiateDepositSTKPushView, DepositStatusView, DarajaCallbackView,
    CreateWithdrawalRequestView, MyWithdrawalRequestsView,
)

urlpatterns = [
    path("deposits/", MyDepositRequestsView.as_view(), name="my-deposits"),
    path("deposits/create/", CreateDepositRequestView.as_view(), name="create-deposit"),
    path("deposits/stkpush/", InitiateDepositSTKPushView.as_view(), name="deposit-stkpush"),
    path("deposits/<int:pk>/status/", DepositStatusView.as_view(), name="deposit-status"),
    path("deposits/daraja-callback/", DarajaCallbackView.as_view(), name="daraja-callback"),
    path("withdrawals/", MyWithdrawalRequestsView.as_view(), name="my-withdrawals"),
    path("withdrawals/create/", CreateWithdrawalRequestView.as_view(), name="create-withdrawal"),
]