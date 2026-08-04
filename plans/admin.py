from django.contrib import admin

from .models import Plan, PlanFeature, PlanPurchase


class PlanFeatureInline(admin.TabularInline):
    """Edit a plan's bullet-point features (cashback, perks, etc) right on the Plan page."""
    model = PlanFeature
    extra = 1


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "tier_order", "unlocked_item_count", "cashback_percentage", "is_active")
    list_filter = ("category", "is_active")
    list_editable = ("is_active",)
    ordering = ("category", "tier_order")
    inlines = [PlanFeatureInline]


@admin.register(PlanPurchase)
class PlanPurchaseAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "price_paid", "is_active", "purchased_at")
    list_filter = ("plan__category", "is_active")
    search_fields = ("user__username",)