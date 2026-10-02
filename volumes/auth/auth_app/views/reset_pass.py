from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.utils.encoding import force_str
from django.utils.decorators import method_decorator
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.csrf import csrf_protect

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from auth_app.models import User
from auth_app.serializers import ResetPasswordSerializer


INVALID_TOKEN_RESPONSE = {
    "detail": "Ce lien est invalide ou a expire. Merci d'en redemander un."
}


@method_decorator(csrf_protect, name="dispatch")
@extend_schema_view(
    post=extend_schema(
        tags=["Authentication"],
        operation_id="auth_reset_password",
    )
)
class ResetPasswordView(CreateAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "reset"

    def post(self, request, *args, **kwargs):
        user = self.get_user_from_token(
            request.query_params.get("uid", ""),
            request.query_params.get("token", ""),
        )

        if user is None:
            return Response(
                INVALID_TOKEN_RESPONSE,
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.context["user"] = user
        serializer.is_valid(raise_exception=True)

        user.set_password(
            serializer.validated_data["new_password"],
        )
        user.save(update_fields=["password", "updated_at"])

        self.revoke_user_sessions(user)

        return Response(
            {
                "detail": "Mot de passe mis a jour. "
                        "Vous pouvez vous connecter.",
            },
            status=status.HTTP_200_OK,
        )

    def get_user_from_token(self, uid, token):
        if not uid or not token:
            return None

        try:
            pk = force_str(urlsafe_base64_decode(uid))
        except (TypeError, ValueError):
            return None

        try:
            user = User.objects.filter(pk=pk).first()
        except (ValidationError, ValueError):
            return None

        if user is None:
            return None

        if not default_token_generator.check_token(user, token):
            return None

        return user

    def revoke_user_sessions(self, user):
        for outstanding_token in OutstandingToken.objects.filter(
            user=user,
        ):
            BlacklistedToken.objects.get_or_create(
                token=outstanding_token,
            )
