from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


@method_decorator(
    ensure_csrf_cookie,
    name="dispatch",
)
class CsrfTokenView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        responses=inline_serializer(
            name="CsrfResponse",
            fields={
                "detail": serializers.CharField(),
            },
        ),
        tags=["Authentication"],
        operation_id="auth_csrf",
    )
    def get(self, request):
        return Response(
            {
                "detail": "CSRF cookie set.",
            }
        )


def csrf_failure(request, reason=""):
    return JsonResponse(
        {
            "detail": "CSRF validation failed.",
        },
        status=403,
    )