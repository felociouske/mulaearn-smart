from decimal import Decimal

from django.conf import settings
from django.db import models

from chat_profiles.models import ChatProfile
from wallets.models import Transaction


class ChatSession(models.Model):
    """One WhatsApp-style conversation between a user and a ChatProfile."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_sessions")
    chat_profile = models.ForeignKey(ChatProfile, on_delete=models.PROTECT, related_name="sessions")
    started_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-started_at"]
        # One open session per (user, profile) pair at a time — re-opening
        # the same profile continues the existing session rather than
        # forking a second one.
        constraints = [
            models.UniqueConstraint(
                fields=["user", "chat_profile"],
                condition=models.Q(is_active=True),
                name="one_active_session_per_user_profile",
            )
        ]

    def __str__(self):
        return f"{self.user.username} <-> {self.chat_profile.name}"


class ChatMessage(models.Model):
    """
    A single message in a session. For MVP (per your call), YOU are the one
    typing the "profile" side's replies from the admin console — `sender`
    just records which side a message came from either way, so the data
    model doesn't have to change when the real foreigner-access mechanism
    is figured out later.
    """

    class Sender(models.TextChoices):
        USER = "user", "Platform user"
        PROFILE = "profile", "Chat profile (you, relaying, for now)"

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    sender = models.CharField(max_length=10, choices=Sender.choices)
    content = models.TextField()
    # How much this specific message earned the user, if anything (only
    # sender=USER messages should ever have a nonzero value here).
    amount_credited = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sent_at"]

    def __str__(self):
        return f"[{self.session}] {self.sender}: {self.content[:30]}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and self.sender == self.Sender.PROFILE:
            # A real staff member just replied through the admin — track
            # it the same way WhatsApp's "last seen" does, independent of
            # the manually-toggled is_online flag.
            from django.utils import timezone

            profile = self.session.chat_profile
            profile.last_seen_at = timezone.now()
            profile.save(update_fields=["last_seen_at"])

    def credit_sender_if_applicable(self):
        """
        Credits the user's account_balance instantly when THEY send a
        message, per "instantly as they chat". Uses the profile's
        rate_per_message_kes — if that's not set yet (see ChatProfile
        docstring), this safely no-ops rather than crediting an undefined
        amount.
        """
        if self.sender != self.Sender.USER:
            return

        rate = self.session.chat_profile.rate_per_message_kes
        if not rate:
            return  # rate not configured for this profile yet — no credit, no error

        wallet = self.session.user.wallet
        wallet.credit(
            wallet_type="account",
            amount=rate,
            transaction_type=Transaction.TransactionType.CHAT_EARNING,
            description=f"Chat message with {self.session.chat_profile.name}",
        )
        self.amount_credited = rate
        self.save(update_fields=["amount_credited"])