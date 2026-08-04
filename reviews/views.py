import random
from datetime import date

from django.db import transaction as db_transaction
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsActivated
from plans.models import get_active_plan
from wallets.models import Transaction

from . import google_play, tmdb
from .models import (
    AppListing,
    AppReview,
    DailyAppPick,
    DailyMoviePick,
    MovieReview,
    random_review_payout_kes,
)
from .serializers import (
    AppListingSerializer,
    AppReviewSerializer,
    DailyMoviePickSerializer,
    MovieReviewSerializer,
)

# No active plan in the category = no items shown at all — the frontend
# shows a "here's what it takes to get started" guide instead of a review
# grid. (Previously this was 1, giving everyone a free daily item
# regardless of plan — that was an assumption flagged for confirmation,
# and it turned out to be wrong: reviewing should require a plan.)
FREE_TIER_DAILY_ITEMS = 0

# How many items we fetch/store for the day overall; the user's plan then
# trims how many of these they're actually allowed to see (unlocked_item_count).
DAILY_POOL_SIZE = 10


def _allowed_count(user, category):
    plan = get_active_plan(user, category)
    return plan.unlocked_item_count if plan else FREE_TIER_DAILY_ITEMS


def _get_or_create_todays_movie_picks():
    today = date.today()
    picks = list(DailyMoviePick.objects.filter(date=today))
    if picks:
        return picks

    trending = tmdb.get_trending_movies(limit=DAILY_POOL_SIZE)
    genre_map = tmdb.get_movie_genres()

    created = []
    for movie in trending:
        genre_names = ", ".join(genre_map.get(gid, "") for gid in movie.get("genre_ids", []) if gid in genre_map)
        trailer_key = tmdb.get_movie_trailer_key(movie["id"]) or ""
        pick, _ = DailyMoviePick.objects.get_or_create(
            date=today,
            tmdb_id=movie["id"],
            defaults=dict(
                title=movie.get("title", ""),
                genres=genre_names,
                overview=movie.get("overview", ""),
                poster_path=movie.get("poster_path") or "",
                trailer_key=trailer_key,
            ),
        )
        created.append(pick)
    return created


class TodaysMoviesView(APIView):
    """
    GET /api/reviews/movies/today/
    Fetches (or reuses) today's trending-movie picks from TMDB, trims the
    list to how many the user's Movie Review plan unlocks, and flags which
    the user has already reviewed today.
    """
    permission_classes = [permissions.IsAuthenticated, IsActivated]

    def get(self, request):
        try:
            picks = _get_or_create_todays_movie_picks()
        except Exception:
            return Response(
                {"detail": "Couldn't reach TMDB right now — try again shortly."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        allowed = _allowed_count(request.user, "movie_review")
        today = date.today()
        already_reviewed_ids = set(
            MovieReview.objects.filter(user=request.user, date=today).values_list("tmdb_id", flat=True)
        )
        visible = picks[:allowed]

        return Response({
            "allowed_count": allowed,
            "reviewed_today": len(already_reviewed_ids),
            "movies": DailyMoviePickSerializer(
                visible, many=True, context={"reviewed_ids": already_reviewed_ids}
            ).data,
        })


class SubmitMovieReviewView(APIView):
    """
    POST /api/reviews/movies/submit/  { "tmdb_id": 123, "rating": 4, "review_text": "..." }
    Credits a random KES 150-250 (converted to local currency) immediately
    on submission — the review itself is saved for admin visibility only,
    never sent to TMDB or any external store.
    """
    permission_classes = [permissions.IsAuthenticated, IsActivated]

    def post(self, request):
        tmdb_id = request.data.get("tmdb_id")
        rating = request.data.get("rating")
        review_text = (request.data.get("review_text") or "").strip()
        today = date.today()

        if not tmdb_id or not rating or not review_text:
            raise DRFValidationError({"detail": ["tmdb_id, rating and review_text are all required."]})
        if not (1 <= int(rating) <= 5):
            raise DRFValidationError({"rating": ["Rating must be between 1 and 5."]})

        pick = DailyMoviePick.objects.filter(date=today, tmdb_id=tmdb_id).first()
        if not pick:
            raise DRFValidationError({"tmdb_id": ["That movie isn't in today's picks."]})

        allowed = _allowed_count(request.user, "movie_review")
        reviewed_today = MovieReview.objects.filter(user=request.user, date=today).count()
        if reviewed_today >= allowed:
            raise DRFValidationError({"detail": [f"You've reached today's limit of {allowed} movie review(s)."]})
        if MovieReview.objects.filter(user=request.user, tmdb_id=tmdb_id, date=today).exists():
            raise DRFValidationError({"detail": ["You've already reviewed this movie today."]})

        payout_kes = random_review_payout_kes()
        country = request.user.country
        credited_amount = country.convert_from_kes(payout_kes) if country else payout_kes
        currency_code = country.currency_code if country else "KES"

        with db_transaction.atomic():
            review = MovieReview.objects.create(
                user=request.user,
                tmdb_id=tmdb_id,
                title=pick.title,
                date=today,
                rating=rating,
                review_text=review_text,
                credited_amount=credited_amount,
                currency_code=currency_code,
            )
            request.user.wallet.credit(
                "account",
                credited_amount,
                Transaction.TransactionType.MOVIE_REVIEW_EARNING,
                description=f"Movie review: {pick.title}",
            )

        return Response(MovieReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class MovieReviewHistoryView(generics.ListAPIView):
    serializer_class = MovieReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MovieReview.objects.filter(user=self.request.user)


def _get_or_create_todays_app_picks():
    today = date.today()
    pick_set, _ = DailyAppPick.objects.get_or_create(date=today)
    if pick_set.apps.exists():
        return pick_set

    chosen_ids = []

    # Primary source: Google Play (see reviews/google_play.py for the
    # "unofficial scraper, not a stable API" caveat). get_or_create by
    # package_name so re-discovering the same app just refreshes its
    # details rather than creating a duplicate.
    for scraped in google_play.discover_apps(limit=DAILY_POOL_SIZE):
        listing, _ = AppListing.objects.update_or_create(
            package_name=scraped["package_name"],
            defaults={
                "name": scraped["name"],
                "genre": scraped["genre"],
                "description": scraped["description"],
                "icon_url": scraped["icon_url"],
                "store_url": scraped["store_url"],
                "is_active": True,
            },
        )
        chosen_ids.append(listing.id)

    # Fallback / top-up: if scraping failed entirely (Google changed
    # something, network issue, etc.) or returned fewer than we wanted,
    # fill the rest from manually-curated AppListing entries so "Today's
    # Apps" is never just empty because of an external dependency.
    if len(chosen_ids) < DAILY_POOL_SIZE:
        manual_pool = list(
            AppListing.objects.filter(is_active=True, package_name__isnull=True)
            .exclude(id__in=chosen_ids)
            .values_list("id", flat=True)
        )
        needed = DAILY_POOL_SIZE - len(chosen_ids)
        chosen_ids.extend(random.sample(manual_pool, min(needed, len(manual_pool))))

    pick_set.apps.set(chosen_ids)
    return pick_set


class TodaysAppsView(APIView):
    """GET /api/reviews/apps/today/ — same pattern as movies, sourced from admin-curated AppListing."""
    permission_classes = [permissions.IsAuthenticated, IsActivated]

    def get(self, request):
        pick_set = _get_or_create_todays_app_picks()
        allowed = _allowed_count(request.user, "app_review")
        today = date.today()
        already_reviewed_ids = set(
            AppReview.objects.filter(user=request.user, date=today).values_list("app_id", flat=True)
        )
        visible = list(pick_set.apps.all())[:allowed]

        return Response({
            "allowed_count": allowed,
            "reviewed_today": len(already_reviewed_ids),
            "apps": AppListingSerializer(visible, many=True, context={"reviewed_ids": already_reviewed_ids}).data,
        })


class SubmitAppReviewView(APIView):
    """POST /api/reviews/apps/submit/  { "app_id": 5, "rating": 4, "review_text": "..." }"""
    permission_classes = [permissions.IsAuthenticated, IsActivated]

    def post(self, request):
        app_id = request.data.get("app_id")
        rating = request.data.get("rating")
        review_text = (request.data.get("review_text") or "").strip()
        today = date.today()

        if not app_id or not rating or not review_text:
            raise DRFValidationError({"detail": ["app_id, rating and review_text are all required."]})
        if not (1 <= int(rating) <= 5):
            raise DRFValidationError({"rating": ["Rating must be between 1 and 5."]})

        app = AppListing.objects.filter(id=app_id, is_active=True).first()
        if not app:
            raise DRFValidationError({"app_id": ["App not found."]})

        allowed = _allowed_count(request.user, "app_review")
        reviewed_today = AppReview.objects.filter(user=request.user, date=today).count()
        if reviewed_today >= allowed:
            raise DRFValidationError({"detail": [f"You've reached today's limit of {allowed} app review(s)."]})
        if AppReview.objects.filter(user=request.user, app=app, date=today).exists():
            raise DRFValidationError({"detail": ["You've already reviewed this app today."]})

        payout_kes = random_review_payout_kes()
        country = request.user.country
        credited_amount = country.convert_from_kes(payout_kes) if country else payout_kes
        currency_code = country.currency_code if country else "KES"

        with db_transaction.atomic():
            review = AppReview.objects.create(
                user=request.user,
                app=app,
                date=today,
                rating=rating,
                review_text=review_text,
                credited_amount=credited_amount,
                currency_code=currency_code,
            )
            request.user.wallet.credit(
                "account",
                credited_amount,
                Transaction.TransactionType.APP_REVIEW_EARNING,
                description=f"App review: {app.name}",
            )

        return Response(AppReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class AppReviewHistoryView(generics.ListAPIView):
    serializer_class = AppReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AppReview.objects.filter(user=self.request.user)