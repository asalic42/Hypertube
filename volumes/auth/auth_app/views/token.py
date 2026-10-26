from django.conf import settings
from drf_spectacular.utils import (
    OpenApiResponse,
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
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from auth_app.cookies import set_refresh_cookie, delete_refresh_cookie

from auth_app.models import User
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
        responses={
            200: OpenApiResponse(description="A new access token; the refresh cookie is rotated."),
            204: OpenApiResponse(description="No session to refresh: the cookie is missing, expired, revoked or belongs to a deleted account. The session cookies are cleared."),
        },
        tags=["Authentication"],
        operation_id="auth_refresh",
        description=(
            "The browser's session endpoint, driven by the refresh cookie. When there is no session "
            "to refresh it answers 204 and clears the cookies rather than an error: the page asks on "
            "every load, and a stale cookie is not a failure worth an error in the browser console."
        ),
    )
)
class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "refresh"

    def post(self, request, *args, **kwargs):
        raw_refresh_token = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        try:
            if not raw_refresh_token:
                raise TokenError("no cookie")
            old_refresh_token = RefreshToken(raw_refresh_token)
            user = User.objects.get(pk=old_refresh_token[api_settings.USER_ID_CLAIM])
        except (TokenError, User.DoesNotExist, KeyError):
            response = Response(status=status.HTTP_204_NO_CONTENT)
            delete_refresh_cookie(response)
            return response

        # Minted from the account as it is now: a username or email changed
        # through another service is in the new tokens, not the old claims.
        new_refresh_token = CustomTokenObtainPairSerializer.get_token(user)
        old_refresh_token.blacklist()

        response = Response({"access": str(new_refresh_token.access_token)}, status=status.HTTP_200_OK)
        set_refresh_cookie(response, str(new_refresh_token))
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
