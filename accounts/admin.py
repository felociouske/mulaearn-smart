from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Country, User


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = (
        "name", "code", "currency_code", "currency_symbol",
        "exchange_rate_to_kes", "activation_fee", "is_international_bucket",
    )
    list_editable = ("activation_fee",)
    search_fields = ("name", "code")


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("EasyEarn profile", {"fields": ("phone_number", "country", "referral_code", "referred_by")}),
        ("Activation", {"fields": ("is_activated", "activated_at")}),
    )
    readonly_fields = ("referral_code", "activated_at")
    list_display = ("username", "email", "phone_number", "country", "is_activated", "is_active", "date_joined")
    list_filter = ("country", "is_activated", "is_active", "is_staff")
    search_fields = ("username", "email", "phone_number", "referral_code")
    actions = ["manually_activate", "manually_deactivate"]

    @admin.action(description="Manually activate selected users (bypasses payment)")
    def manually_activate(self, request, queryset):
        from django.utils import timezone

        updated = queryset.filter(is_activated=False).update(
            is_activated=True, activated_at=timezone.now()
        )
        self.message_user(request, f"Activated {updated} user(s).")

    @admin.action(description="Deactivate selected users (revoke activation)")
    def manually_deactivate(self, request, queryset):
        updated = queryset.filter(is_activated=True).update(is_activated=False, activated_at=None)
        self.message_user(request, f"Deactivated {updated} user(s).")