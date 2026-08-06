from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def root(request):
    return JsonResponse({"service": "movies-api", "status": "ok"})


urlpatterns = [
    path("", root),
    path("api/movies/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/movies/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/movies/admin", admin.site.urls),
    path("api/movies", include("movies_app.urls")),
]