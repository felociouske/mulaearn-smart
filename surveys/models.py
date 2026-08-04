from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db import models

# Survey days — Monday=0 ... Sunday=6 in Python's date.weekday()
SURVEY_WEEKDAYS = {0, 2, 4}  # Mon, Wed, Fri

QUESTIONS_PER_ATTEMPT = 10


def today_is_survey_day(today=None):
    today = today or date.today()
    return today.weekday() in SURVEY_WEEKDAYS


def payout_for_score(score):
    """
    Tiered KES payout for a /10 survey score, per spec:
      10/10        -> 20
      8 or 9       -> 15
      4, 5, 6, 7   -> 8
      1, 2, or 3   -> 2
      0            -> 0
    """
    if score == QUESTIONS_PER_ATTEMPT:
        return Decimal("20.00")
    if score >= 8:
        return Decimal("15.00")
    if score >= 4:
        return Decimal("8.00")
    if score >= 1:
        return Decimal("2.00")
    return Decimal("0.00")


class SurveyQuestion(models.Model):
    """
    One question in the ~100-question pool. 10 are drawn at random for
    each day's attempt (see SurveyAttempt). Options stored as a JSON list;
    correct_option is the 0-based index into that list.
    """
    text = models.CharField(max_length=500)
    options = models.JSONField(
        help_text='List of answer strings, e.g. ["Nairobi", "Mombasa", "Kisumu", "Eldoret"]'
    )
    correct_option = models.PositiveSmallIntegerField(
        help_text="0-based index into 'options' for the correct answer"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text[:60]


class SurveyAttempt(models.Model):
    """
    One user's attempt on one survey day. Unique per (user, date) — only
    one attempt allowed per active survey day. Created (with question_ids
    only) when the user opens today's survey, then filled in on submit.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="survey_attempts")
    date = models.DateField()
    question_ids = models.JSONField(help_text="The 10 SurveyQuestion ids presented, in the order shown")
    answers = models.JSONField(
        null=True, blank=True, help_text="User's submitted 0-based answer indices, same order as question_ids"
    )
    score = models.PositiveSmallIntegerField(null=True, blank=True)
    credited_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency_code = models.CharField(max_length=5, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("user", "date")]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.user.username} — {self.date} (score={self.score})"