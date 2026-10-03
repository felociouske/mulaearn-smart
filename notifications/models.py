from django.conf import settings
from django.db import models
from django.utils import timezone


class NotificationType(models.TextChoices):
    # Granular on purpose: each type gets its own icon/colour on the frontend.
    DEPOSIT = "deposit", "Deposit"
    WITHDRAWAL = "withdrawal", "Withdrawal"
    REFUND = "refund", "Refund"
    SURVEY = "survey", "Survey earning"
    MOVIE_REVIEW = "movie_review", "Movie review earning"
    APP_REVIEW = "app_review", "App review earning"
    WHEEL = "wheel", "Wheel spin"
    CHAT = "chat", "Chat earning"
    REFERRAL = "referral", "Referral commission"
    LOAN = "loan", "Loan"
    PLAN = "plan", "Plan"
    SYSTEM = "system", "System"
    PROMO = "promo", "Promotion"


class NotificationQuerySet(models.QuerySet):
    def active(self):
        """Hides notifications whose expires_at has passed (used for promos)."""
        now = timezone.now()
        return self.filter(models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now))


class Notification(models.Model):
    """
    ONE row per (notification, user). A message for "all users" is fanned
    out into one row per user (see services.send_broadcast) — deliberately
    the simple approach: read/unread and delete are then plain per-user
    columns, with no extra "who has read this broadcast" table to maintain.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=20, choices=NotificationType.choices, default=NotificationType.SYSTEM)
    title = models.CharField(max_length=120)
    message = models.TextField()

    # Signed: positive = money in, negative = money out. Null for non-money
    # notifications (system/promo). Lets the frontend render "+KSh 30.00".
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency_code = models.CharField(max_length=5, blank=True)

    # Optional in-app route the notification opens, e.g. "/loans".
    link = models.CharField(max_length=300, blank=True)

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Optional. Hidden from the user after this time.")

    objects = NotificationQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["user", "is_read"]),
        ]

    def __str__(self):
        return f"{self.user.username} | {self.type} | {self.title}"


class Broadcast(models.Model):
    """
    The record you create in the admin to message ALL users. Saving it
    (add only) fans out a Notification to every active user. Kept as its
    own model so you have a history of what was sent and to how many people.
    """
    type = models.CharField(
        max_length=20,
        choices=[(NotificationType.PROMO.value, "Promotion"), (NotificationType.SYSTEM.value, "System")],
        default=NotificationType.PROMO,
    )
    title = models.CharField(max_length=120)
    message = models.TextField()
    link = models.CharField(max_length=300, blank=True, help_text="Optional in-app route, e.g. /loans")
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Optional. Hidden from users after this time.")
    sent_count = models.PositiveIntegerField(default=0, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.sent_count} sent)"