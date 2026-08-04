"""
Django settings for the Mulaearn backend.
"""

from pathlib import Path
from datetime import timedelta
import dj_database_url
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Security ---
# SECRET_KEY and DEBUG come from a .env file (never hardcode secrets in
# settings.py — this is what keeps your key out of git history).
SECRET_KEY = config("SECRET_KEY", default="dev-only-insecure-key-change-in-env")
DEBUG = config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# --- Applications ---
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "channels",

    # Local apps (each earning mechanic gets its own app — keeps wallet
    # logic, chat logic, and task logic from tangling into one giant app)
    'accounts',
    'activation',
    'wallets',
    "plans",
    "chat_profiles",
    "chat",
    "surveys",
    "wheel",
    "reviews",
    "payment",
    "referrals",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # serves static files in prod, no separate server needed
    "corsheaders.middleware.CorsMiddleware",  # must sit above CommonMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "mulaearn_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "mulaearn_backend.wsgi.application"
ASGI_APPLICATION = "mulaearn_backend.asgi.application"  
# --- Channels ---
# In-memory layer for local dev — no Redis needed on your machine.
# On Railway we'll swap this for channels_redis so chat messages route
# correctly across multiple server processes/workers.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        ssl_require=True,
    )
}


STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


# --- Custom user model ---
# Must point here before the first `migrate` — Django can't swap the user
# model after tables exist, so this has to be right from day one.
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- DRF + JWT ---
# Username/password login exchanges for a JWT pair; the React frontend
# attaches the access token to every request instead of using cookies/sessions.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
}

# --- CORS ---
# Vercel will serve the React frontend from a different origin than
# Railway serves this API, so the frontend's domain(s) must be whitelisted
# explicitly rather than left wide open.
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:5173",
    cast=Csv(),
)

# --- CSRF (needed for Django admin + any session/cookie-based views) ---
# CSRF_TRUSTED_ORIGINS must list the exact scheme+domain of anywhere that
# will submit forms or POST with a CSRF token — e.g. your Vercel frontend,
# and Railway's own domain if you hit admin from it directly.
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:5173,http://127.0.0.1:5173",
    cast=Csv(),
)


# Cookies should only travel over HTTPS in production
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG


# "None" — but that only works combined with Secure=True (HTTPS).
CSRF_COOKIE_SAMESITE = "Lax" 
SESSION_COOKIE_SAMESITE = "Lax"

# --- Internationalization ---
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True

# --- Static files ---
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# --- Media files (ChatProfile photos) ---
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- TMDB (movie reviews) ---
# Use the "API Read Access Token" (the long JWT-looking one), not the
# plain API Key — reviews/tmdb.py sends it as a Bearer token.
TMDB_API_READ_ACCESS_TOKEN = config("TMDB_API_READ_ACCESS_TOKEN", default="")


# --- Daraja (M-Pesa till-number instant deposits) ---
# DARAJA_ENV: "sandbox" while testing, "production" once you have live
# Daraja app credentials approved for your till. DARAJA_CALLBACK_URL must
# be a real public HTTPS URL — Safaricom cannot reach localhost, so use
# your deployed Railway URL (or ngrok while testing locally).
DARAJA_ENV = config("DARAJA_ENV", default="sandbox")
DARAJA_CONSUMER_KEY = config("DARAJA_CONSUMER_KEY", default="")
DARAJA_CONSUMER_SECRET = config("DARAJA_CONSUMER_SECRET", default="")
DARAJA_TILL_NUMBER = config("DARAJA_TILL_NUMBER", default="")
DARAJA_PASSKEY = config("DARAJA_PASSKEY", default="")
DARAJA_CALLBACK_URL = config(
    "DARAJA_CALLBACK_URL", default="https://example.com/api/payments/deposits/daraja-callback/"
)