from django.contrib import admin

from .models import (
    ActivationSubmission,
    GhanaNigeriaPaymentGateway,
    KenyaPaymentGateway,
    OtherPaymentGateway,
    UgandaTanzaniaPaymentGateway,
)


class BaseGatewayAdmin(admin.ModelAdmin):
    """
    Shared list-view behaviour for all four gateway admins below — this is
    the "update payment methods with ease" screen: tick is_active, reorder,
    edit description, no code or deploy needed.
    """
    list_display = ("country", "display_name", "is_active", "order")
    list_filter = ("country", "is_active")
    list_editable = ("is_active", "order")
    search_fields = ("display_name", "country__name")
    ordering = ("country", "order")


@admin.register(KenyaPaymentGateway)
class KenyaPaymentGatewayAdmin(BaseGatewayAdmin):
    list_display = BaseGatewayAdmin.list_display + ("is_automatic",)
    list_filter = BaseGatewayAdmin.list_filter + ("is_automatic",)
    fieldsets = (
        (None, {"fields": ("country", "display_name", "is_automatic", "is_active", "order")}),
        ("Till / paybill details", {"fields": ("till_number", "paybill_number", "account_reference")}),
        ("Shown to the user — activation page AND deposit page", {"fields": ("description",)}),
    )


@admin.register(UgandaTanzaniaPaymentGateway)
class UgandaTanzaniaPaymentGatewayAdmin(BaseGatewayAdmin):
    fieldsets = (
        (None, {"fields": ("country", "display_name", "is_active", "order")}),
        ("Recipient details", {"fields": ("recipient_name", "recipient_phone")}),
        ("Shown to the user — activation page AND deposit page", {"fields": ("description",)}),
    )

@admin.register(GhanaNigeriaPaymentGateway)
class GhanaNigeriaPaymentGatewayAdmin(BaseGatewayAdmin):
    fieldsets = (
        (None, {"fields": ("country", "display_name", "is_active", "order")}),
        ("Eversend details", {"fields": ("eversend_link", "recipient_name")}),
        ("Shown to the user — activation page AND deposit page", {"fields": ("description",)}),
    )

@admin.register(OtherPaymentGateway)
class OtherPaymentGatewayAdmin(BaseGatewayAdmin):
    fieldsets = (
        (None, {"fields": ("country", "display_name", "is_active", "order")}),
        ("Recipient details", {"fields": ("recipient_name", "recipient_phone")}),
        ("Shown to the user — activation page AND deposit page", {"fields": ("description",)}),
    )

@admin.register(ActivationSubmission)
class ActivationSubmissionAdmin(admin.ModelAdmin):
    list_display = ("user", "gateway_display_name", "amount", "currency_code", "status", "created_at")
    list_filter = ("gateway_group", "status", "currency_code")
    search_fields = ("user__username", "user__email", "reference_code")
    readonly_fields = ("created_at", "reviewed_at", "reviewed_by", "gateway_group", "gateway_display_name")
    actions = ["approve_selected", "reject_selected"]

    @admin.action(description="Approve selected activation submissions")
    def approve_selected(self, request, queryset):
        count = 0
        for submission in queryset.filter(status="pending"):
            submission.approve(reviewed_by=request.user)
            count += 1
        self.message_user(request, f"Approved {count} activation submission(s).")

    @admin.action(description="Reject selected activation submissions")
    def reject_selected(self, request, queryset):
        count = 0
        for submission in queryset.filter(status="pending"):
            submission.reject(reviewed_by=request.user)
            count += 1
        self.message_user(request, f"Rejected {count} activation submission(s).")
