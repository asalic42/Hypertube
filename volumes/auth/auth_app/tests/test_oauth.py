from unittest.mock import patch

import requests

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from auth_app.models import OAuthAccount, User
from auth_app.views.oauth import _state_session_key

PROFILE = {
    "sub": "google-123",
    "email": "jane@example.com",
    "email_verified": True,
    "given_name": "Jane",
    "family_name": "Doe",
    "picture": None,
}


class OAuthCallbackTests(TestCase):
    def _callback(self, profile=PROFILE):
        session = self.client.session
        session[_state_session_key("google")] = "state-1"
        session.save()
        with (
            patch("auth_app.oauth.google.exchange_code", return_value="provider-token"),
            patch("auth_app.oauth.google.fetch_profile", return_value=profile),
            patch("auth_app.views.oauth.requests.post") as post,
        ):
            post.return_value.status_code = 201
            response = self.client.get(
                reverse("oauth-google-callback"), {"code": "abc", "state": "state-1"}
            )
        return response, post

    def test_callback_logs_in_with_identifying_claims(self):
        response, post = self._callback()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], settings.OAUTH_FRONTEND_CALLBACK)
        user = User.objects.get(email="jane@example.com")
        self.assertTrue(OAuthAccount.objects.filter(user=user, provider="google").exists())

        # The refresh cookie carries the claims the other services read, so
        # every access token the refresh flow derives from it carries them too.
        refresh = RefreshToken(response.cookies[settings.REFRESH_COOKIE_NAME].value)
        self.assertEqual(refresh["username"], user.username)
        self.assertEqual(refresh["email"], "jane@example.com")
        self.assertEqual(refresh.access_token["username"], user.username)
        self.assertEqual(response.cookies[settings.SESSION_COOKIE_MARKER_NAME].value, "1")

    def test_profile_is_created_as_the_user(self):
        _, post = self._callback()
        user = User.objects.get(email="jane@example.com")

        post.assert_called_once()
        kwargs = post.call_args.kwargs
        self.assertEqual(post.call_args.args[0], f"{settings.USERS_SERVICE_BASE_URL}/api/users/")
        self.assertEqual(kwargs["json"], {"firstname": "Jane", "lastname": "Doe"})
        bearer = kwargs["headers"]["Authorization"].removeprefix("Bearer ")
        access = AccessToken(bearer)
        self.assertEqual(access["username"], user.username)
        self.assertEqual(access["email"], "jane@example.com")

    def test_users_service_outage_does_not_block_login(self):
        session = self.client.session
        session[_state_session_key("google")] = "state-1"
        session.save()
        with (
            patch("auth_app.oauth.google.exchange_code", return_value="provider-token"),
            patch("auth_app.oauth.google.fetch_profile", return_value=PROFILE),
            patch("auth_app.views.oauth.requests.post", side_effect=requests.ConnectionError),
            self.assertLogs("auth_app.views.oauth", level="WARNING"),
        ):
            response = self.client.get(
                reverse("oauth-google-callback"), {"code": "abc", "state": "state-1"}
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], settings.OAUTH_FRONTEND_CALLBACK)

    def test_unverified_email_cannot_take_over_an_account(self):
        victim = User.objects.create_user(email="jane@example.com", username="jane", password="Str0ng-pass!")

        response, post = self._callback({**PROFILE, "email_verified": False})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"{settings.FRONTEND_BASE_URL}/login?error=oauth_no_email")
        self.assertNotIn(settings.REFRESH_COOKIE_NAME, response.cookies)
        self.assertFalse(OAuthAccount.objects.filter(user=victim).exists())
        self.assertEqual(User.objects.count(), 1)
        post.assert_not_called()

    def test_already_linked_account_logs_in_without_email(self):
        user = User.objects.create_user(email="jane@example.com", username="jane", password="Str0ng-pass!")
        OAuthAccount.objects.create(user=user, provider="google", provider_user_id="google-123")

        response, _ = self._callback({**PROFILE, "email": None, "email_verified": False})

        self.assertEqual(response["Location"], settings.OAUTH_FRONTEND_CALLBACK)
        self.assertIn(settings.REFRESH_COOKIE_NAME, response.cookies)
