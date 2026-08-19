from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from drf_spectacular.utils import extend_schema
from auth_app.serializers import HealthSerializer

from auth_app.serializers import HealthSerializer


class HealthView(APIView):
    permission_classes = (
        AllowAny,
    )
    authentication_classes = ()

    @extend_schema(
        responses=HealthSerializer,
        tags=["Health"],
        operation_id="auth_health",
    )
    def get(self, request):
        return Response(
            {
                "status": "ok",
                "service": "auth",
            }
        )