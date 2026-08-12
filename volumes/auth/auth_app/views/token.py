from django.conf import settings
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,

)
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.serializers import TokenVerifySerializer
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import (
    InvalidToken,
    TokenError,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from auth_app.cookies import set_refresh_cookie

from auth_app.serializers import CustomTokenObtainPairSerializer


@method_decorator(csrf_protect, name="dispatch")
@extend_schema_view(
    post=extend_schema(
        tags=["Authentication"],
        operation_id="auth_login",
    )
)
class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        refresh_token = response.data.pop("refresh", None)
        if refresh_token:
            set_refresh_cookie(response, refresh_token)
        return response


@method_decorator(csrf_protect, name="dispatch")
@extend_schema_view(
    post=extend_schema(
        request=None,
        tags=["Authentication"],
        operation_id="auth_refresh",
    )
)
class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "refresh"

    def post(self, request, *args, **kwargs):
        raw_refresh_token = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not raw_refresh_token:
            return Response(
                {
                    "detail":"Refresh token missing."
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
        
        serializer = self.get_serializer(data={"refresh":raw_refresh_token,})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0]) from exc
        data = dict(serializer.validated_data)
        new_refresh_token = data.pop("refresh", None)
        response = Response(data, status=status.HTTP_200_OK)

        if new_refresh_token:
            set_refresh_cookie(response, new_refresh_token)
        return response


@extend_schema_view(
    post=extend_schema(
        request=TokenVerifySerializer,
        tags=["Authentication"],
        operation_id="auth_verify",
    )
)
class VerifyView(TokenVerifyView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "verify"