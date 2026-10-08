import logging
import re

import requests
from django.conf import settings

from movies_app.services import http

logger = logging.getLogger(__name__)

LANGUAGE = re.compile(r"^[a-z]{2}$")


def preferred_language(username, authorization=""):
    """Ask the users service; None when it cannot tell."""
    if not username or not re.fullmatch(r"[\w.@+-]+", username):
        return None
    try:
        payload = http.get(
            f"{settings.USERS_SERVICE_URL}/api/users/{username}/",
            headers={"Authorization": authorization} if authorization else None,
            timeout=(2, 3),
        ).json()
    except (requests.RequestException, ValueError) as error:
        logger.warning("users service lookup failed: %s", error)
        return None
    language = str(payload.get("user", {}).get("preferredLanguage", "")).lower()
    return language if LANGUAGE.match(language) else None
