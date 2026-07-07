from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def root(request):
    return JsonResponse({"service": "users-api", "status": "ok"})


urlpatterns = [
    path("", root),
    path("api/", include("api.urls")),
    path("admin/", admin.site.urls),
]