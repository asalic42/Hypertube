from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from auth_app.serializers import CustomTokenObtainPairSerializer

@extend_schema(
    tags=["Authentication"],
    operation_id="auth_login",
)
class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]
    authentification_classes = []
    throttle_scope = "login"


@extend_schema(
    tags=["Authentication"],
    operation_id="auth_refresh",
)
class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    authentification_classes = []
    throttle_scope = "refresh"    


@extend_schema(
    tags=["Authentication"],
    operation_id="auth_verify",
)
class VerifyView(TokenVerifyView):
    permission_classes = [AllowAny]
    authentification_classes = []
    throttle_scope = "verify"