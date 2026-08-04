from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import DepositRequest, WithdrawalRequest


@admin.register(DepositRequest)
class DepositRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "method", "amount", "currency_code", "status", "created_at")
    list_filter = ("method", "status", "currency_code")
    search_fields = ("user__username",)
    actions = ["approve_selected"]

    @admin.action(description="Approve selected deposit requests")
    def approve_selected(self, request, queryset):
        succeeded, failed = 0, []
        for deposit in queryset.filter(status="pending"):
            try:
                deposit.approve(reviewed_by=request.user)
                succeeded += 1
            except ValidationError as e:
                failed.append(f"#{deposit.pk} ({deposit.user.username}): {e}")

        if succeeded:
            self.message_user(request, f"Approved {succeeded} deposit request(s).")
        for msg in failed:
            self.message_user(request, msg, level="ERROR")


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "wallet_type", "amount", "currency_code", "status", "created_at")
    list_filter = ("wallet_type", "status", "currency_code")
    search_fields = ("user__username",)
    actions = ["approve_selected", "reject_selected"]

    @admin.action(description="Approve selected withdrawal requests")
    def approve_selected(self, request, queryset):
        # A single request with an insufficient balance (e.g. the wallet
        # dropped after the request was made, or an old request slipped
        # past the balance check that used to be missing) must not stop
        # the rest of the batch from being approved — each one gets its
        # own try/except and a clear message back to the admin.
        succeeded, failed = 0, []
        for w in queryset.filter(status="pending"):
            try:
                w.approve(reviewed_by=request.user)
                succeeded += 1
            except ValidationError as e:
                failed.append(f"#{w.pk} ({w.user.username}): {e}")

        if succeeded:
            self.message_user(request, f"Approved {succeeded} withdrawal request(s).")
        for msg in failed:
            self.message_user(request, msg, level="ERROR")

    @admin.action(description="Reject selected withdrawal requests")
    def reject_selected(self, request, queryset):
        count = 0
        for w in queryset.filter(status="pending"):
            w.reject(reviewed_by=request.user)
            count += 1
        self.message_user(request, f"Rejected {count} withdrawal request(s).")