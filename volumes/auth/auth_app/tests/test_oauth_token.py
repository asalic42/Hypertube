import base64

from django.test import TestCase
from rest_framework_simplejwt.tokens import AccessToken

from auth_app.models import ApiClient, User
from auth_app.serializers import CustomTokenObtainPairSerializer

PASSWORD = "Str0ng-pass!"


class OAuthTokenTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", username="jane", password=PASSWORD)
        self.bearer = f"Bearer {CustomTokenObtainPairSerializer.get_token(self.user).access_token}"

    def create_client(self, name="my script", bearer=None):
        return self.client.post(
            "/api/auth/oauth/clients/", {"name": name}, content_type="application/json", HTTP_AUTHORIZATION=bearer or self.bearer
        )

    def token(self, data=None, **extra):
        # Form-encoded, as RFC 6749 clients send it.
        return self.client.post("/api/auth/oauth/token/", data or {}, **extra)


class ApiClientTests(OAuthTokenTestCase):
    def test_the_secret_is_shown_once(self):
        response = self.create_client()
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(set(body), {"client_id", "name", "created_at", "last_used_at", "client_secret"})
        self.assertNotEqual(ApiClient.objects.get().secret_hash, body["client_secret"], "stored hashed")

        listing = self.client.get("/api/auth/oauth/clients/", HTTP_AUTHORIZATION=self.bearer).json()
        self.assertEqual([c["client_id"] for c in listing], [body["client_id"]])
        self.assertNotIn("client_secret", listing[0])

    def test_clients_need_a_session_and_a_name(self):
        self.assertEqual(self.client.post("/api/auth/oauth/clients/", {"name": "x"}, content_type="application/json").status_code, 401)
        self.assertEqual(self.client.get("/api/auth/oauth/clients/").status_code, 401)
        self.assertEqual(self.create_client(name="  ").status_code, 400)

    def test_only_the_owner_revokes_a_client(self):
        client_id = self.create_client().json()["client_id"]
        other = User.objects.create_user(email="bob@example.com", username="bob", password=PASSWORD)
        other_bearer = f"Bearer {CustomTokenObtainPairSerializer.get_token(other).access_token}"
        self.assertEqual(self.client.delete(f"/api/auth/oauth/clients/{client_id}/", HTTP_AUTHORIZATION=other_bearer).status_code, 404)
        self.assertEqual(self.client.delete(f"/api/auth/oauth/clients/{client_id}/", HTTP_AUTHORIZATION=self.bearer).status_code, 204)
        self.assertFalse(ApiClient.objects.exists())

    def test_clients_go_with_the_account(self):
        self.create_client()
        self.user.delete()
        self.assertFalse(ApiClient.objects.exists())


class ClientCredentialsGrantTests(OAuthTokenTestCase):
    def setUp(self):
        super().setUp()
        created = self.create_client().json()
        self.client_id, self.client_secret = created["client_id"], created["client_secret"]

    def test_client_and_secret_give_a_token_for_their_owner(self):
        response = self.token({"grant_type": "client_credentials", "client_id": self.client_id, "client_secret": self.client_secret})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store")
        body = response.json()
        self.assertEqual(set(body), {"access_token", "token_type", "expires_in"})
        self.assertEqual(body["token_type"], "Bearer")
        self.assertEqual(body["expires_in"], 600)
        self.assertNotIn("refresh", self.client.cookies, "no browser session is opened")

        claims = AccessToken(body["access_token"])
        self.assertEqual((claims["username"], claims["email"], claims["client_id"]), ("jane", "jane@example.com", self.client_id))

        me = self.client.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {body['access_token']}")
        self.assertEqual((me.status_code, me.json()["username"]), (200, "jane"))
        self.assertIsNotNone(ApiClient.objects.get().last_used_at)

    def test_credentials_in_a_basic_authorization_header(self):
        header = "Basic " + base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        response = self.token({"grant_type": "client_credentials"}, HTTP_AUTHORIZATION=header)
        self.assertEqual(response.status_code, 200)

    def test_json_bodies_are_accepted_too(self):
        response = self.client.post(
            "/api/auth/oauth/token/",
            {"grant_type": "client_credentials", "client_id": self.client_id, "client_secret": self.client_secret},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    def test_wrong_or_unknown_credentials_are_refused_alike(self):
        for client_id, secret in ((self.client_id, "wrong"), ("00000000-0000-0000-0000-000000000000", self.client_secret), ("not-a-uuid", "x")):
            response = self.token({"grant_type": "client_credentials", "client_id": client_id, "client_secret": secret})
            self.assertEqual(response.status_code, 401, client_id)
            self.assertEqual(response.json()["error"], "invalid_client")
            self.assertIn("Basic", response["WWW-Authenticate"])

    def test_a_revoked_client_gives_no_token(self):
        self.client.delete(f"/api/auth/oauth/clients/{self.client_id}/", HTTP_AUTHORIZATION=self.bearer)
        response = self.token({"grant_type": "client_credentials", "client_id": self.client_id, "client_secret": self.client_secret})
        self.assertEqual(response.status_code, 401)

    def test_missing_fields_and_unknown_grants(self):
        response = self.token({"grant_type": "client_credentials"})
        self.assertEqual((response.status_code, response.json()["error"]), (400, "invalid_request"))
        response = self.token({"grant_type": "authorization_code", "code": "x"})
        self.assertEqual((response.status_code, response.json()["error"]), (400, "unsupported_grant_type"))
        response = self.token({})
        self.assertEqual((response.status_code, response.json()["error"]), (400, "invalid_request"))


class PasswordGrantTests(OAuthTokenTestCase):
    def test_username_and_password_give_a_token(self):
        response = self.token({"grant_type": "password", "username": "JANE", "password": PASSWORD})
        self.assertEqual(response.status_code, 200)
        claims = AccessToken(response.json()["access_token"])
        self.assertEqual(claims["username"], "jane")
        self.assertNotIn("client_id", claims)

    def test_wrong_password_is_an_invalid_grant(self):
        response = self.token({"grant_type": "password", "username": "jane", "password": "wrong"})
        self.assertEqual((response.status_code, response.json()["error"]), (400, "invalid_grant"))
        response = self.token({"grant_type": "password", "username": "jane"})
        self.assertEqual((response.status_code, response.json()["error"]), (400, "invalid_request"))
