"""
Google Play app discovery via the `google-play-scraper` package.

IMPORTANT CAVEAT: unlike reviews/tmdb.py, this is NOT an official API.
`google-play-scraper` works by parsing Play Store web pages — there's no
sanctioned Google endpoint for this. That means:
  - It can break without warning whenever Google changes their page structure.
  - Scraping Play Store pages sits in a legal gray area under Google's ToS.
  - There's no official rate-limit guidance — keep call volume low (this
    module is designed to run once per day, not per-request).
This is a reasonable choice for reading public app names/descriptions/
icons for internal use, but it's a "works until Google changes something"
dependency, not a stable contract like TMDB's official API.

This module doesn't hit "top charts" — that endpoint isn't exposed by
this package version. Instead it discovers apps by searching a rotating
set of generic category terms (finance, games, social, etc.), one term
per day so the pool varies day to day without needing a fixed app list
that goes stale.
"""
import logging
from datetime import date

from google_play_scraper import app as gp_app_detail
from google_play_scraper import search as gp_search
from google_play_scraper.exceptions import NotFoundError

logger = logging.getLogger(__name__)

PLAY_STORE_URL = "https://play.google.com/store/apps/details?id={app_id}"

# One search term is used per day (chosen deterministically by date, so
# it's stable across repeated calls the same day), rotating through this
# list. Add/remove categories freely.
SEARCH_TERMS = [
    "finance", "games", "photo editor", "music player", "shopping",
    "fitness", "education", "productivity", "social", "utilities",
]


def _term_for_today():
    return SEARCH_TERMS[date.today().toordinal() % len(SEARCH_TERMS)]


def discover_apps(limit=10, country="ke", lang="en"):
    """
    Returns up to `limit` app summaries: [{package_name, name, genre, icon_url, store_url}, ...]
    Fetches full descriptions via get_app_details() separately since
    search() doesn't return them — that's a second request per app, so
    keep `limit` modest (10 is plenty for a daily pool).
    """
    term = _term_for_today()
    try:
        results = gp_search(term, n_hits=limit, lang=lang, country=country)
    except Exception:
        logger.exception("Google Play search failed for term '%s'", term)
        return []

    apps = []
    for result in results:
        package_name = result.get("appId")
        if not package_name:
            continue
        try:
            detail = gp_app_detail(package_name, lang=lang, country=country)
        except NotFoundError:
            continue
        except Exception:
            logger.exception("Google Play detail fetch failed for %s", package_name)
            continue

        apps.append({
            "package_name": package_name,
            "name": detail.get("title") or result.get("title") or package_name,
            "genre": detail.get("genre") or result.get("genre") or "",
            "description": (detail.get("description") or "")[:2000],
            "icon_url": detail.get("icon") or result.get("icon") or "",
            "store_url": PLAY_STORE_URL.format(app_id=package_name),
        })

    return apps