from django.conf import settings
from django.db import models


class PlanCategory(models.TextChoices):
    APP_REVIEW = "app_review", "App Reviews"
    MOVIE_REVIEW = "movie_review", "Movie Reviews"
    CHAT = "chat", "Chat with Foreigners"


class Plan(models.Model):
    """
    A purchasable plan tier, scoped to one category. A user can hold an
    active plan in each of the three categories simultaneously — buying a
    Chat plan doesn't touch an existing active App-review plan (see
    PurchasePlanView, which only deactivates previous purchases in the
    SAME category).

    Unlocks are expressed as a count/flag rather than a hardcoded per-tier
    if/else chain, so adding a 5th App-review tier later is just adding a
    row in admin — no code change required.
    """
    category = models.CharField(max_length=20, choices=PlanCategory.choices)
    name = models.CharField(max_length=50)  # e.g. "App Review Starter", "Chat Plan 3" — display name, up to you
    price = models.DecimalField(max_digits=10, decimal_places=2)  # in KES
    # Lower tier_order = cheaper/entry plan within THIS category (unique per
    # category, not globally — App-review tier 1 and Chat tier 1 can coexist).
    tier_order = models.PositiveIntegerField()

    # Generic unlock count — meaning depends on category:
    #   APP_REVIEW   -> how many app-review tasks this plan unlocks
    #   MOVIE_REVIEW -> how many movie-review tasks this plan unlocks
    #   CHAT         -> how many chat profiles this plan unlocks (lowest-paying first)
    unlocked_item_count = models.PositiveIntegerField(default=0)

    # Optional headline cashback number shown on the pricing card, e.g. 5.00
    # for "5% cashback". Leave blank for plans that don't have one — use the
    # PlanFeature bullets below for anything more specific.
    cashback_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Optional headline cashback %, e.g. 5.00 for '5% cashback'. Leave blank if none.",
    )

    is_active = models.BooleanField(default=True)  # lets you retire a plan without deleting purchase history

    class Meta:
        ordering = ["category", "tier_order"]
        unique_together = [("category", "tier_order")]

    def __str__(self):
        return f"[{self.get_category_display()}] {self.name} (KES {self.price})"


class PlanFeature(models.Model):
    """
    One bullet point shown under a plan on the pricing page, e.g.
    "Unlock 20 apps", "5% cashback on every review", "Priority support".
    A free-form list rather than fixed fields so you can add/remove/reorder
    marketing copy per plan straight from admin, no deploy needed.
    """
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="features")
    description = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.description


class PlanPurchase(models.Model):
    """
    Records each time a user buys or upgrades a plan. We keep every purchase
    row (not just "current plan" on User) so referral commissions and
    purchase history stay auditable even after an upgrade.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="plan_purchases")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="purchases")
    price_paid = models.DecimalField(max_digits=10, decimal_places=2)  # snapshot — protects history if Plan.price changes later
    is_active = models.BooleanField(default=True)  # only one PlanPurchase per user PER CATEGORY should be active at a time
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-purchased_at"]

    def __str__(self):
        return f"{self.user.username} -> {self.plan.name} @ {self.purchased_at:%Y-%m-%d}"


def get_active_plan(user, category):
    """Convenience lookup: the user's active plan in one specific category, or None."""
    purchase = (
        PlanPurchase.objects.filter(user=user, is_active=True, plan__category=category)
        .select_related("plan")
        .order_by("-purchased_at")
        .first()
    )
    return purchase.plan if purchase else None


def get_active_plans_by_category(user):
    """
    All three at once, as {category: Plan|None} — one query instead of three,
    handy for a single dashboard summary or for task-unlock checks that need
    to know about more than one category (e.g. "does the user have ANY plan").
    """
    result = {choice: None for choice in PlanCategory.values}
    purchases = PlanPurchase.objects.filter(user=user, is_active=True).select_related("plan")
    for purchase in purchases:
        result[purchase.plan.category] = purchase.plan
    return result