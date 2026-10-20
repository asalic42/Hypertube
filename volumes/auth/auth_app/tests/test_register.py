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

    def test_malformed_usernames_are_refused(self):
        for username in ("ab", "a" * 31, "jane doe", "<script>", "jane@doe", ".jane", "", "   "):
            response = self.register(username=username)
            self.assertEqual(response.status_code, 400, repr(username))
            self.assertIn("username", response.json())
        self.assertEqual(User.objects.count(), 0)

    def test_username_is_unique_whatever_the_case(self):
        self.assertEqual(self.register().status_code, 201)
        response = self.register(username="Jane.Doe", email="other@example.com")
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.json())

    def test_email_is_unique_whatever_the_case(self):
        self.assertEqual(self.register().status_code, 201)
        response = self.register(username="other", email="  Jane@Example.COM ")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json())
        self.assertEqual(User.objects.count(), 1)

    def test_email_is_stored_lower_case_and_logs_in_whatever_the_case(self):
        self.assertEqual(self.register(email="Jane@Example.com").status_code, 201)
        self.assertEqual(User.objects.get().email, "jane@example.com")
        response = self.client.post(
            "/api/auth/login/", {"email": "JANE@example.com", "password": VALID["password"]}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())

    def test_forgot_password_finds_the_account_whatever_the_case(self):
        self.assertEqual(self.register().status_code, 201)
        response = self.client.post("/api/auth/forgot-password/", {"email": "JANE@Example.com"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["jane@example.com"])
