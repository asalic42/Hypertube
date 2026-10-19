"""Settings for `manage.py test --settings=users.settings_test`: no Postgres, no S3."""

import tempfile

from .settings import *  # noqa: F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage", "OPTIONS": {"location": tempfile.mkdtemp()}},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
