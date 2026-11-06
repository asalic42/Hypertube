"""OAuth2 / OIDC provider implementation for Google.

Everything specific to the Google provider lives here so the rest of the
code (views, models) stays provider agnostic. Mirrors the structure of
`forty_two.py`.
"""

from __future__ import annotations

import requests
from authlib.integrations.requests_client import OAuth2Session
from django.conf import settings


PROVIDER = "google"

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

SCOPE = "openid email profile"
TIMEOUT = 10


def is_configured() -> bool:
    return bool(settings.GOOGLE_UID and settings.GOOGLE_SECRET)


def build_authorize_url(state: str) -> str:
    """Build the URL the browser is redirected to so the user can authorize."""
    session = OAuth2Session(
        client_id=settings.GOOGLE_UID,
        client_secret=settings.GOOGLE_SECRET,
        scope=SCOPE,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )
    uri, _ = session.create_authorization_url(
        AUTHORIZE_URL,
        state=state,
        prompt="select_account",
    )
    return uri


def exchange_code(code: str) -> str:
    """Exchange the authorization code for an access token (server to server)."""
    session = OAuth2Session(
        client_id=settings.GOOGLE_UID,
        client_secret=settings.GOOGLE_SECRET,
        scope=SCOPE,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
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


def normalize(data: dict) -> dict:
    """Map the provider payload to a common profile shape."""
    return {
        "provider": PROVIDER,
        "provider_user_id": str(data["sub"]),
        "email": data.get("email"),
        "email_verified": bool(data.get("email_verified")),
        "username": None,
        "first_name": data.get("given_name") or "",
        "last_name": data.get("family_name") or "",
        "avatar_url": data.get("picture"),
    }
