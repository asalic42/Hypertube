"""OAuth2 provider implementation for GitHub.

Everything specific to the GitHub provider lives here so the rest of the
code (views, models) stays provider agnostic. Mirrors the structure of
`forty_two.py` and `google.py`.

Notes:
- GitHub requires a valid `User-Agent` header on every API request, or it
  answers with a 403.
- The email is only exposed through `/user/emails` (needs the `user:email`
  scope) and only when the user has a verified address.
"""

from __future__ import annotations

import requests
from authlib.integrations.requests_client import OAuth2Session
from django.conf import settings


PROVIDER = "github"

AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"
USER_URL = "https://api.github.com/user"
EMAILS_URL = "https://api.github.com/user/emails"

SCOPE = "read:user user:email"
TIMEOUT = 10


def is_configured() -> bool:
    return bool(settings.GITHUB_UID and settings.GITHUB_SECRET)


def build_authorize_url(state: str) -> str:
    """Build the URL the browser is redirected to so the user can authorize."""
    session = OAuth2Session(
        client_id=settings.GITHUB_UID,
        client_secret=settings.GITHUB_SECRET,
        scope=SCOPE,
        redirect_uri=settings.GITHUB_REDIRECT_URI,
    )
    uri, _ = session.create_authorization_url(AUTHORIZE_URL, state=state)
    return uri


def exchange_code(code: str) -> str:
    """Exchange the authorization code for an access token (server to server)."""
    session = OAuth2Session(
        client_id=settings.GITHUB_UID,
        client_secret=settings.GITHUB_SECRET,
        scope=SCOPE,
        redirect_uri=settings.GITHUB_REDIRECT_URI,
    )
    token = session.fetch_token(TOKEN_URL, code=code)
    return token["access_token"]


def _headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "Hypertube",
    }


def fetch_profile(access_token: str) -> dict:
    """Fetch the authenticated user's profile and email addresses."""
    headers = _headers(access_token)

    user = requests.get(USER_URL, headers=headers, timeout=TIMEOUT)
    user.raise_for_status()

    emails = requests.get(EMAILS_URL, headers=headers, timeout=TIMEOUT)
    emails.raise_for_status()

    return {"user": user.json(), "emails": emails.json()}


def _pick_email(emails: list[dict]) -> str | None:
    """Return the primary verified email, else the first verified one."""
    for entry in emails:
        if entry.get("primary") and entry.get("verified"):
            return entry.get("email")
    for entry in emails:
        if entry.get("verified"):
            return entry.get("email")
    return None


def _split_name(name: str | None) -> tuple[str, str]:
    if not name:
        return "", ""
    parts = name.split()
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def normalize(data: dict) -> dict:
    """Map the provider payload to a common profile shape."""
    user = data["user"]
    emails = data.get("emails") or []

    email = _pick_email(emails)
    first_name, last_name = _split_name(user.get("name"))

    return {
        "provider": PROVIDER,
        "provider_user_id": str(user["id"]),
        "email": email,
        "email_verified": bool(email),
        "username": user.get("login"),
        "first_name": first_name,
        "last_name": last_name,
        "avatar_url": user.get("avatar_url"),
    }
