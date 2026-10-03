from django.contrib import admin

from .models import Broadcast, Notification
from .services import send_broadcast


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Send a notification to ONE user: Add -> pick the user -> write it -> Save.
    It shows up in their bell instantly if they're online. (Deposit, withdrawal,
    earnings and loan notifications are created automatically — you'll see them
    listed here too, but you never need to write those by hand.)
    """
    list_display = ("user", "type", "title", "amount", "is_read", "created_at")
    list_filter = ("type", "is_read", "created_at")
    search_fields = ("user__username", "user__email", "title", "message")
    autocomplete_fields = ("user",)  # UserAdmin already defines search_fields
    date_hierarchy = "created_at"

    def get_fields(self, request, obj=None):
        if obj is None:  # the "add" form stays short: only what you'd write by hand
            return ("user", "type", "title", "message", "link", "expires_at")
        return ("user", "type", "title", "message", "amount", "currency_code", "link", "is_read", "expires_at", "created_at")

    def get_readonly_fields(self, request, obj=None):
        return ("created_at", "amount", "currency_code") if obj else ()


@admin.register(Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    """
    Send to ALL active users: Add -> write it -> Save. One notification per
    user is created immediately. A sent broadcast is read-only (editing it
    would not change what users already received).
    """
    list_display = ("title", "type", "sent_count", "expires_at", "created_at")
    list_filter = ("type",)

    def get_fields(self, request, obj=None):
        base = ("type", "title", "message", "link", "expires_at")
        return base + ("sent_count", "created_at") if obj else base

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("type", "title", "message", "link", "expires_at", "sent_count", "created_at")
        return ()

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            count = send_broadcast(obj)
            self.message_user(request, f"Sent to {count} user(s).")