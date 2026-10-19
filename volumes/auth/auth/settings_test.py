"""Settings for `manage.py test --settings=auth.settings_test`: no Postgres."""

from .settings import *  # noqa: F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
