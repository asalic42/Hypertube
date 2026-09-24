from pathlib import Path
from datetime import timedelta
import os


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-hypertube-dev-secret-key")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "movies_app",
]

MIDDLEWARE = [
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
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "30/minute",
        # A playing video alone issues many range requests.
        "user": "1200/minute",
    },
}


def read_key_file(env_variable: str, default: str) -> str:
    path = Path(os.getenv(env_variable) or default)
    # Without the key every token is rejected: the service fails closed.
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

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# File storage (S3) for the downloaded movies and their subtitles.
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_MOVIES_STORAGE_BUCKET_NAME = os.environ.get("AWS_MOVIES_STORAGE_BUCKET_NAME") or "movies"
AWS_S3_ENDPOINT_URL = os.environ.get("AWS_S3_ENDPOINT_URL")
AWS_S3_REGION_NAME = os.environ.get("AWS_S3_REGION_NAME") or "us-east-1"

# Torrents: working directory shared by the web and worker containers.
MOVIES_DOWNLOAD_DIR = os.environ.get("MOVIES_DOWNLOAD_DIR") or "/downloads"
TORRENT_LISTEN_PORT = int(os.environ.get("TORRENT_LISTEN_PORT") or 6881)
# A stored movie nobody watched for this long is erased.
MOVIE_RETENTION_DAYS = 30
# Lower resolutions encoded once a movie is stored; only those below the source's height are made.
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
