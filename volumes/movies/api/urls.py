from django.urls import include, path

from .views import HealthView
from . import views 


user_urlpatterns = [
    path("create/", views.MovieCreateView.as_view(), name="movie-create"),
]


urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("movies/", include((user_urlpatterns, "api"))),
]