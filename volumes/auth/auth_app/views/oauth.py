"""OAuth (OmniAuth) entry points for the auth service.

Providers are registered in `PROVIDERS` and wired through the URL config
with `as_view(provider=<slug>)` (see `urls.py`). The flow is the standard
authorization code flow:

    browser -> /start/ -> provider -> /callback/ -> (JWT refresh cookie)
    -> frontend /oauth/callback

The `state` (CSRF protection) is stored server side in the session, under
a per-provider key so several provider flows can coexist.
"""

from __future__ import annotations

import logging
import re
import secrets
from urllib.parse import urlsplit

import requests
from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import HttpResponseRedirect
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from auth_app.cookies import set_refresh_cookie
from auth_app.models import OAuthAccount, User
from auth_app.oauth import discord, forty_two, github, google
from auth_app.serializers import CustomTokenObtainPairSerializer
from auth_app.validators import USERNAME_MAX_LENGTH, USERNAME_MIN_LENGTH


logger = logging.getLogger(__name__)

AVATAR_MAX_BYTES = 5 * 1024 * 1024
AVATAR_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
AVATAR_ALLOWED_HOSTS = {
    "cdn.discordapp.com",
    "cdn.intra.42.fr",
}
AVATAR_ALLOWED_HOST_SUFFIXES = (
    ".googleusercontent.com",
    ".githubusercontent.com",
)

# Maps the URL slug used by the frontend to the provider module.
# Routes are built with `as_view(provider=<slug>)`.
PROVIDERS = {
    "42": forty_two,
    "github": github,
    "google": google,
    "discord": discord,
}


def _state_session_key(provider: str) -> str:
    return f"oauth_{provider}_state"


class OAuthUserError(Exception):
    """Raised when we cannot map a provider profile to a local user."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _unique_username(raw_username: str | None, email: str) -> str:
    base = (raw_username or email.split("@")[0] or "user").strip()
    # Same rule as registration: allowed characters only, a letter or digit first.
    base = re.sub(r"[^A-Za-z0-9_.-]", "", base).lstrip("._-")[:USERNAME_MAX_LENGTH]
    if len(base) < USERNAME_MIN_LENGTH:
        base = "user"

    username = base
    suffix = 2
    # Case-insensitive like registration and login: "Alice" and "alice" are the same account name.
    while User.objects.filter(username__iexact=username).exists():
        tail = f"_{suffix}"
        username = base[: 30 - len(tail)] + tail
        suffix += 1
    return username


@transaction.atomic
def resolve_user(profile: dict) -> User:
    """Find, link or create the local User for a provider profile."""
    provider = profile["provider"]
    provider_user_id = profile["provider_user_id"]

    account = (
        OAuthAccount.objects.select_related("user")
        .filter(provider=provider, provider_user_id=provider_user_id)
        .first()
    )
    if account:
        return account.user

    # Only a verified email may identify an account: anyone can type someone
    # else's address into a provider profile, and linking on it would hand
    # them that person's account. Providers that do not verify say so.
    email = profile.get("email")
    if not email or not profile.get("email_verified"):
        raise OAuthUserError("oauth_no_email")

    # Accounts sharing the same email are merged into a single local user.
    existing = User.objects.filter(email__iexact=email).first()
    if existing:
        OAuthAccount.objects.create(
            user=existing,
            provider=provider,
            provider_user_id=provider_user_id,
        )
        return existing

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                email=email,
                username=_unique_username(profile.get("username"), email),
            )
    except IntegrityError:
        # Concurrent signup/oauth for the same email: link to the winner.
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            raise

    OAuthAccount.objects.create(
        user=user,
        provider=provider,
        provider_user_id=provider_user_id,
    )
    return user


def sync_public_user(user: User, profile: dict, access_token: str) -> None:
    """Best effort creation and initial population of the matching public profile.

    The users service takes the username and email from the bearer token, so
    the call is made as the user, with the access token just minted for them.
    Must never make the login fail: failures are only logged.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"{settings.USERS_SERVICE_BASE_URL}/api/users/{user.pk}/"

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=5,
        )
    except requests.RequestException:
        logger.warning("PublicUser lookup failed", exc_info=True)
        return

    if response.status_code != 200:
        logger.warning(
            "PublicUser lookup returned %s: %s",
            response.status_code,
            response.text[:200],
        )
        return

    try:
        public_profile = response.json()["user"]
    except (KeyError, TypeError, ValueError):
        logger.warning("PublicUser lookup returned an invalid response")
        return
    if not isinstance(public_profile, dict):
        logger.warning("PublicUser lookup returned an invalid response")
        return

    payload = {}
    for field, provider_field in (("firstname", "first_name"), ("lastname", "last_name")):
        value = profile.get(provider_field)
        name = value.strip() if isinstance(value, str) else ""
        if not public_profile.get(field) and name:
            payload[field] = name

    avatar = None
    if not public_profile.get("avatar_url"):
        avatar = _download_provider_avatar(profile.get("avatar_url"))

    if not payload and avatar is None:
        return

    try:
        if avatar:
            response = requests.patch(
                url,
                data=payload,
                files={"avatar": avatar},
                headers=headers,
                timeout=5,
            )
        else:
            response = requests.patch(url, json=payload, headers=headers, timeout=5)
    except requests.RequestException:
        logger.warning("PublicUser sync request failed", exc_info=True)
        return

    if response.status_code not in (200, 201):
        logger.warning(
            "PublicUser sync returned %s: %s",
            response.status_code,
            response.text[:200],
        )


def _download_provider_avatar(url: str | None) -> tuple[str, bytes, str] | None:
    """Download a bounded image only from the OAuth providers' avatar hosts."""
    if not isinstance(url, str) or not url:
        return None

    try:
        parsed = urlsplit(url)
        host = parsed.hostname or ""
        allowed_host = host in AVATAR_ALLOWED_HOSTS or any(
            host.endswith(suffix) for suffix in AVATAR_ALLOWED_HOST_SUFFIXES
        )
        if (
            parsed.scheme != "https"
            or parsed.username
            or parsed.password
            or parsed.port not in (None, 443)
            or not allowed_host
        ):
            logger.warning("OAuth avatar URL is not from an allowed provider host")
            return None
    except ValueError:
        logger.warning("OAuth avatar URL is invalid")
        return None

    try:
        response = requests.get(url, timeout=5, allow_redirects=False, stream=True)
        try:
            response.raise_for_status()
            if response.status_code != 200:
                logger.warning("OAuth avatar download returned %s", response.status_code)
                return None

            content_type = str(response.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
            extension = AVATAR_CONTENT_TYPES.get(content_type)
            if not extension:
                logger.warning("OAuth avatar has unsupported content type %s", content_type or "unknown")
                return None

            content = bytearray()
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                if len(content) + len(chunk) > AVATAR_MAX_BYTES:
                    logger.warning("OAuth avatar exceeds the upload size limit")
                    return None
                content.extend(chunk)
            if not content:
                logger.warning("OAuth avatar download was empty")
                return None
            return f"oauth-avatar.{extension}", bytes(content), content_type
        finally:
            response.close()
    except requests.RequestException:
        logger.warning("OAuth avatar download failed", exc_info=True)
        return None


class OAuthProviderMixin:
    """Resolve the provider module from the URL slug set at `as_view` time."""

    # Injected by `OAuthStartView.as_view(provider="google")` etc.
    provider: str | None = None

    @property
    def provider_module(self):
        module = PROVIDERS.get(self.provider)
        if module is None:
            raise ValueError(f"Unknown OAuth provider: {self.provider!r}")
        return module


@extend_schema(exclude=True)
class OAuthStartView(OAuthProviderMixin, APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "oauth"

    def get(self, request):
        module = self.provider_module
        if not module.is_configured():
            return HttpResponseRedirect(
                f"{settings.FRONTEND_BASE_URL}/login?error=oauth_not_configured"
            )

        state = secrets.token_urlsafe(32)
        request.session[_state_session_key(self.provider)] = state

        return HttpResponseRedirect(module.build_authorize_url(state))


@extend_schema(exclude=True)
class OAuthCallbackView(OAuthProviderMixin, APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "oauth"

    def _redirect_error(self, code: str) -> HttpResponseRedirect:
        return HttpResponseRedirect(
            f"{settings.FRONTEND_BASE_URL}/login?error={code}"
        )

    def get(self, request):
        module = self.provider_module

        if request.GET.get("error"):
            return self._redirect_error("oauth_denied")

        state = request.GET.get("state")
        expected_state = request.session.pop(
            _state_session_key(self.provider), None
        )
        if (
            not state
            or not expected_state
            or not secrets.compare_digest(state, expected_state)
        ):
            return self._redirect_error("oauth_state")

        code = request.GET.get("code")
        if not code:
            return self._redirect_error("oauth_failed")

        try:
            access_token = module.exchange_code(code)
            raw_profile = module.fetch_profile(access_token)
        except Exception:
            logger.exception("%s OAuth token exchange failed", self.provider)
            return self._redirect_error("oauth_failed")

        profile = module.normalize(raw_profile)

        try:
            user = resolve_user(profile)
        except OAuthUserError as exc:
            return self._redirect_error(exc.code)

        # Same claims as a password login: the other services read username
        # and email from the token, and the refresh flow copies them over.
        refresh = CustomTokenObtainPairSerializer.get_token(user)
        sync_public_user(user, profile, str(refresh.access_token))

        response = HttpResponseRedirect(settings.OAUTH_FRONTEND_CALLBACK)
        set_refresh_cookie(response, str(refresh))
        return response
