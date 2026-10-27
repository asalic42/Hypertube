"""Settings for `manage.py test --settings=users.settings_test`: no Postgres, no S3."""

import os

# The real settings refuse to start without these: tests provide their own.
os.environ.setdefault("USERS_SECRET_KEY", "test-only-" + "k" * 60)
os.environ.setdefault("DJANGO_ALLOWED_HOSTS", "testserver,localhost")

import tempfile

from .settings import *  # noqa: F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage", "OPTIONS": {"location": tempfile.mkdtemp()}},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# One process runs every test: rate limits would carry over between them.
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_CLASSES": ()}  # noqa: F405
