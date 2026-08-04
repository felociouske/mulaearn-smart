from django.urls import path

from .views import MyWalletView, MyTransactionsView

urlpatterns = [
    path("me/", MyWalletView.as_view(), name="my-wallet"),
    path("transactions/", MyTransactionsView.as_view(), name="my-transactions"),
]