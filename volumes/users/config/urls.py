from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def root(request):
    return JsonResponse({"service": "users-api", "status": "ok"})


urlpatterns = [
    path("", root),
    path("users/api/", include("api.urls")),
    path("users/api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "users/api/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("users/admin/", admin.site.urls),
]
