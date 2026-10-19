"""OAuth2 provider implementation for 42's intra (api.intra.42.fr).

Everything specific to the 42 provider lives here so the rest of the
code (views, models) stays provider agnostic.
"""

from __future__ import annotations

import requests
from authlib.integrations.requests_client import OAuth2Session
from django.conf import settings


PROVIDER = "forty_two"

AUTHORIZE_URL = "https://api.intra.42.fr/oauth/authorize"
TOKEN_URL = "https://api.intra.42.fr/oauth/token"
USERINFO_URL = "https://api.intra.42.fr/v2/me"

SCOPE = "public"
TIMEOUT = 10


def is_configured() -> bool:
    return bool(settings.FORTY_TWO_UID and settings.FORTY_TWO_SECRET)


def build_authorize_url(state: str) -> str:
    """Build the URL the browser is redirected to so the user can authorize."""
    session = OAuth2Session(
        client_id=settings.FORTY_TWO_UID,
        client_secret=settings.FORTY_TWO_SECRET,
        scope=SCOPE,
        redirect_uri=settings.FORTY_TWO_REDIRECT_URI,
    )
    uri, _ = session.create_authorization_url(AUTHORIZE_URL, state=state)
    return uri


def exchange_code(code: str) -> str:
    """Exchange the authorization code for an access token (server to server)."""
    session = OAuth2Session(
        client_id=settings.FORTY_TWO_UID,
        client_secret=settings.FORTY_TWO_SECRET,
        scope=SCOPE,
        redirect_uri=settings.FORTY_TWO_REDIRECT_URI,
    )
    token = session.fetch_token(TOKEN_URL, code=code)
    return token["access_token"]


def fetch_profile(access_token: str) -> dict:
    """Fetch the authenticated user's profile from the provider."""
    response = requests.get(
        USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def _extract_avatar_url(data: dict) -> str | None:
    """Extract the avatar from 42 and returns it as an object."""
    image = data.get("image")
    if isinstance(image, dict):
        return image.get("link")
    if isinstance(image, str):
        return image
    return data.get("image_url")


def normalize(data: dict) -> dict:
    """Map the provider payload to a common profile shape."""
    return {
        "provider": PROVIDER,
        "provider_user_id": str(data["id"]),
        "email": data.get("email"),
        "email_verified": True,
        "username": data.get("login"),
        "first_name": data.get("first_name") or "",
        "last_name": data.get("last_name") or "",
        "avatar_url": _extract_avatar_url(data),
    }
