import random
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db import models

REVIEW_PAYOUT_MIN_KES = 150
REVIEW_PAYOUT_MAX_KES = 250


def random_review_payout_kes():
    """Random whole-shilling KES amount in the 150-250 review payout range."""
    return Decimal(random.randint(REVIEW_PAYOUT_MIN_KES, REVIEW_PAYOUT_MAX_KES))


class AppListing(models.Model):
    """
    Apps available for review. Populated two ways:
      1. Auto-discovered from Google Play (see reviews/google_play.py) —
         these have package_name set, and get their name/genre/description
         refreshed each time they're picked again.
      2. Manually added via the admin (package_name left blank) — still
         supported for anything you want to feature deliberately rather
         than leave to the daily scrape.
    """
    name = models.CharField(max_length=150)
    genre = models.CharField(max_length=100)
    description = models.TextField()
    icon_url = models.URLField(blank=True)
    store_url = models.URLField(blank=True, help_text="Play Store / App Store link, optional")
    package_name = models.CharField(
        max_length=255, unique=True, null=True, blank=True,
        help_text="Google Play package id (e.g. com.example.app) — set only for scraped entries",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class DailyAppPick(models.Model):
    """Today's set of apps available to review — refreshed once per day."""
    date = models.DateField(unique=True)
    apps = models.ManyToManyField(AppListing)

    def __str__(self):
        return f"App picks — {self.date}"


class DailyMoviePick(models.Model):
    """
    Today's set of movies to review, sourced from TMDB's trending/day
    endpoint. Stores a lightweight snapshot (not just the tmdb_id) so a
    review always reflects what the user actually saw, even if TMDB's
    trending list shifts later in the day.
    """
    date = models.DateField()
    tmdb_id = models.PositiveIntegerField()
    title = models.CharField(max_length=255)
    genres = models.CharField(max_length=255, blank=True)
    overview = models.TextField(blank=True)
    poster_path = models.CharField(max_length=255, blank=True)
    trailer_key = models.CharField(max_length=50, blank=True, help_text="YouTube key for the trailer, if found")

    class Meta:
        unique_together = [("date", "tmdb_id")]

    def __str__(self):
        return f"{self.title} — {self.date}"


class AppReview(models.Model):
    """
    A submitted app review. Never sent anywhere external — it's saved
    here (visible/moderatable in the Django admin) and the account is
    credited immediately on submission, per the agreed flow.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="app_reviews")
    app = models.ForeignKey(AppListing, on_delete=models.CASCADE, related_name="reviews")
    date = models.DateField(default=date.today)
    rating = models.PositiveSmallIntegerField(help_text="1-5 stars")
    review_text = models.TextField()
    credited_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency_code = models.CharField(max_length=5)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "app", "date")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} → {self.app.name} ({self.date})"


class MovieReview(models.Model):
    """A submitted movie review — same submit-and-credit-immediately flow as AppReview."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="movie_reviews")
    tmdb_id = models.PositiveIntegerField()
    title = models.CharField(max_length=255)
    date = models.DateField(default=date.today)
    rating = models.PositiveSmallIntegerField(help_text="1-5 stars")
    review_text = models.TextField()
    credited_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency_code = models.CharField(max_length=5)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "tmdb_id", "date")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} → {self.title} ({self.date})"