"""
The OAuth2 token endpoint of the API (RFC 6749), and the client credentials
a user issues for it. The tokens it returns are the same JWTs as the login's,
so every service accepts them as the user.
"""

import base64
import binascii
import secrets
import uuid

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_app.models import ApiClient
from auth_app.serializers import (
    ApiClientCreatedSerializer,
    ApiClientCreateSerializer,
    ApiClientSerializer,
    CustomTokenObtainPairSerializer,
    OAuthErrorSerializer,
    OAuthTokenRequestSerializer,
    OAuthTokenResponseSerializer,
)

MAX_CLIENTS_PER_USER = 10

# Checked against when the client id is unknown, so that a wrong id and a
# wrong secret take the same time to refuse.
_NO_CLIENT_HASH = make_password(secrets.token_urlsafe(32))


class OAuthError(Exception):
    def __init__(self, error, description, status_code=status.HTTP_400_BAD_REQUEST):
        super().__init__(description)
        self.error = error
        self.description = description
        self.status_code = status_code


def _basic_credentials(request):
    """The client id and secret of an HTTP Basic Authorization header, if any."""
    header = request.META.get("HTTP_AUTHORIZATION", "")
    scheme, _, encoded = header.partition(" ")
    if scheme.lower() != "basic" or not encoded:
        return None
    try:
        decoded = base64.b64decode(encoded.strip(), validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        raise OAuthError("invalid_client", "The Authorization header is malformed.", status.HTTP_401_UNAUTHORIZED)
    client_id, _, client_secret = decoded.partition(":")
    return client_id, client_secret


def _client_credentials_user(data, request):
    basic = _basic_credentials(request)
    client_id = data.get("client_id") or (basic and basic[0])
    client_secret = data.get("client_secret") or (basic and basic[1])
    if not client_id or not client_secret:
        raise OAuthError("invalid_request", "client_id and client_secret are required.")

    client = _client(client_id)
    if client is None:
        check_password(client_secret, _NO_CLIENT_HASH)  # same cost as a real check
        raise OAuthError("invalid_client", "Unknown client or wrong secret.", status.HTTP_401_UNAUTHORIZED)
    if not check_password(client_secret, client.secret_hash):
        raise OAuthError("invalid_client", "Unknown client or wrong secret.", status.HTTP_401_UNAUTHORIZED)

    ApiClient.objects.filter(pk=client.pk).update(last_used_at=timezone.now())
    return client.user, client


def _client(client_id):
    try:
        client_id = uuid.UUID(str(client_id))
    except ValueError:
        return None
    return ApiClient.objects.select_related("user").filter(pk=client_id).first()


def _password_user(data, request):
    username, password = data.get("username"), data.get("password")
    if not username or not password:
        raise OAuthError("invalid_request", "username and password are required.")
    user = authenticate(request, username=username, password=password)
    if user is None:
        raise OAuthError("invalid_grant", "Wrong username or password.")
    return user, None


GRANTS = {
    "client_credentials": _client_credentials_user,
    "password": _password_user,
}


@method_decorator(csrf_exempt, name="dispatch")
class OAuthTokenView(APIView):
    """
    POST oauth/token: an access token for the API. The token is a bearer JWT
    with the same claims as the one the login issues, so the other services
    treat the caller as the user who owns the credentials. No cookie is set
    and no refresh token is returned: a client asks again with its credentials.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "login"

    @extend_schema(
        tags=["Authentication"],
        operation_id="oauth_token",
        request={"application/x-www-form-urlencoded": OAuthTokenRequestSerializer, "application/json": OAuthTokenRequestSerializer},
        responses={
            200: OAuthTokenResponseSerializer,
            400: OAuthErrorSerializer,
            401: OpenApiResponse(response=OAuthErrorSerializer, description="Unknown client or wrong secret."),
        },
        description=(
            "RFC 6749 token endpoint. `grant_type=client_credentials` takes a `client_id` and `client_secret` "
            "issued at /api/auth/oauth/clients/, in the body or in an HTTP Basic Authorization header. "
            "`grant_type=password` takes the account's `username` and `password`."
        ),
    )
    def post(self, request):
        try:
            form = OAuthTokenRequestSerializer(data=request.data)
            if not form.is_valid():
                if "grant_type" in form.errors and request.data.get("grant_type"):
                    raise OAuthError("unsupported_grant_type", "Use client_credentials or password.")
                field, messages = next(iter(form.errors.items()))
                raise OAuthError("invalid_request", f"{field}: {messages[0]}")
            user, client = GRANTS[form.validated_data["grant_type"]](form.validated_data, request)
        except OAuthError as error:
            response = Response(
                {"error": error.error, "error_description": error.description},
                status=error.status_code,
                headers={"Cache-Control": "no-store"},
            )
            if error.status_code == status.HTTP_401_UNAUTHORIZED:
                response["WWW-Authenticate"] = 'Basic realm="hypertube"'
            return response

        token = CustomTokenObtainPairSerializer.get_token(user)
        if client is not None:
            token["client_id"] = str(client.pk)
        access = token.access_token
        return Response(
            {
                "access_token": str(access),
                "token_type": "Bearer",
                "expires_in": int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
            },
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
        )


@method_decorator(csrf_protect, name="dispatch")
class ApiClientListView(APIView):
    """The caller's API clients: list them, or issue a new one and get its secret once."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Authentication"], operation_id="oauth_clients_list", responses=ApiClientSerializer(many=True))
    def get(self, request):
        return Response(ApiClientSerializer(request.user.api_clients.all(), many=True).data)

    @extend_schema(
        tags=["Authentication"],
        operation_id="oauth_clients_create",
        request=ApiClientCreateSerializer,
        responses={201: ApiClientCreatedSerializer, 400: OpenApiResponse(description="Invalid name or too many clients.")},
        description="Creates a client for the token endpoint. The secret is shown in this answer only.",
    )
    def post(self, request):
        form = ApiClientCreateSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        if request.user.api_clients.count() >= MAX_CLIENTS_PER_USER:
            return Response(
                {"detail": f"You may hold at most {MAX_CLIENTS_PER_USER} API clients: delete one first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        secret = secrets.token_urlsafe(32)
        client = ApiClient.objects.create(user=request.user, name=form.validated_data["name"], secret_hash=make_password(secret))
        client.client_secret = secret
        return Response(ApiClientCreatedSerializer(client).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_protect, name="dispatch")
class ApiClientDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Authentication"],
        operation_id="oauth_clients_delete",
        responses={204: None, 404: OpenApiResponse(description="Not one of your clients.")},
        description="Revokes a client: its credentials no longer give tokens. Tokens already issued expire on their own.",
    )
    def delete(self, request, client_id):
        deleted, _ = request.user.api_clients.filter(pk=client_id).delete()
        if not deleted:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
