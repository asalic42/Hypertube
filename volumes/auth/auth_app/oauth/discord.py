"""OAuth2 provider implementation for Discord.

Everything specific to the Discord provider lives here so the rest of the
code (views, models) stays provider agnostic. Mirrors the structure of
`forty_two.py`, `github.py` and `google.py`.

Notes:
- The `email` scope makes `/users/@me` return `email` and `verified`.
- Discord has no first/last name: only `username` (handle) and `global_name`
  (display name), which we map to `first_name`.
"""

from __future__ import annotations

import requests
from authlib.integrations.requests_client import OAuth2Session
from django.conf import settings


PROVIDER = "discord"

AUTHORIZE_URL = "https://discord.com/oauth2/authorize"
TOKEN_URL = "https://discord.com/api/oauth2/token"
USER_URL = "https://discord.com/api/users/@me"

SCOPE = "identify email"
TIMEOUT = 10

CDN_BASE = "https://cdn.discordapp.com"


def is_configured() -> bool:
    return bool(settings.DISCORD_UID and settings.DISCORD_SECRET)


def build_authorize_url(state: str) -> str:
    """Build the URL the browser is redirected to so the user can authorize."""
    session = OAuth2Session(
        client_id=settings.DISCORD_UID,
        client_secret=settings.DISCORD_SECRET,
        scope=SCOPE,
        redirect_uri=settings.DISCORD_REDIRECT_URI,
    )
    uri, _ = session.create_authorization_url(AUTHORIZE_URL, state=state)
    return uri


def exchange_code(code: str) -> str:
    """Exchange the authorization code for an access token (server to server)."""
    session = OAuth2Session(
        client_id=settings.DISCORD_UID,
        client_secret=settings.DISCORD_SECRET,
        scope=SCOPE,
        redirect_uri=settings.DISCORD_REDIRECT_URI,
    )
    token = session.fetch_token(TOKEN_URL, code=code)
    return token["access_token"]


def fetch_profile(access_token: str) -> dict:
    """Fetch the authenticated user's profile from the provider."""
    response = requests.get(
        USER_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def _avatar_url(user: dict) -> str:
    """Build the avatar URL, falling back to Discord's default avatar."""
    user_id = str(user["id"])
    avatar = user.get("avatar")
    if avatar:
        ext = "gif" if avatar.startswith("a_") else "png"
        return f"{CDN_BASE}/avatars/{user_id}/{avatar}.{ext}?size=256"

    index = (int(user_id) >> 22) % 6
    return f"{CDN_BASE}/embed/avatars/{index}.png"


def normalize(data: dict) -> dict:
    """Map the provider payload to a common profile shape."""
    return {
        "provider": PROVIDER,
        "provider_user_id": str(data["id"]),
        "email": data.get("email"),
        "email_verified": bool(data.get("verified")),
        "username": data.get("username"),
        "first_name": data.get("global_name") or "",
        "last_name": "",
        "avatar_url": _avatar_url(data),
    }
