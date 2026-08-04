from django.contrib import admin

from .models import AppListing, AppReview, DailyAppPick, DailyMoviePick, MovieReview


@admin.register(AppListing)
class AppListingAdmin(admin.ModelAdmin):
    list_display = ["name", "genre", "package_name", "is_active"]
    list_filter = ["genre", "is_active"]
    search_fields = ["name", "package_name"]


@admin.register(DailyAppPick)
class DailyAppPickAdmin(admin.ModelAdmin):
    list_display = ["date"]
    filter_horizontal = ["apps"]


@admin.register(DailyMoviePick)
class DailyMoviePickAdmin(admin.ModelAdmin):
    list_display = ["title", "date", "tmdb_id"]
    list_filter = ["date"]
    search_fields = ["title"]


@admin.register(AppReview)
class AppReviewAdmin(admin.ModelAdmin):
    list_display = ["user", "app", "date", "rating", "credited_amount", "currency_code"]
    list_filter = ["date", "rating"]
    search_fields = ["user__username", "app__name"]
    readonly_fields = ["credited_amount", "currency_code"]


@admin.register(MovieReview)
class MovieReviewAdmin(admin.ModelAdmin):
    list_display = ["user", "title", "date", "rating", "credited_amount", "currency_code"]
    list_filter = ["date", "rating"]
    search_fields = ["user__username", "title"]
    readonly_fields = ["credited_amount", "currency_code"]