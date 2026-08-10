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
    "auth_app.apps.AuthAppConfig",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "auth.urls"

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "https://localhost:8080"
]

CSRF_TRUSTED_ORIGINS = [
    "https://localhost:8080",
    "https://127.0.0.1:8080",
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

WSGI_APPLICATION = "auth.wsgi.application"
ASGI_APPLICATION = "auth.asgi.application"

SPECTACULAR_SETTINGS = {
    "TITLE": "auth API",
    "DESCRIPTION": "API de gestion de l'authentification.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("AUTH_USER"),
        "PASSWORD": os.getenv("AUTH_PASSWORD"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT"),
        "OPTIONS": {
            "sslmode": "verify-full",
            "sslrootcert": "/certs/ca.crt",
        },
    }
}

AUTH_USER_MODEL = "auth_app.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication."
        "JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions."
        "IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS":
        "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling."
        "AnonRateThrottle",
        "rest_framework.throttling."
        "UserRateThrottle",
        "rest_framework.throttling."
        "ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "600/minute",
        "register": "5/minute",
        "login": "10/minute",
        "refresh": "30/minute",
        "verify": "60/minute",
    },
}


 def read_required_file(env_variable: str) -> str:
     path = os.getenv(env_variable)
     if not path:
         raise RuntimeError(f"Missing {env_variable}")
    return Path(path).read_text(encoding="utf-8")

JWT_PRIVATE_KEY = read_required_file("JWT_PRIVATE_KEY_PATH")


JWT_PUBLIC_KEY = read_required_file("JWT_PUBLIC_KEY_PATH")


SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":
        timedelta(minutes=10),
    "REFRESH_TOKEN_LIFETIME":
        timedelta(days=7),
    "ROTATE_REFRESH_TOKENS":
        True,
    "BLACKLIST_AFTER_ROTATION":
        True,
    "UPDATE_LAST_LOGIN":
        False,
    "ALGORITHM":
        "RS256",
    "SIGNING_KEY":
        JWT_PRIVATE_KEY,
    "VERIFYING_KEY":
        JWT_PUBLIC_KEY,
    "ISSUER":
        "auth-service",
    "AUDIENCE":
        "hypertube",
    "AUTH_HEADER_TYPES": (
        "Bearer",
    ),
    "USER_ID_FIELD":
        "id",
    "USER_ID_CLAIM":
        "sub",
    "TOKEN_TYPE_CLAIM":
        "token_type",
    "JTI_CLAIM":
        "jti",
    "LEEWAY":
        5,
}


SPECTACULAR_SETTINGS = {
    "TITLE": "auth API",
    "DESCRIPTION":
        "Authentication service for Hypertube",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)
