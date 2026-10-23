import logging
import re
import uuid

import requests
from django.conf import settings

from movies_app.services import http

logger = logging.getLogger(__name__)

LANGUAGE = re.compile(r"^[a-z]{2}$")


def preferred_language(user_id, authorization=""):
    """Ask the users service for the account's choice; None when it cannot tell."""
    try:
        user_id = uuid.UUID(str(user_id or ""))
    except ValueError:
        return None
    try:
        payload = http.get(
            f"{settings.USERS_SERVICE_URL}/api/users/{user_id}/",
            headers={"Authorization": authorization} if authorization else None,
            timeout=(2, 3),
        ).json()
    except (requests.RequestException, ValueError) as error:
        logger.warning("users service lookup failed: %s", error)
        return None
    language = str(payload.get("user", {}).get("preferredLanguage", "")).lower()
    return language if LANGUAGE.match(language) else None
