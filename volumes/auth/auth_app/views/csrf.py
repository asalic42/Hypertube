from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse
from django.middleware.csrf import get_token
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_app.serializers import CsrfTokenSerializer


@method_decorator(
    ensure_csrf_cookie,
    name="dispatch",
)
class CsrfTokenView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        responses=CsrfTokenSerializer,
        tags=["Authentication"],
        operation_id="auth_csrf",
    )
    def get(self, request):
        return Response(
            {"detail": "CSRF cookie set."}
        )


def csrf_failure(request, reason=""):
    return JsonResponse(
        {
            "detail": "CSRF validation failed.",
        },
        status=403,
    )