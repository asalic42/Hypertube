import re

from django.conf import settings
from django.core import mail
from django.test import TestCase
from rest_framework_simplejwt.tokens import RefreshToken

from auth_app.models import User

EMAIL, USERNAME, PASSWORD = "jane@example.com", "jane", "Str0ng-pass!"


class AuthFlowTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email=EMAIL, username=USERNAME, password=PASSWORD)

    def post(self, path, body=None, **extra):
        return self.client.post(path, body or {}, content_type="application/json", **extra)

    def login(self, username=USERNAME, password=PASSWORD):
        return self.post("/api/auth/login/", {"username": username, "password": password})

    def refresh_cookie(self, response):
        return response.cookies.get(settings.REFRESH_COOKIE_NAME)


class LoginTests(AuthFlowTestCase):
    def test_login_returns_an_access_token_and_sets_the_session_cookies(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("access", body)
        self.assertNotIn("refresh", body, "the refresh token travels only in the cookie")
        self.assertEqual(body["user"]["username"], "jane")

        refresh = self.refresh_cookie(response)
        self.assertTrue(refresh["httponly"])
        self.assertEqual(refresh["path"], settings.REFRESH_COOKIE_PATH)
        self.assertEqual(RefreshToken(refresh.value)["username"], "jane")
        self.assertEqual(response.cookies[settings.SESSION_COOKIE_MARKER_NAME].value, "1")
        self.assertFalse(response.cookies[settings.SESSION_COOKIE_MARKER_NAME]["httponly"])

    def test_wrong_credentials_are_refused_without_a_cookie(self):
        for username, password in ((USERNAME, "wrong"), ("nobody", PASSWORD), (EMAIL, PASSWORD)):
            response = self.login(username, password)
            self.assertEqual(response.status_code, 401, username)
            self.assertIsNone(self.refresh_cookie(response))

    def test_login_takes_the_username_whatever_its_case(self):
        response = self.login("JANE")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["username"], "jane")

    def test_login_without_a_username_is_a_validation_error(self):
        response = self.post("/api/auth/login/", {"email": EMAIL, "password": PASSWORD})
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.json())

    def test_verify(self):
        access = self.login().json()["access"]
        self.assertEqual(self.post("/api/auth/verify/", {"token": access}).status_code, 200)
        self.assertEqual(self.post("/api/auth/verify/", {"token": "not.a.token"}).status_code, 401)


class RefreshTests(AuthFlowTestCase):
    def test_refresh_rotates_the_cookie_and_revokes_the_previous_token(self):
        first = self.refresh_cookie(self.login()).value

        response = self.post("/api/auth/refresh/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())
        second = self.refresh_cookie(response).value
        self.assertNotEqual(first, second)

        # The old token is single use.
        self.client.cookies[settings.REFRESH_COOKIE_NAME] = first
        response = self.post("/api/auth/refresh/")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.refresh_cookie(response).value, "", "a revoked cookie is cleared")

    def test_refresh_needs_the_cookie(self):
        self.assertEqual(self.post("/api/auth/refresh/").status_code, 401)


class LogoutTests(AuthFlowTestCase):
    def test_logout_clears_the_cookies_and_revokes_the_refresh_token(self):
        login = self.login()
        access, refresh = login.json()["access"], self.refresh_cookie(login).value

        response = self.post("/api/auth/logout/", HTTP_AUTHORIZATION=f"Bearer {access}")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.refresh_cookie(response).value, "")
        self.assertEqual(response.cookies[settings.SESSION_COOKIE_MARKER_NAME].value, "")

        self.client.cookies[settings.REFRESH_COOKIE_NAME] = refresh
        self.assertEqual(self.post("/api/auth/refresh/").status_code, 401)

    def test_logout_needs_a_token(self):
        self.login()
        self.assertEqual(self.client.post("/api/auth/logout/").status_code, 401)


class PasswordResetTests(AuthFlowTestCase):
    def request_link(self, email=EMAIL):
        return self.post("/api/auth/forgot-password/", {"email": email})

    def link_from_mail(self):
        match = re.search(r"uid=(?P<uid>[^&\s]+)&token=(?P<token>[^\s\"<]+)", mail.outbox[-1].body)
        self.assertIsNotNone(match, mail.outbox[-1].body)
        return match["uid"], match["token"]

    def reset(self, uid, token, new_password="N3w-pass-word!", confirm=None):
        return self.post(
            f"/api/auth/reset-password/?uid={uid}&token={token}",
            {"new_password": new_password, "confirm_password": confirm if confirm is not None else new_password},
        )

    def test_unknown_email_gets_the_same_answer_and_no_mail(self):
        known = self.request_link()
        unknown = self.request_link("nobody@example.com")
        self.assertEqual((known.status_code, unknown.status_code), (200, 200))
        self.assertEqual(known.json(), unknown.json())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [EMAIL])
        self.assertIn(settings.FRONTEND_BASE_URL, mail.outbox[0].body)

    def test_the_link_resets_the_password_once_and_revokes_sessions(self):
        before = self.refresh_cookie(self.login()).value
        self.request_link()
        uid, token = self.link_from_mail()

        self.assertEqual(self.reset(uid, token).status_code, 200)
        self.assertEqual(self.login().status_code, 401, "the old password is gone")
        self.assertEqual(self.login(password="N3w-pass-word!").status_code, 200)

        # Sessions opened before the reset are revoked, and the link is single use.
        self.client.cookies[settings.REFRESH_COOKIE_NAME] = before
        self.assertEqual(self.post("/api/auth/refresh/").status_code, 401)
        self.assertEqual(self.reset(uid, token, "An0ther-pass!").status_code, 400)

    def test_bad_links_and_weak_or_mismatched_passwords_are_refused(self):
        self.request_link()
        uid, token = self.link_from_mail()
        self.assertEqual(self.reset(uid, "wrong-token").status_code, 400)
        self.assertEqual(self.reset("bad-uid", token).status_code, 400)
        self.assertEqual(self.reset(uid, token, "N3w-pass-word!", confirm="other").status_code, 400)
        self.assertEqual(self.reset(uid, token, "short").status_code, 400)
        self.assertEqual(self.login().status_code, 200, "nothing changed")
