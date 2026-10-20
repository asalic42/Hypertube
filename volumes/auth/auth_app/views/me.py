import logging

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError


from auth_app.serializers import UserSerializer, UserUpdateSerializer
from auth_app.cookies import delete_refresh_cookie
from auth_app.services import RemoteError, delete_user_data

logger = logging.getLogger(__name__)


@method_decorator(csrf_protect, name="dispatch")
class MeView(RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    @extend_schema(
        tags=["Authentication"],
        operation_id="auth_current_user",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        request=UserUpdateSerializer,
        responses=UserSerializer,
        tags=["Authentication"],
        operation_id="auth_update_current_user",
        description="Changes the email of the current user.",
    )
    def patch(self, request, *args, **kwargs):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)

    @extend_schema(
        request=None,
        responses={204: None, 503: None},
        tags=["Authentication"],
        operation_id="auth_delete_current_user",
        description=(
            "Deletes the account and everything the other services hold about it: "
            "profile and picture, comments, watch history. When one of them cannot "
            "erase its part the account is kept and 503 is returned, to try again later."
        ),
    )
    def delete(self, request, *args, **kwargs):
        # The other services check the user's own token, so nothing but the
        # account owner can trigger this, and nothing is left behind.
        try:
            delete_user_data(request.user.username, request.META.get("HTTP_AUTHORIZATION", ""))
        except RemoteError as error:
            logger.error("account %s not deleted, a service kept its data: %s", request.user.pk, error)
            return Response(
                {"detail": "The account could not be deleted right now, please try again later."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        raw_refresh_token = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)

        if raw_refresh_token:
            try:
                refresh_token = RefreshToken(raw_refresh_token)
                token_user_id = refresh_token.get("sub")
                if str(token_user_id) == str(request.user.pk):
                    refresh_token.blacklist()
            except TokenError:
                pass

        request.user.delete()
        response = Response(status=status.HTTP_204_NO_CONTENT)
        delete_refresh_cookie(response)
        return response