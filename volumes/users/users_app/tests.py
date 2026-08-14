from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

from .models import PublicUser

class HealthApiTestCase(APITestCase):
    
    url = reverse('health')
    
    def test_get_health(self):
    
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected = {
            "status": "ok",
            "service": "users",
        }
        self.assertEqual(response.data, expected)



class UsersApiTestCase(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.users = [
            PublicUser.objects.create(
                username='testuser1',
                firstname='fn1',
                lastname='ln1',
                email='testuser1@example.com'
            ),
            PublicUser.objects.create(
                username='testuser2',
                firstname='fn2',
                lastname='ln2',
                email='testuser2@example.com'
            )
        ]


    url = reverse('user-list')

    def test_get_users(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected = {
            "users": [
                {
                    "id": user.id,
                    "username": user.username,
                    "firstname": user.firstname,
                    "lastname": user.lastname,
                    "email": user.email,
                    "avatar": user.avatar,
                    "preferredLanguage": user.preferredLanguage,
                } for user in self.users
            ]
        }
        self.assertEqual(response.data, expected)

    def test_create_user(self):
        data = {
            "username": "newuser",
            "firstname": "New",
            "lastname": "User",
            "email": "newuser@example.com",
            "preferredLanguage": "fr",
            "avatar": "",
        }
        response = self.client.post(self.url, data=data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PublicUser.objects.count(), 3)
        self.assertEqual(response.data["user"], {
            "id": PublicUser.objects.get(username="newuser").id,
            "username": "newuser",
            "firstname": "New",
            "lastname": "User",
            "email": "newuser@example.com",
            "avatar": "",
            "preferredLanguage": "fr",
        })



class UsernameApiTestCase(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.users = [
            PublicUser.objects.create(
                username='testuser1',
                firstname='fn1',
                lastname='ln1',
                email='testuser1@example.com'
            ),
            PublicUser.objects.create(
                username='testuser2',
                firstname='fn2',
                lastname='ln2',
                email='testuser2@example.com'
            )
        ]

    def test_get_user(self):
        user = self.users[0]
        url = reverse('user', args=[user.username])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected = {
            "id": user.id,
            "username": user.username,
            "firstname": user.firstname,
            "lastname": user.lastname,
            "email": user.email,
            "avatar": user.avatar,
            "preferredLanguage": user.preferredLanguage,
        }
        self.assertEqual(response.data["user"], expected)

    def test_get_user_not_found(self):
        url = reverse('user', args=['nonexistentuser'])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "No PublicUser matches the given query.")

    def test_alter_user(self):
        user = self.users[0]
        url = reverse('user', args=[user.username])
        data = {
            "firstname": "UpdatedFirstName",
            "lastname": "UpdatedLastName",
            "preferredLanguage": "es"
        }
        response = self.client.patch(url, data=data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.firstname, "UpdatedFirstName")
        self.assertEqual(user.lastname, "UpdatedLastName")
        self.assertEqual(user.preferredLanguage, "es")