import uuid
from types import SimpleNamespace

from rest_framework.test import APITestCase

from users_app.models import PublicUser


def token_user(username, email=None):
    """What JWTStatelessUserAuthentication hands the views: the token's claims."""
    return SimpleNamespace(
        id=str(uuid.uuid4()),
        pk=None,
        username=username,
        email=email or f"{username}@example.test",
        is_authenticated=True,
        is_anonymous=False,
    )


class UsersApiTests(APITestCase):
    def setUp(self):
        self.ana = PublicUser.objects.create(username="ana", email="ana@example.test", firstname="Ana", lastname="Lopez")
        self.bob = PublicUser.objects.create(username="bob", email="bob@example.test")
        self.client.force_authenticate(token_user("ana", "ana@example.test"))

    def test_everything_needs_a_token(self):
        self.client.force_authenticate(None)
        for method, url in (("get", "/api/users/"), ("get", "/api/users/ana/"), ("patch", "/api/users/ana/"), ("get", "/api/users/ana/avatar/")):
            self.assertEqual(getattr(self.client, method)(url).status_code, 401, url)
        self.assertEqual(self.client.get("/api/users/health/").status_code, 200)

    def test_list_exposes_ids_and_usernames_only(self):
        response = self.client.get("/api/users/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["users"], [{"id": self.ana.pk, "username": "ana"}, {"id": self.bob.pk, "username": "bob"}])

    def test_email_is_only_shown_to_its_owner(self):
        own = self.client.get("/api/users/ana/").data["user"]
        other = self.client.get("/api/users/bob/").data["user"]
        self.assertEqual(own["email"], "ana@example.test")
        self.assertNotIn("email", other)
        self.assertEqual((other["username"], other["firstname"]), ("bob", ""))
        self.assertEqual(self.client.get("/api/users/nobody/").status_code, 404)

    def test_only_the_owner_updates_or_deletes(self):
        self.assertEqual(self.client.patch("/api/users/bob/", {"firstname": "Hacked"}).status_code, 403)
        self.assertEqual(self.client.delete("/api/users/bob/").status_code, 403)
        self.assertEqual(self.client.patch("/api/users/bob/avatar/", {}).status_code, 403)
        self.assertEqual(self.client.delete("/api/users/bob/avatar/").status_code, 403)
        self.bob.refresh_from_db()
        self.assertEqual(self.bob.firstname, "")

        response = self.client.patch("/api/users/ana/", {"firstname": "Anita", "preferredLanguage": "es"})
        self.assertEqual((response.status_code, response.data["user"]["firstname"], response.data["user"]["preferredLanguage"]), (200, "Anita", "es"))
        self.assertEqual(self.client.delete("/api/users/ana/").status_code, 200)
        self.assertFalse(PublicUser.objects.filter(username="ana").exists())

    def test_profile_is_created_for_the_token_identity(self):
        self.client.force_authenticate(token_user("carl", "carl@example.test"))
        response = self.client.post("/api/users/", {"firstname": "Carl", "preferredLanguage": "fr", "username": "ana", "email": "x@example.test"})
        self.assertEqual(response.status_code, 201)
        # The body cannot pick another identity.
        self.assertEqual((response.data["user"]["username"], response.data["user"]["email"], response.data["user"]["firstname"]), ("carl", "carl@example.test", "Carl"))
        self.assertEqual(self.client.post("/api/users/", {"firstname": "Again"}).status_code, 409)

    def test_missing_own_profile_is_created_on_read(self):
        self.client.force_authenticate(token_user("dora", "dora@example.test"))
        response = self.client.get("/api/users/dora/")
        self.assertEqual((response.status_code, response.data["user"]["email"]), (200, "dora@example.test"))
        self.assertTrue(PublicUser.objects.filter(username="dora").exists())

    def test_missing_picture_is_not_an_error(self):
        response = self.client.get("/api/users/bob/avatar/")
        self.assertEqual((response.status_code, response.data["avatar_url"]), (200, None))
