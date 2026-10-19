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
    while User.objects.filter(username=username).exists():
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
    """Best effort creation of the matching PublicUser in the users service.

    The users service takes the username and email from the bearer token, so
    the call is made as the user, with the access token just minted for them.
    Must never make the login fail: failures are only logged.
    """
    payload = {
        "firstname": profile.get("first_name") or "",
        "lastname": profile.get("last_name") or "",
    }
    # The users service requires both names. Without them the profile is
    # created from the token on the user's first read, to be completed later.
    if not payload["firstname"] or not payload["lastname"]:
        return
    url = f"{settings.USERS_SERVICE_BASE_URL}/api/users/"

    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5,
        )
    except requests.RequestException:
        logger.warning("PublicUser sync request failed", exc_info=True)
        return

    # 409: the profile already exists, which is the case on every login after the first.
    if response.status_code not in (200, 201, 409):
        logger.warning(
            "PublicUser sync returned %s: %s",
            response.status_code,
            response.text[:200],
        )


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
