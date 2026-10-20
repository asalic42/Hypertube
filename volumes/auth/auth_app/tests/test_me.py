from unittest.mock import patch

import requests
from django.conf import settings
from django.test import TestCase

from auth_app.models import User
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from auth_app.serializers import CustomTokenObtainPairSerializer


class DeleteAccountTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", username="jane", password="Str0ng-pass!")
        self.bearer = f"Bearer {CustomTokenObtainPairSerializer.get_token(self.user).access_token}"

    def delete(self):
        return self.client.delete("/api/auth/me/", HTTP_AUTHORIZATION=self.bearer)

    def test_the_other_services_erase_their_data_first(self):
        with patch("auth_app.services.requests.delete") as remote:
            remote.return_value.status_code = 204
            response = self.delete()

        self.assertEqual(response.status_code, 204)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        calls = [(call.args[0], call.kwargs["headers"]["Authorization"]) for call in remote.call_args_list]
        self.assertEqual(calls, [
            (f"{settings.USERS_SERVICE_BASE_URL}/api/users/jane/", self.bearer),
            (f"{settings.MOVIES_SERVICE_BASE_URL}/api/movies/me/", self.bearer),
        ])

    def test_a_missing_profile_is_not_an_error(self):
        with patch("auth_app.services.requests.delete") as remote:
            remote.return_value.status_code = 404
            self.assertEqual(self.delete().status_code, 204)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())

    def test_the_account_is_kept_when_a_service_cannot_erase(self):
        for failure in ({"side_effect": requests.ConnectionError()}, {"return_value.status_code": 500}):
            with patch("auth_app.services.requests.delete", **failure), self.assertLogs("auth_app.views.me", level="ERROR"):
                response = self.delete()
            self.assertEqual(response.status_code, 503, failure)
            self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_needs_a_token(self):
        self.assertEqual(self.client.delete("/api/auth/me/").status_code, 401)


class UpdateEmailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", username="jane", password="Str0ng-pass!")
        User.objects.create_user(email="bob@example.com", username="bob", password="Str0ng-pass!")
        self.bearer = f"Bearer {CustomTokenObtainPairSerializer.get_token(self.user).access_token}"

    def patch(self, email):
        return self.client.patch("/api/auth/me/", {"email": email}, content_type="application/json", HTTP_AUTHORIZATION=self.bearer)

    def test_another_account_email_is_refused_whatever_the_case(self):
        response = self.patch("Bob@Example.com")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json())
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "jane@example.com")

    def test_own_email_is_normalized(self):
        response = self.patch("  Jane.New@Example.com ")
        self.assertEqual((response.status_code, response.json()["user"]["email"]), (200, "jane.new@example.com"))
        # Changing only the case of one's own address is allowed, and a no-op.
        self.assertEqual(self.patch("JANE.NEW@example.com").status_code, 200)

    def test_new_tokens_carry_the_new_email(self):
        response = self.patch("jane.new@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AccessToken(response.json()["access"])["email"], "jane.new@example.com")
        refresh = RefreshToken(response.cookies[settings.REFRESH_COOKIE_NAME].value)
        self.assertEqual(refresh["email"], "jane.new@example.com")
