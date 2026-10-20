"""Settings for `manage.py test --settings=auth.settings_test`: no Postgres."""

import os

# The real settings refuse to start without these: tests provide their own.
os.environ.setdefault("AUTH_SECRET_KEY", "test-only-" + "k" * 60)
os.environ.setdefault("DJANGO_ALLOWED_HOSTS", "testserver,localhost")


from .settings import *  # noqa: F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

# One process runs every test: rate limits would carry over between them.
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_CLASSES": ()}  # noqa: F405
