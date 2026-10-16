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
from django.db import transaction
from django.http import HttpResponseRedirect
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from auth_app.cookies import set_refresh_cookie
from auth_app.models import OAuthAccount, User
from auth_app.oauth import forty_two, github, google


logger = logging.getLogger(__name__)

# Maps the URL slug used by the frontend to the provider module.
# Routes are built with `as_view(provider=<slug>)`.
PROVIDERS = {
    "42": forty_two,
    "github": github,
    "google": google,
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
    base = re.sub(r"[^A-Za-z0-9_.-]", "", base)[:30] or "user"

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

    email = profile.get("email")

    # Link to an existing account only when the email is verified.
    if email and profile.get("email_verified"):
        existing = User.objects.filter(email__iexact=email).first()
        if existing:
            OAuthAccount.objects.create(
                user=existing,
                provider=provider,
                provider_user_id=provider_user_id,
            )
            return existing

    if not email:
        raise OAuthUserError("oauth_no_email")

    user = User.objects.create_user(
        email=email,
        username=_unique_username(profile.get("username"), email),
    )
    OAuthAccount.objects.create(
        user=user,
        provider=provider,
        provider_user_id=provider_user_id,
    )
    return user


def sync_public_user(user: User, profile: dict) -> None:
    """Best effort creation of the matching PublicUser in the users service.

    Must never make the login fail: failures are only logged.
    """
    payload = {
        "username": user.username,
        "email": user.email,
        "firstname": profile.get("first_name") or "",
        "lastname": profile.get("last_name") or "",
    }
    url = f"{settings.USERS_SERVICE_BASE_URL}/api/users/"

    try:
        response = requests.post(url, json=payload, timeout=5)
    except requests.RequestException:
        logger.warning("PublicUser sync request failed", exc_info=True)
        return

    if response.status_code not in (200, 201):
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

        sync_public_user(user, profile)

        refresh = RefreshToken.for_user(user)
        response = HttpResponseRedirect(settings.OAUTH_FRONTEND_CALLBACK)
        set_refresh_cookie(response, str(refresh))
        return response
