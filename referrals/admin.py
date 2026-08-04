from django.contrib import admin

from .models import ReferralCommission


@admin.register(ReferralCommission)
class ReferralCommissionAdmin(admin.ModelAdmin):
    list_display = ("referrer", "referred_user", "amount", "created_at")
    search_fields = ("referrer__username", "referred_user__username")
    readonly_fields = [f.name for f in ReferralCommission._meta.fields]

    def has_add_permission(self, request):
        return False