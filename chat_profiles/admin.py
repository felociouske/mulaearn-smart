from django.contrib import admin

from .models import ChatProfile


@admin.register(ChatProfile)
class ChatProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "payout_amount_usd", "rate_per_message_kes", "is_active", "is_online", "last_seen_at")
    list_editable = ("is_active", "is_online")
    search_fields = ("name",)