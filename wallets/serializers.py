from rest_framework import serializers

from .models import Wallet, Transaction


class WalletSerializer(serializers.ModelSerializer):
    total_withdrawn = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = [
            "deposit_balance", "account_balance", "yield_balance",
            "total_yield_earned", "total_withdrawn", "updated_at",
        ]
        read_only_fields = fields  # balances are NEVER writable via the API — only Wallet.credit()/debit() can change them

    def get_total_withdrawn(self, wallet):
        # Computed from approved WithdrawalRequests rather than a stored
        # counter — one less thing that can drift out of sync with reality.
        from decimal import Decimal

        from django.db.models import Sum

        from payment.models import WithdrawalRequest

        total = WithdrawalRequest.objects.filter(
            user=wallet.user, status="approved"
        ).aggregate(total=Sum("amount"))["total"]
        return str((total or Decimal("0.00")).quantize(Decimal("0.01")))


class TransactionSerializer(serializers.ModelSerializer):
    transaction_type_display = serializers.CharField(source="get_transaction_type_display", read_only=True)

    class Meta:
        model = Transaction
        fields = ["id", "wallet_type", "transaction_type", "transaction_type_display", "amount", "balance_after", "description", "created_at"]
        read_only_fields = fields