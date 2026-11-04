from unittest.mock import Mock, patch

import requests

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from auth_app.models import OAuthAccount, User
from auth_app.oauth import discord, forty_two, github, google
from auth_app.serializers import CustomTokenObtainPairSerializer
from auth_app.views.oauth import _download_provider_avatar, _state_session_key

PROFILE = {
    "sub": "google-123",
    "email": "jane@example.com",
    "email_verified": True,
    "given_name": "Jane",
    "family_name": "Doe",
    "picture": None,
}


class OAuthCallbackTests(TestCase):
    def _callback(self, profile=PROFILE, provider="google", public_profile=None, avatar_response=None):
        session = self.client.session
        session[_state_session_key(provider)] = "state-1"
        session.save()
        module = {"42": "forty_two", "github": "github", "google": "google", "discord": "discord"}[provider]
        profile_response = Mock(status_code=200)
        profile_response.json.return_value = {
            "user": public_profile or {"firstname": "", "lastname": "", "avatar_url": None}
        }
        with (
            patch(f"auth_app.oauth.{module}.exchange_code", return_value="provider-token"),
            patch(f"auth_app.oauth.{module}.fetch_profile", return_value=profile),
            patch("auth_app.views.oauth.requests.get") as get,
            patch("auth_app.views.oauth.requests.patch") as patch_profile,
        ):
            get.return_value = profile_response
            if avatar_response is not None:
                get.side_effect = [profile_response, avatar_response]
            patch_profile.return_value.status_code = 200
            response = self.client.get(
                reverse(f"oauth-{provider}-callback"), {"code": "abc", "state": "state-1"}
            )
        return response, get, patch_profile

    def test_callback_logs_in_with_identifying_claims(self):
        response, _, _ = self._callback()

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
        _, get, patch_profile = self._callback()
        user = User.objects.get(email="jane@example.com")

        get.assert_called_once()
        self.assertEqual(get.call_args.args[0], f"{settings.USERS_SERVICE_BASE_URL}/api/users/{user.pk}/")
        kwargs = patch_profile.call_args.kwargs
        self.assertEqual(patch_profile.call_args.args[0], f"{settings.USERS_SERVICE_BASE_URL}/api/users/{user.pk}/")
        self.assertEqual(kwargs["json"], {"firstname": "Jane", "lastname": "Doe"})
        bearer = kwargs["headers"]["Authorization"].removeprefix("Bearer ")
        access = AccessToken(bearer)
        self.assertEqual(access["username"], user.username)
        self.assertEqual(access["email"], "jane@example.com")

    def test_discord_avatar_is_imported_even_without_a_last_name(self):
        response_image = type("ImageResponse", (), {
            "status_code": 200,
            "headers": {"Content-Type": "image/png"},
            "raise_for_status": lambda self: None,
            "iter_content": lambda self, chunk_size: iter([b"discord-image"]),
            "close": lambda self: None,
        })()
        profile = {
            "id": "discord-123",
            "email": "nova@example.com",
            "verified": True,
            "username": "nova",
            "global_name": "Nova",
            "avatar": "avatar-hash",
        }
        _, get, patch_profile = self._callback(profile, provider="discord", avatar_response=response_image)

        user = User.objects.get(email="nova@example.com")
        self.assertEqual(get.call_count, 2)
        self.assertEqual(get.call_args.args[0], "https://cdn.discordapp.com/avatars/discord-123/avatar-hash.png?size=256&format=png")
        kwargs = patch_profile.call_args.kwargs
        self.assertEqual(kwargs["data"], {"firstname": "Nova"})
        self.assertEqual(kwargs["files"]["avatar"], ("oauth-avatar.png", b"discord-image", "image/png"))
        self.assertEqual(
            AccessToken(kwargs["headers"]["Authorization"].removeprefix("Bearer "))["username"],
            user.username,
        )

    def test_provider_normalizers_expose_their_avatar_urls(self):
        self.assertEqual(
            discord.normalize({"id": "123", "avatar": "hash"})["avatar_url"],
            "https://cdn.discordapp.com/avatars/123/hash.png?size=256&format=png",
        )
        self.assertEqual(
            google.normalize({"sub": "g", "picture": "https://lh3.googleusercontent.com/a"})["avatar_url"],
            "https://lh3.googleusercontent.com/a",
        )
        self.assertEqual(
            github.normalize({"user": {"id": 1, "avatar_url": "https://avatars.githubusercontent.com/u/1"}, "emails": []})["avatar_url"],
            "https://avatars.githubusercontent.com/u/1",
        )
        self.assertEqual(
            forty_two.normalize({"id": 42, "image": {"link": "https://cdn.intra.42.fr/users/42/avatar"}})["avatar_url"],
            "https://cdn.intra.42.fr/users/42/avatar",
        )

    def test_avatar_download_accepts_each_provider_host(self):
        urls = (
            "https://cdn.discordapp.com/avatars/123/hash.png",
            "https://lh3.googleusercontent.com/a",
            "https://avatars.githubusercontent.com/u/1",
            "https://cdn.intra.42.fr/users/42/avatar",
        )
        for url in urls:
            with self.subTest(url=url):
                image = Mock(status_code=200, headers={"Content-Type": "image/webp"})
                image.iter_content.return_value = [b"provider-image"]
                with patch("auth_app.views.oauth.requests.get", return_value=image) as get:
                    self.assertEqual(
                        _download_provider_avatar(url),
                        ("oauth-avatar.webp", b"provider-image", "image/webp"),
                    )
                get.assert_called_once_with(url, timeout=5, allow_redirects=False, stream=True)
                image.close.assert_called_once()

    def test_oauth_sync_keeps_an_existing_picture(self):
        existing_profile = {"firstname": "Jane", "lastname": "Doe", "avatar_url": "https://files.example/avatar"}
        _, get, patch_profile = self._callback(public_profile=existing_profile)
        get.assert_called_once()
        patch_profile.assert_not_called()

    def test_users_service_outage_does_not_block_login(self):
        session = self.client.session
        session[_state_session_key("google")] = "state-1"
        session.save()
        with (
            patch("auth_app.oauth.google.exchange_code", return_value="provider-token"),
            patch("auth_app.oauth.google.fetch_profile", return_value=PROFILE),
            patch("auth_app.views.oauth.requests.get", side_effect=requests.ConnectionError),
            self.assertLogs("auth_app.views.oauth", level="WARNING"),
        ):
            response = self.client.get(
                reverse("oauth-google-callback"), {"code": "abc", "state": "state-1"}
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], settings.OAUTH_FRONTEND_CALLBACK)

    def test_unverified_email_cannot_take_over_an_account(self):
        victim = User.objects.create_user(email="jane@example.com", username="jane", password="Str0ng-pass!")

        response, get, patch_profile = self._callback({**PROFILE, "email_verified": False})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"{settings.FRONTEND_BASE_URL}/login?error=oauth_no_email")
        self.assertNotIn(settings.REFRESH_COOKIE_NAME, response.cookies)
        self.assertFalse(OAuthAccount.objects.filter(user=victim).exists())
        self.assertEqual(User.objects.count(), 1)
        get.assert_not_called()
        patch_profile.assert_not_called()

    def test_already_linked_account_logs_in_without_email(self):
        user = User.objects.create_user(email="jane@example.com", username="jane", password="Str0ng-pass!")
        OAuthAccount.objects.create(user=user, provider="google", provider_user_id="google-123")

        response, _, _ = self._callback({**PROFILE, "email": None, "email_verified": False})

        self.assertEqual(response["Location"], settings.OAUTH_FRONTEND_CALLBACK)
        self.assertIn(settings.REFRESH_COOKIE_NAME, response.cookies)

    def test_a_new_oauth_account_has_no_password_and_reports_its_provider(self):
        self._callback()
        user = User.objects.get(email="jane@example.com")
        self.assertFalse(user.has_usable_password())

        bearer = CustomTokenObtainPairSerializer.get_token(user).access_token
        response = self.client.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {bearer}")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["has_password"])
        self.assertEqual(response.json()["oauth_providers"], ["google"])


class OAuthUsernameTests(TestCase):
    def test_the_username_does_not_collide_with_an_existing_one_in_another_case(self):
        from auth_app.views.oauth import _unique_username

        User.objects.create_user(email="first@example.com", username="Jane", password="Str0ng-pass-word")

        self.assertEqual(_unique_username("jane", "jane@example.com"), "jane_2")
        # Login looks the username up whatever its case: a second "jane" would break it for both.
        self.assertEqual(User.objects.get_by_natural_key("JANE").username, "Jane")
