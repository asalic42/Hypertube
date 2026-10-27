import io
import uuid
from types import SimpleNamespace
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APITestCase

from users_app.models import PublicUser
from users_app.services import account


def token_user(username, email=None, user_id=None):
    """What JWTStatelessUserAuthentication hands the views: the token's claims."""
    return SimpleNamespace(
        id=str(user_id or uuid.uuid4()),
        pk=None,
        username=username,
        email=email or f"{username}@example.test",
        is_authenticated=True,
        is_anonymous=False,
    )


class UsersApiTests(APITestCase):
    def setUp(self):
        self.ana = PublicUser.objects.create(id=uuid.uuid4(), username="ana", email="ana@example.test", firstname="Ana", lastname="Lopez")
        self.bob = PublicUser.objects.create(id=uuid.uuid4(), username="bob", email="bob@example.test")
        self.client.force_authenticate(token_user("ana", "ana@example.test", self.ana.pk))

    def url(self, user, suffix=""):
        return f"/api/users/{getattr(user, 'pk', user)}/{suffix}"

    def test_everything_needs_a_token(self):
        self.client.force_authenticate(None)
        for method, url in (("get", "/api/users/"), ("get", self.url(self.ana)), ("patch", self.url(self.ana)), ("get", self.url(self.ana, "avatar/"))):
            self.assertEqual(getattr(self.client, method)(url).status_code, 401, url)
        self.assertEqual(self.client.get("/api/users/health/").status_code, 200)

    def test_list_exposes_ids_and_usernames_only(self):
        response = self.client.get("/api/users/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["users"], [{"id": str(self.ana.pk), "username": "ana"}, {"id": str(self.bob.pk), "username": "bob"}])

    def test_profiles_are_addressed_by_the_account_id(self):
        self.assertEqual(self.client.get(self.url(self.ana)).data["user"]["id"], str(self.ana.pk))
        self.assertEqual(self.client.get("/api/users/ana/").status_code, 404, "the username is not an address")
        self.assertEqual(self.client.get(self.url(uuid.uuid4())).status_code, 404)

    def test_email_is_only_shown_to_its_owner(self):
        own = self.client.get(self.url(self.ana)).data["user"]
        other = self.client.get(self.url(self.bob)).data["user"]
        self.assertEqual(own["email"], "ana@example.test")
        self.assertNotIn("email", other)
        self.assertEqual((other["username"], other["firstname"]), ("bob", ""))

    def test_only_the_owner_updates_or_deletes(self):
        self.assertEqual(self.client.patch(self.url(self.bob), {"firstname": "Hacked"}).status_code, 403)
        self.assertEqual(self.client.delete(self.url(self.bob)).status_code, 403)
        self.assertEqual(self.client.patch(self.url(self.bob, "avatar/"), {}).status_code, 403)
        self.assertEqual(self.client.delete(self.url(self.bob, "avatar/")).status_code, 403)
        self.bob.refresh_from_db()
        self.assertEqual(self.bob.firstname, "")

        response = self.client.patch(self.url(self.ana), {"firstname": "Anita", "preferredLanguage": "es"})
        self.assertEqual((response.status_code, response.data["user"]["firstname"], response.data["user"]["preferredLanguage"]), (200, "Anita", "es"))
        self.assertEqual(self.client.delete(self.url(self.ana)).status_code, 200)
        self.assertFalse(PublicUser.objects.filter(pk=self.ana.pk).exists())

    def test_profile_is_created_for_the_token_identity(self):
        carl = token_user("carl", "carl@example.test")
        self.client.force_authenticate(carl)
        response = self.client.post("/api/users/", {"firstname": "Carl", "lastname": "Sagan", "preferredLanguage": "fr", "username": "ana", "email": "x@example.test", "id": str(self.ana.pk)})
        self.assertEqual(response.status_code, 201)
        # The body cannot pick another identity.
        user = response.data["user"]
        self.assertEqual((user["id"], user["username"], user["email"], user["firstname"]), (carl.id, "carl", "carl@example.test", "Carl"))
        self.assertEqual(self.client.post("/api/users/", {"firstname": "Again", "lastname": "Sagan"}).status_code, 409)

    def test_missing_own_profile_is_created_on_read(self):
        dora = token_user("dora", "dora@example.test")
        self.client.force_authenticate(dora)
        response = self.client.get(self.url(dora.id))
        self.assertEqual((response.status_code, response.data["user"]["email"]), (200, "dora@example.test"))
        self.assertTrue(PublicUser.objects.filter(pk=dora.id, username="dora").exists())

    def test_missing_picture_is_not_an_error(self):
        response = self.client.get(self.url(self.bob, "avatar/"))
        self.assertEqual((response.status_code, response.data["avatar_url"]), (200, None))

    def test_names_are_required(self):
        eve = token_user("eve", "eve@example.test")
        self.client.force_authenticate(eve)
        for body in ({}, {"firstname": "Eve"}, {"firstname": " ", "lastname": "Adams"}, {"firstname": "Eve", "lastname": ""}):
            response = self.client.post("/api/users/", body)
            self.assertEqual(response.status_code, 400, body)
        self.assertFalse(PublicUser.objects.filter(username="eve").exists())

        response = self.client.post("/api/users/", {"firstname": "  Eve ", "lastname": "Adams"})
        self.assertEqual((response.status_code, response.data["user"]["firstname"]), (201, "Eve"))

        # A name can be changed but not emptied.
        self.assertEqual(self.client.patch(self.url(eve.id), {"lastname": ""}).status_code, 400)
        self.assertEqual(self.client.patch(self.url(eve.id), {"lastname": "Smith"}).status_code, 200)

    def test_the_profile_email_follows_the_token(self):
        # After the auth service changed the email, the token carries the new one and the profile follows.
        self.client.force_authenticate(token_user("ana", "ana.new@example.test", self.ana.pk))
        response = self.client.get(self.url(self.ana))
        self.assertEqual(response.data["user"]["email"], "ana.new@example.test")
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.email, "ana.new@example.test")

    def test_a_stale_profile_with_the_same_username_is_replaced(self):
        # Bob's account was deleted but his profile stayed; a new account took the username.
        new_bob = token_user("bob", "bob2@example.test")
        self.client.force_authenticate(new_bob)
        with self.assertLogs("users_app.views.public_users", level="WARNING"):
            response = self.client.get(self.url(new_bob.id))
        self.assertEqual((response.status_code, response.data["user"]["username"]), (200, "bob"))
        self.assertFalse(PublicUser.objects.filter(pk=self.bob.pk).exists())

    def test_an_email_held_by_another_profile_is_released_to_its_owner(self):
        # Bob's profile still shows an address the auth service now gives to Ana.
        self.client.force_authenticate(token_user("ana", "bob@example.test", self.ana.pk))
        with self.assertLogs("users_app.views.public_users", level="WARNING"):
            response = self.client.get(self.url(self.ana))
        self.assertEqual((response.status_code, response.data["user"]["email"]), (200, "bob@example.test"))
        self.bob.refresh_from_db()
        self.assertTrue(self.bob.email.endswith("@unknown.invalid"), "bob keeps his profile, only the stale address is gone")


def png(name="me.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class ProfileUpdateTests(APITestCase):
    """One PATCH for the whole profile: what the auth service owns is relayed to it."""

    def setUp(self):
        self.ana = PublicUser.objects.create(id=uuid.uuid4(), username="ana", email="ana@example.test", firstname="Ana", lastname="Lopez")
        self.client.force_authenticate(token_user("ana", "ana@example.test", self.ana.pk))
        self.url = f"/api/users/{self.ana.pk}/"

    def patch(self, body, **extra):
        return self.client.patch(self.url, body, HTTP_AUTHORIZATION="Bearer tok", **extra)

    def test_email_and_password_go_to_the_auth_service(self):
        answer = {"user": {"email": "ana.new@example.test"}, "access": "new-access"}
        with mock.patch.object(account, "update_credentials", return_value=answer) as relay:
            response = self.patch({"firstname": "Anita", "email": "Ana.New@example.test", "password": "N3w-pass!", "current_password": "old"})
        # Sent as typed: the auth service normalizes and answers with what it stored.
        relay.assert_called_once_with({"email": "Ana.New@example.test", "password": "N3w-pass!", "current_password": "old"}, "Bearer tok")
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.data["user"]["firstname"], response.data["user"]["email"], response.data["access"]), ("Anita", "ana.new@example.test", "new-access"))
        self.ana.refresh_from_db()
        self.assertEqual((self.ana.firstname, self.ana.email), ("Anita", "ana.new@example.test"))

    def test_a_refusal_of_the_auth_service_is_the_answer_and_nothing_changes(self):
        refusal = account.CredentialsRejected(400, {"current_password": ["Wrong password."]})
        with mock.patch.object(account, "update_credentials", side_effect=refusal):
            response = self.patch({"firstname": "Anita", "password": "N3w-pass!", "current_password": "wrong"})
        self.assertEqual((response.status_code, response.data), (400, {"current_password": ["Wrong password."]}))
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.firstname, "Ana")

    def test_an_unreachable_auth_service_changes_nothing(self):
        with mock.patch.object(account, "update_credentials", side_effect=account.AuthUnavailable()):
            response = self.patch({"firstname": "Anita", "email": "ana.new@example.test"})
        self.assertEqual(response.status_code, 503)
        self.ana.refresh_from_db()
        self.assertEqual((self.ana.firstname, self.ana.email), ("Ana", "ana@example.test"))

    def test_without_credentials_the_auth_service_is_not_called(self):
        with mock.patch.object(account, "update_credentials") as relay:
            response = self.patch({"firstname": "Anita"})
        relay.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("access", response.data)

    def test_the_username_cannot_change(self):
        response = self.patch({"username": "anita"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.data)

    def test_the_picture_comes_in_the_same_patch(self):
        with mock.patch("users_app.serializers.get_presigned_url", return_value="https://files.example.test/avatars/me.png"):
            response = self.patch({"lastname": "Diaz", "avatar": png()}, format="multipart")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["avatar_url"], "https://files.example.test/avatars/me.png")
        self.assertNotIn("avatar", response.data["user"], "the storage key is not exposed")
        self.ana.refresh_from_db()
        self.assertTrue(self.ana.avatar.startswith("avatars/"))
        self.assertEqual(self.ana.lastname, "Diaz")

        response = self.client.get(self.url)
        self.assertIsNone(response.data["user"]["avatar_url"], "no url when the storage cannot sign one")

    def test_a_profile_without_picture_has_no_url(self):
        self.assertIsNone(self.client.get(self.url).data["user"]["avatar_url"])


class AccountRelayTests(APITestCase):
    def test_the_relay_fetches_a_csrf_cookie_then_patches_as_the_user(self):
        session = mock.MagicMock()
        session.cookies.get.return_value = "csrf-123"
        session.patch.return_value.status_code = 200
        session.patch.return_value.json.return_value = {"user": {"email": "x@example.test"}, "access": "a"}
        with mock.patch("users_app.services.account.requests.Session", return_value=session):
            answer = account.update_credentials({"email": "x@example.test"}, "Bearer tok")
        self.assertEqual(answer["access"], "a")
        session.get.assert_called_once()
        self.assertTrue(session.get.call_args.args[0].endswith("/api/auth/csrf/"))
        url, kwargs = session.patch.call_args.args[0], session.patch.call_args.kwargs
        self.assertTrue(url.endswith("/api/auth/me/"))
        self.assertEqual(kwargs["json"], {"email": "x@example.test"})
        self.assertEqual((kwargs["headers"]["Authorization"], kwargs["headers"]["X-CSRFToken"]), ("Bearer tok", "csrf-123"))

    def test_refusals_and_outages_are_told_apart(self):
        session = mock.MagicMock()
        session.patch.return_value.status_code = 400
        session.patch.return_value.json.return_value = {"email": ["taken"]}
        with mock.patch("users_app.services.account.requests.Session", return_value=session):
            with self.assertRaises(account.CredentialsRejected) as refused:
                account.update_credentials({"email": "x@example.test"}, "Bearer tok")
        self.assertEqual((refused.exception.status_code, refused.exception.body), (400, {"email": ["taken"]}))

        session.patch.return_value.status_code = 500
        with mock.patch("users_app.services.account.requests.Session", return_value=session):
            with self.assertRaises(account.AuthUnavailable):
                account.update_credentials({"email": "x@example.test"}, "Bearer tok")
