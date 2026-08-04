from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import WalletSerializer, TransactionSerializer


class MyWalletView(APIView):
    """GET /api/wallets/me/ — the four balances for the dashboard."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(WalletSerializer(request.user.wallet).data)


class MyTransactionsView(generics.ListAPIView):
    """GET /api/wallets/transactions/ — full ledger history, newest first, for the dashboard's transaction list."""
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.user.wallet.transactions.all()