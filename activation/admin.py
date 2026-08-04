from django.contrib import admin

from .models import ActivationSubmission, PaymentGateway


@admin.register(PaymentGateway)
class PaymentGatewayAdmin(admin.ModelAdmin):
    """
    This is the "update payment gateways with ease" screen: add a row per
    country/rail, fill in till/paybill/phone + instructions, tick
    is_active. No code or deploy needed to add a country or change a
    till number.
    """
    list_display = ("country", "display_name", "method_type", "is_automatic", "is_active", "order")
    list_filter = ("country", "method_type", "is_automatic", "is_active")
    list_editable = ("is_active", "order")
    search_fields = ("display_name", "country__name")
    ordering = ("country", "order")
    fieldsets = (
        (None, {"fields": ("country", "method_type", "display_name", "is_automatic", "is_active", "order")}),
        ("Destination details", {
            "fields": ("till_number", "paybill_number", "account_reference", "recipient_name", "recipient_phone"),
            "description": "Fill in only the fields this rail actually needs; leave the rest blank.",
        }),
        ("Instructions shown to the user", {"fields": ("instructions",)}),
    )


@admin.register(ActivationSubmission)
class ActivationSubmissionAdmin(admin.ModelAdmin):
    list_display = ("user", "method_type", "amount", "currency_code", "status", "created_at")
    list_filter = ("method_type", "status", "currency_code")
    search_fields = ("user__username", "user__email", "reference_code")
    readonly_fields = ("created_at", "reviewed_at", "reviewed_by")
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
