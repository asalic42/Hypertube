from django.urls import include, path

from .views import HealthView
from . import views 


user_urlpatterns = [
]


urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("auth/", include((user_urlpatterns, "api"))),
]