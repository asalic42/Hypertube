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
            (f"{settings.USERS_SERVICE_BASE_URL}/api/users/{self.user.pk}/", self.bearer),
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

    def test_the_username_cannot_change(self):
        response = self.client.patch("/api/auth/me/", {"username": "janet"}, content_type="application/json", HTTP_AUTHORIZATION=self.bearer)
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.json())
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "jane")

    def test_new_tokens_carry_the_new_email(self):
        response = self.patch("jane.new@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AccessToken(response.json()["access"])["email"], "jane.new@example.com")
        refresh = RefreshToken(response.cookies[settings.REFRESH_COOKIE_NAME].value)
        self.assertEqual(refresh["email"], "jane.new@example.com")


class UpdatePasswordTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", username="jane", password="Str0ng-pass!")
        self.bearer = f"Bearer {CustomTokenObtainPairSerializer.get_token(self.user).access_token}"

    def patch(self, **body):
        return self.client.patch("/api/auth/me/", body, content_type="application/json", HTTP_AUTHORIZATION=self.bearer)

    def login(self, password):
        return self.client.post("/api/auth/login/", {"username": "jane", "password": password}, content_type="application/json")

    def test_the_current_password_is_required_and_checked(self):
        response = self.patch(password="N3w-pass-word!")
        self.assertEqual((response.status_code, list(response.json())), (400, ["current_password"]))
        response = self.patch(password="N3w-pass-word!", current_password="wrong")
        self.assertEqual((response.status_code, list(response.json())), (400, ["current_password"]))
        self.assertEqual(self.login("Str0ng-pass!").status_code, 200, "nothing changed")

    def test_the_new_password_is_validated(self):
        response = self.patch(password="short", current_password="Str0ng-pass!")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.json())
        self.assertEqual(self.patch(password="", current_password="Str0ng-pass!").status_code, 400)

    def test_the_password_changes(self):
        response = self.patch(password="N3w-pass-word!", current_password="Str0ng-pass!")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("password", response.json()["user"])
        self.assertEqual(self.login("Str0ng-pass!").status_code, 401)
        self.assertEqual(self.login("N3w-pass-word!").status_code, 200)

    def test_email_and_password_change_together(self):
        response = self.patch(email="jane.new@example.com", password="N3w-pass-word!", current_password="Str0ng-pass!")
        self.assertEqual((response.status_code, response.json()["user"]["email"]), (200, "jane.new@example.com"))
        self.assertEqual(self.login("N3w-pass-word!").status_code, 200)
