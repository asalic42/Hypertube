from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def root(request):
    return JsonResponse({"service": "users-api", "status": "ok"})


urlpatterns = [
    path("", root),
    path("api/users/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/users/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/users/admin/", admin.site.urls),
    path("api/users/", include("users_app.urls")),
] + static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT
)
