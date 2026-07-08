from django.urls import path

from .views import HealthView
from .views import TestDBView


urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("test-db/", TestDBView.as_view(), name="test-db")
]