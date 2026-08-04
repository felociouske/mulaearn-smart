from rest_framework import serializers

from . import tmdb
from .models import AppListing, AppReview, DailyMoviePick, MovieReview


class DailyMoviePickSerializer(serializers.ModelSerializer):
    poster_url = serializers.SerializerMethodField()
    already_reviewed = serializers.SerializerMethodField()

    class Meta:
        model = DailyMoviePick
        fields = ["tmdb_id", "title", "genres", "overview", "poster_url", "trailer_key", "already_reviewed"]

    def get_poster_url(self, obj):
        return tmdb.poster_url(obj.poster_path)

    def get_already_reviewed(self, obj):
        return obj.tmdb_id in self.context.get("reviewed_ids", set())


class MovieReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovieReview
        fields = [
            "id", "tmdb_id", "title", "date", "rating", "review_text",
            "credited_amount", "currency_code", "created_at",
        ]
        read_only_fields = ["credited_amount", "currency_code"]


class AppListingSerializer(serializers.ModelSerializer):
    already_reviewed = serializers.SerializerMethodField()

    class Meta:
        model = AppListing
        fields = ["id", "name", "genre", "description", "icon_url", "store_url", "already_reviewed"]

    def get_already_reviewed(self, obj):
        return obj.id in self.context.get("reviewed_ids", set())


class AppReviewSerializer(serializers.ModelSerializer):
    app_name = serializers.CharField(source="app.name", read_only=True)

    class Meta:
        model = AppReview
        fields = [
            "id", "app", "app_name", "date", "rating", "review_text",
            "credited_amount", "currency_code", "created_at",
        ]
        read_only_fields = ["credited_amount", "currency_code"]