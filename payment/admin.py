from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import DepositRequest, WithdrawalRequest


@admin.register(DepositRequest)
class DepositRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "method", "gateway_display_name", "amount", "currency_code", "status", "created_at")
    list_filter = ("method", "gateway_group", "status", "currency_code")
    search_fields = ("user__username",)
    # "reject_selected" is now a real method below — this was missing before,
    # which is why "Reject" never showed up in the admin dropdown.
    actions = ["approve_selected", "reject_selected"]

    @admin.action(description="Approve selected deposit requests")
    def approve_selected(self, request, queryset):
        succeeded, failed = 0, []
        # .filter(status="pending") lets an admin multi-select a mixed batch
        # (pending + already-approved) without double-processing anything.
        for deposit in queryset.filter(status="pending"):
            try:
                deposit.approve(reviewed_by=request.user)
                succeeded += 1
            except ValidationError as e:
                # Collect failures instead of raising immediately, so one bad
                # row doesn't stop the rest of the batch from being approved.
                failed.append(f"#{deposit.pk} ({deposit.user.username}): {e}")

        if succeeded:
            self.message_user(request, f"Approved {succeeded} deposit request(s).")
        for msg in failed:
            self.message_user(request, msg, level="ERROR")

    @admin.action(description="Reject selected deposit requests")
    def reject_selected(self, request, queryset):
        # NOTE: assumes DepositRequest.reject(reviewed_by=...) exists and
        # behaves like WithdrawalRequest.reject() below — a plain status
        # transition with no ValidationError path. If your reject() can
        # raise (e.g. can't reject an already-settled deposit), wrap this
        # in try/except ValidationError the same way approve_selected is.
        count = 0
        for deposit in queryset.filter(status="pending"):
            deposit.reject(reviewed_by=request.user)
            count += 1
        self.message_user(request, f"Rejected {count} deposit request(s).")


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "wallet_type", "amount", "currency_code", "status", "created_at")
    list_filter = ("wallet_type", "status", "currency_code")
    search_fields = ("user__username",)
    actions = ["approve_selected", "reject_selected"]

    @admin.action(description="Approve selected withdrawal requests")
    def approve_selected(self, request, queryset):
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