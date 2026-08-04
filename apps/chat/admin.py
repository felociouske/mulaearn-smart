from django.contrib import admin

from .models import ChatSession, ChatMessage


class ChatMessageInline(admin.TabularInline):
    """
    This is how staff actually reply, for now: open the session in
    /admin/, add a row here with sender="Chat profile" and your reply
    text. amount_credited/sent_at are computed, so those stay read-only —
    but sender/content need to be editable or there'd be no way to send a
    reply at all (the previous version of this inline made every field
    read-only, which was a bug, not a deliberate lock).
    """
    model = ChatMessage
    extra = 1
    fields = ("sender", "content", "amount_credited", "sent_at")
    readonly_fields = ("amount_credited", "sent_at")


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "chat_profile", "is_active", "started_at")
    list_filter = ("is_active", "chat_profile")
    search_fields = ("user__username", "chat_profile__name")
    inlines = [ChatMessageInline]