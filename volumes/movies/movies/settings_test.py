"""Settings for `manage.py test --settings=movies.settings_test`: no Postgres, no network services."""

import os

# The real settings refuse to start without these: tests provide their own.
os.environ.setdefault("MOVIES_SECRET_KEY", "test-only-" + "k" * 60)
os.environ.setdefault("DJANGO_ALLOWED_HOSTS", "testserver,localhost")


from .settings import *  # noqa: F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_CLASSES": ()}  # noqa: F405
TMDB_API_KEY = ""
OPENSUBTITLES_API_KEY = ""
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler", "level": "WARNING"}},
    "loggers": {"movies_app": {"handlers": ["console"], "level": "WARNING"}},
}
