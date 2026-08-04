from django.contrib import admin

from .models import WheelSpin


@admin.register(WheelSpin)
class WheelSpinAdmin(admin.ModelAdmin):
    list_display = ["user", "date", "amount_kes", "credited_amount", "currency_code", "created_at"]
    list_filter = ["date"]
    search_fields = ["user__username"]
    readonly_fields = [f.name for f in WheelSpin._meta.fields]

    def has_add_permission(self, request):
        return False