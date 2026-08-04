from django.urls import path

from .views import (
    AppReviewHistoryView,
    MovieReviewHistoryView,
    SubmitAppReviewView,
    SubmitMovieReviewView,
    TodaysAppsView,
    TodaysMoviesView,
)

urlpatterns = [
    path("movies/today/", TodaysMoviesView.as_view(), name="reviews-movies-today"),
    path("movies/submit/", SubmitMovieReviewView.as_view(), name="reviews-movies-submit"),
    path("movies/history/", MovieReviewHistoryView.as_view(), name="reviews-movies-history"),
    path("apps/today/", TodaysAppsView.as_view(), name="reviews-apps-today"),
    path("apps/submit/", SubmitAppReviewView.as_view(), name="reviews-apps-submit"),
    path("apps/history/", AppReviewHistoryView.as_view(), name="reviews-apps-history"),
]