import re

from django.core.exceptions import ValidationError

# A username is what other users see and type into URLs: letters, digits and
# `. _ -`, starting with a letter or digit. Same rule as the OAuth fallback.
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 30
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
USERNAME_HELP = (
    f"Use {USERNAME_MIN_LENGTH} to {USERNAME_MAX_LENGTH} letters, digits, dots, "
    "underscores or dashes, starting with a letter or digit."
)


def validate_username(value: str) -> str:
    """The username stripped of surrounding spaces, or a ValidationError."""
    value = (value or "").strip()
    if not USERNAME_MIN_LENGTH <= len(value) <= USERNAME_MAX_LENGTH or not USERNAME_PATTERN.match(value):
        raise ValidationError(USERNAME_HELP)
    return value
