from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from drf_spectacular.utils import extend_schema
from users_app.serializers import HealthSerializer


class HealthView(GenericAPIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Health"],
        operation_id="health_check",
        responses=HealthSerializer,
        description="Vérifie l'état de santé du service.",
    )
    def get(self, request):
        return Response(
            {
                "status": "ok",
                "service": "users",
            }
        )