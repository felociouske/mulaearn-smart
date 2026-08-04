"""
Thin wrapper around TMDB's v3 API. Auth is the Bearer read-access token
(settings.TMDB_API_READ_ACCESS_TOKEN) — the long JWT-looking one, not the
plain API Key. Every function raises requests.HTTPError on a bad response;
callers are expected to catch that and return a 502 to the frontend rather
than letting it bubble up as a 500.
"""
import requests
from django.conf import settings

TMDB_BASE_URL = "https://api.themoviedb.org/3"
POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"


def _headers():
    return {
        "Authorization": f"Bearer {settings.TMDB_API_READ_ACCESS_TOKEN}",
        "accept": "application/json",
    }


def get_trending_movies(limit=10):
    """GET /trending/movie/day — today's trending movies, TMDB's own ranking."""
    resp = requests.get(f"{TMDB_BASE_URL}/trending/movie/day", headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json().get("results", [])[:limit]


def get_movie_genres():
    """GET /genre/movie/list — {id: name} map for turning genre_ids into readable text."""
    resp = requests.get(f"{TMDB_BASE_URL}/genre/movie/list", headers=_headers(), timeout=10)
    resp.raise_for_status()
    return {g["id"]: g["name"] for g in resp.json().get("genres", [])}


def get_movie_trailer_key(tmdb_id):
    """GET /movie/{id}/videos — first official YouTube trailer key found, or None."""
    resp = requests.get(f"{TMDB_BASE_URL}/movie/{tmdb_id}/videos", headers=_headers(), timeout=10)
    resp.raise_for_status()
    for video in resp.json().get("results", []):
        if video.get("site") == "YouTube" and video.get("type") == "Trailer":
            return video["key"]
    return None


def poster_url(poster_path):
    return f"{POSTER_BASE_URL}{poster_path}" if poster_path else None