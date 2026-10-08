import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.decorators import method_decorator
from django.utils.http import urlsafe_base64_encode
from django.views.decorators.csrf import csrf_protect

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from auth_app.models import User
from auth_app.serializers import ForgotPasswordSerializer


logger = logging.getLogger(__name__)

GENERIC_RESPONSE = {
    "detail": (
        "Si un compte est associé a cette adresse email, un lien de "
        "réinitialisation vient d'etre envoyé."
    ),
}


@method_decorator(csrf_protect, name="dispatch")
@extend_schema_view(
    post=extend_schema(
        tags=["Authentication"],
        operation_id="auth_forgot_password",
    )
)
class ForgotPasswordView(CreateAPIView):
    serializer_class = ForgotPasswordSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "forgot"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(
            email=serializer.validated_data["email"],
        ).first()

        if user:
            self.send_reset_email(user)

        return Response(
            GENERIC_RESPONSE,
            status=status.HTTP_200_OK,
        )

    def send_reset_email(self, user):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        reset_url = (
            f"{settings.FRONTEND_BASE_URL}/reset-password"
            f"?uid={uid}&token={token}"
        )

        context = {
            "user": user,
            "reset_url": reset_url,
            "expiry_hours": max(
                int(settings.PASSWORD_RESET_TIMEOUT) // 3600,
                1,
            ),
        }

        subject = "Réinitialisation de votre mot de passe Hypertube"

        try:
            message = EmailMultiAlternatives(
                subject=subject,
                body=render_to_string(
                    "auth_app/password_reset_email.txt",
                    context,
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            message.attach_alternative(
                render_to_string(
                    "auth_app/password_reset_email.html",
                    context,
                ),
                "text/html",
            )
            message.send(fail_silently=False)
        except Exception:
            logger.exception(
                "Unable to send the password reset email to %s",
                user.email,
            )
