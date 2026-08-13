from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

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
