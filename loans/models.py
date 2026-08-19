"""
Loan-giving feature — separate app on purpose (per your request), even
though LoanPlan/LoanPlanPurchase are structurally close cousins of
plans.Plan/PlanPurchase. Kept apart because the eligibility rule is
genuinely different: plans.PlanPurchase deactivates the previous
purchase in the same category (one active plan per category); loan-plan
purchases STACK — a user can own several tiers at once, and their
eligible loan range is read off the highest tier they own (see
get_loan_eligibility() below). Folding that into plans.models would mean
a special-cased category that behaves unlike the other three, which is
worse than a second small app.
"""
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class LoanPlan(models.Model):
    """
    A purchasable tier that unlocks a loan amount range. Six rows for
    now (3500/6800/13500/18500/26000/49000 KES), but — same reasoning as
    plans.Plan — expressed as data (min/max/order), not a hardcoded
    if/else chain, so adding a 7th tier later is an admin row, not a
    deploy.

    repayment_period_days: no loan term was specified when this was
    designed, so this defaults to 30 and is admin-editable per tier
    rather than hardcoded — it's what LoanApplication.due_date is
    computed from at application time. Adjust in admin if 30 isn't
    right; no code change needed.
    """
    name = models.CharField(max_length=50)  # e.g. "Loan Tier 1" — display name, up to you
    price = models.DecimalField(max_digits=10, decimal_places=2)  # in KES
    min_amount = models.DecimalField(max_digits=12, decimal_places=2)
    max_amount = models.DecimalField(max_digits=12, decimal_places=2)
    # Lower order = cheaper/entry tier. Also what "highest tier owned"
    # (get_loan_eligibility below) compares on — NOT price directly, so
    # you can reorder tiers in admin independent of price if you ever
    # need to.
    order = models.PositiveIntegerField()
    repayment_period_days = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)  # retire a tier without deleting purchase/application history

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.name} (KES {self.price} -> {self.min_amount}-{self.max_amount})"


class LoanPlanPurchase(models.Model):
    """
    One row per loan-plan purchase. Unlike plans.PlanPurchase there is
    NO deactivation of earlier purchases here — tiers stack by design
    (confirmed: a user can hold multiple tiers; eligibility is read off
    the highest one owned, not summed across all of them). Every
    purchase row stays "current" forever; there's nothing to expire.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="loan_plan_purchases")
    loan_plan = models.ForeignKey(LoanPlan, on_delete=models.PROTECT, related_name="purchases")
    price_paid = models.DecimalField(max_digits=10, decimal_places=2)  # snapshot — protects history if LoanPlan.price changes later
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-purchased_at"]

    def __str__(self):
        return f"{self.user.username} -> {self.loan_plan.name} @ {self.purchased_at:%Y-%m-%d}"


def get_loan_eligibility(user):
    """
    The user's current loan range, based on the HIGHEST-order LoanPlan
    they've ever purchased (owning a cheap tier AND an expensive one
    doesn't widen the range beyond the expensive one's own min/max — it
    just means they hold two purchase rows). Returns the LoanPlan
    instance, or None if the user has never bought one — callers check
    `is None` for the "plan needed, view plans" case.
    """
    purchase = (
        LoanPlanPurchase.objects.filter(user=user)
        .select_related("loan_plan")
        .order_by("-loan_plan__order")
        .first()
    )
    return purchase.loan_plan if purchase else None


class RepaymentStatus(models.TextChoices):
    OWING = "owing", "Owing"
    PAID = "paid", "Paid"
    WRITTEN_OFF = "written_off", "Written off"


class LoanApplication(models.Model):
    """
    One row per loan application. Credited to account_balance immediately
    on creation (see views.SubmitLoanApplicationView) — there's no
    review/approval step, so unlike ActivationSubmission/DepositRequest
    this has no PENDING status; it's disbursed the moment it's created.
    Applying again later (even with amount_owed still > 0 on an earlier
    row) is allowed without limit, per your spec — nothing here blocks a
    second application.

    full_name is asked fresh rather than auto-filled: the User model
    only has username/email/phone_number/country (no first/last name is
    collected at registration), so there's nothing to prefill a legal
    name FROM. email/phone_number/country_name below ARE auto-filled —
    snapshotted from request.user at submission time (server-side, not
    client-editable) since those genuinely do exist on the account and
    "auto-fills with account details" means exactly this for them.

    amount_owed/due_date/repayment_status track this as a debt, per your
    decision to record it even without collection logic yet — nothing
    currently automates moving OWING -> PAID; that's a manual admin
    action (see admin.py) until a real repayment flow is built.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="loan_applications")
    # Which tier's range this application was validated against — kept even
    # though it's derivable from get_loan_eligibility() at read time, because
    # that function's answer can change later (user buys a higher tier
    # afterward) and this row should keep showing what was true when they applied.
    loan_plan = models.ForeignKey(LoanPlan, on_delete=models.PROTECT, related_name="applications")

    # --- Auto-filled account details (server-populated snapshot, not client input) ---
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    country_name = models.CharField(max_length=50)

    # --- Form answers (client input) ---
    full_name = models.CharField(max_length=150)
    age = models.PositiveIntegerField()
    source_of_income = models.CharField(max_length=200)
    repayment_method = models.CharField(max_length=200)
    security = models.CharField(max_length=200, blank=True)  # collateral description — optional, some loans are unsecured
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # the amount they chose, validated within loan_plan's range at submission

    # --- Debt tracking ---
    amount_owed = models.DecimalField(max_digits=12, decimal_places=2)  # starts equal to `amount`; would shrink with real repayments once that's built
    due_date = models.DateField()
    repayment_status = models.CharField(max_length=15, choices=RepaymentStatus.choices, default=RepaymentStatus.OWING)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} | KES {self.amount} | {self.get_repayment_status_display()}"

    def save(self, *args, **kwargs):
        # amount_owed/due_date are derived at creation, not something the
        # caller passes in — computed here so every creation path (admin,
        # API, a future management command) gets the same behavior instead
        # of each one having to remember to set them.
        if self._state.adding:
            if not self.amount_owed:
                self.amount_owed = self.amount
            if not self.due_date:
                self.due_date = (timezone.now() + timedelta(days=self.loan_plan.repayment_period_days)).date()
        super().save(*args, **kwargs)