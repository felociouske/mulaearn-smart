from django.contrib import admin

from .models import LoanApplication, LoanPlan, LoanPlanPurchase, RepaymentStatus


@admin.register(LoanPlan)
class LoanPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "min_amount", "max_amount", "order", "repayment_period_days", "is_active")
    list_editable = ("is_active",)
    ordering = ("order",)


@admin.register(LoanPlanPurchase)
class LoanPlanPurchaseAdmin(admin.ModelAdmin):
    list_display = ("user", "loan_plan", "price_paid", "purchased_at")
    search_fields = ("user__username",)
    list_filter = ("loan_plan",)


@admin.action(description="Mark selected loans as repaid")
def mark_as_repaid(modeladmin, request, queryset):
    # Manual only — there's no automated repayment collection yet (none
    # was in scope), so this is the one place OWING -> PAID happens today.
    queryset.update(repayment_status=RepaymentStatus.PAID, amount_owed=0)


@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "amount", "amount_owed", "repayment_status", "due_date", "created_at")
    list_filter = ("repayment_status", "loan_plan")
    search_fields = ("user__username", "full_name", "phone_number")
    actions = [mark_as_repaid]