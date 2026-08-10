from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated

from auth_app.serializers import UserSerializer


@extend_schema(
    tags=["Authentication"],
    operation_id="auth_current_user",
)
class MeView(RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = (
        IsAuthenticated,
    )

    def get_object(self):
        return self.request.user