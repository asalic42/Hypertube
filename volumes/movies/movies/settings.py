from pathlib import Path
from datetime import timedelta
import os

from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent

def required_env(name: str) -> str:
    """A setting that must come from the environment: no fallback, start-up fails without it."""
    value = os.getenv(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"{name} is not set. Add it to the .env file at the root of the project.")
    return value


def secret_key(name: str) -> str:
    key = required_env(name)
    if len(key) < 50 or key.startswith("django-insecure-"):
        raise ImproperlyConfigured(
            f"{name} is too weak: use at least 50 random characters, never committed, made with "
            "python3 -c \"import secrets; print(secrets.token_urlsafe(64))\""
        )
    return key


# Security settings have no safe default: each one is read from .env, and the
# service refuses to start without them. DEBUG is off unless asked for.
SECRET_KEY = secret_key("MOVIES_SECRET_KEY")
DEBUG = os.getenv("DJANGO_DEBUG", "0").strip().lower() in ("1", "true", "yes")
ALLOWED_HOSTS = [host.strip() for host in required_env("DJANGO_ALLOWED_HOSTS").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
    "movies_app",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "movies.urls"
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "https://localhost:8080"
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "movies.wsgi.application"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTStatelessUserAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # One proxy (nginx) stands in front: the client address is the one it
    # writes in X-Forwarded-For, not whatever the client put there itself.
    "NUM_PROXIES": 1,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "30/minute",
        "user": "1200/minute",
    },
}


def read_key_file(env_variable: str, default: str) -> str:
    path = Path(os.getenv(env_variable) or default)
    return path.read_text(encoding="utf-8") if path.is_file() else ""


# Tokens are issued by the auth service; this service only verifies them.
SIMPLE_JWT = {
    "ALGORITHM": "RS256",
    "VERIFYING_KEY": read_key_file("JWT_PUBLIC_KEY_PATH", "/jwt/jwt_public.pem"),
    "ISSUER": "auth-service",
    "AUDIENCE": "hypertube",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_CLAIM": "sub",
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",
    "LEEWAY": 5,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Movies API",
    "DESCRIPTION": "API de gestion des films.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("MOVIES_USER"),
        "PASSWORD": os.getenv("MOVIES_PASSWORD"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT"),
	"OPTIONS": {
		"sslmode": "verify-full",
		"sslrootcert": "/certs/ca.crt",
	},
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# File storage (S3) for the downloaded movies and their subtitles.
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_MOVIES_STORAGE_BUCKET_NAME = os.environ.get("AWS_MOVIES_STORAGE_BUCKET_NAME") or "movies"
AWS_S3_ENDPOINT_URL = os.environ.get("AWS_S3_ENDPOINT_URL")
AWS_S3_REGION_NAME = os.environ.get("AWS_S3_REGION_NAME") or "us-east-1"

# Torrents: working directory shared by the web and worker containers.
MOVIES_DOWNLOAD_DIR = os.environ.get("MOVIES_DOWNLOAD_DIR") or "/downloads"
TORRENT_LISTEN_PORT = int(os.environ.get("TORRENT_LISTEN_PORT") or 6881)
MOVIE_RETENTION_DAYS = 30
MOVIE_RENDITION_HEIGHTS = (1080, 720, 480, 360)
STREAM_TOKEN_MAX_AGE = timedelta(hours=12)

# External services. Metadata and subtitles are simply skipped without their key.
ARCHIVE_COLLECTION = os.environ.get("ARCHIVE_COLLECTION") or "feature_films"
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "").strip()
OPENSUBTITLES_API_KEY = os.environ.get("OPENSUBTITLES_API_KEY", "").strip()
OPENSUBTITLES_USERNAME = os.environ.get("OPENSUBTITLES_USERNAME", "").strip()
OPENSUBTITLES_PASSWORD = os.environ.get("OPENSUBTITLES_PASSWORD", "")
USERS_SERVICE_URL = os.environ.get("USERS_SERVICE_URL") or "http://users:8443"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"movies_app": {"handlers": ["console"], "level": "INFO"}},
}
