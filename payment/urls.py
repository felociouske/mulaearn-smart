from django.urls import path

from .views import (
    CreateDepositRequestView, MyDepositRequestsView,
    InitiateDepositBluepayPushView, DepositStatusView,
    CreateWithdrawalRequestView, MyWithdrawalRequestsView,
    # InitiateDepositSTKPushView, DarajaCallbackView,  # Daraja — dormant, kept
    # in views.py for reference/rollback only.
)

urlpatterns = [
    path("deposits/", MyDepositRequestsView.as_view(), name="my-deposits"),
    path("deposits/create/", CreateDepositRequestView.as_view(), name="create-deposit"),
    path("deposits/stkpush/", InitiateDepositBluepayPushView.as_view(), name="deposit-stkpush"),
    path("deposits/<int:pk>/status/", DepositStatusView.as_view(), name="deposit-status"),
    # path("deposits/daraja-callback/", DarajaCallbackView.as_view(), name="daraja-callback"),
    # ^ Daraja callback route removed — BluePay's webhook (/api/bluepay/callback/)
    # now handles this for both deposits and activation.
    path("withdrawals/", MyWithdrawalRequestsView.as_view(), name="my-withdrawals"),
    path("withdrawals/create/", CreateWithdrawalRequestView.as_view(), name="create-withdrawal"),
]