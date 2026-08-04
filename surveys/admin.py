from django.contrib import admin

from .models import SurveyAttempt, SurveyQuestion


@admin.register(SurveyQuestion)
class SurveyQuestionAdmin(admin.ModelAdmin):
    list_display = ["id", "text", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["text"]


@admin.register(SurveyAttempt)
class SurveyAttemptAdmin(admin.ModelAdmin):
    list_display = ["user", "date", "score", "credited_amount", "currency_code", "submitted_at"]
    list_filter = ["date"]
    search_fields = ["user__username"]
    readonly_fields = [f.name for f in SurveyAttempt._meta.fields]

    def has_add_permission(self, request):
        return False