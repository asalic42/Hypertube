from django.conf import settings
from django.core import mail
from django.test import TestCase

from auth_app.models import User

VALID = {"username": "jane.doe", "email": "jane@example.com", "password": "Str0ng-pass!", "password_confirmation": "Str0ng-pass!"}


class RegisterTests(TestCase):
    def register(self, **overrides):
        return self.client.post("/api/auth/register/", {**VALID, **overrides}, content_type="application/json")

    def test_valid_username_creates_and_logs_in(self):
        response = self.register(username="  jane.doe ")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["user"]["username"], "jane.doe")
        self.assertIn("access", response.json())

    def refused(self, response, field, message=None):
        # A refusal is an expected answer, sent as 200 so the browser logs no error: no token, no cookie.
        self.assertEqual(response.status_code, 200, message)
        self.assertEqual(list(response.json()), ["errors"], message)
        self.assertIn(field, response.json()["errors"], message)
        self.assertNotIn(settings.REFRESH_COOKIE_NAME, response.cookies, message)

    def test_malformed_usernames_are_refused(self):
        for username in ("ab", "a" * 31, "jane doe", "<script>", "jane@doe", ".jane", "", "   "):
            self.refused(self.register(username=username), "username", repr(username))
        self.assertEqual(User.objects.count(), 0)

    def test_username_is_unique_whatever_the_case(self):
        self.assertEqual(self.register().status_code, 201)
        self.refused(self.register(username="Jane.Doe", email="other@example.com"), "username")

    def test_email_is_unique_whatever_the_case(self):
        self.assertEqual(self.register().status_code, 201)
        self.refused(self.register(username="other", email="  Jane@Example.COM "), "email")
        self.assertEqual(User.objects.count(), 1)

    def test_email_is_stored_lower_case(self):
        self.assertEqual(self.register(email="Jane@Example.com").status_code, 201)
        self.assertEqual(User.objects.get().email, "jane@example.com")

    def test_the_new_account_logs_in_with_its_username(self):
        self.assertEqual(self.register().status_code, 201)
        response = self.client.post(
            "/api/auth/login/", {"username": VALID["username"], "password": VALID["password"]}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())

    def test_forgot_password_finds_the_account_whatever_the_case(self):
        self.assertEqual(self.register().status_code, 201)
        response = self.client.post("/api/auth/forgot-password/", {"email": "JANE@Example.com"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["jane@example.com"])
