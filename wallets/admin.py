from django.contrib import admin

from .models import Wallet, Transaction


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "deposit_balance", "account_balance", "yield_balance", "total_yield_earned", "updated_at")
    search_fields = ("user__username", "user__email", "user__phone_number")
    readonly_fields = ("deposit_balance", "account_balance", "yield_balance", "total_yield_earned")
    # Balances are read-only in admin on purpose — always adjust via
    # Wallet.credit()/debit() (e.g. in the shell or an admin action) so an
    # audit Transaction row always gets created alongside the change.


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("wallet", "wallet_type", "transaction_type", "amount", "balance_after", "created_at")
    list_filter = ("wallet_type", "transaction_type")
    search_fields = ("wallet__user__username",)
    readonly_fields = [f.name for f in Transaction._meta.fields]  # ledger rows are immutable

    def has_add_permission(self, request):
        return False  # transactions are only ever created via Wallet.credit()/debit()

    def has_delete_permission(self, request, obj=None):
        return False