from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,

)
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny

from auth_app.models import User
from auth_app.serializers import RegisterSerializer


@extend_schema_view(
    post=extend_schema(
        tags=["Authentication"],
        operation_id="auth_register",
    )
)
class RegisterView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "register"

