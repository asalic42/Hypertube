"""Security emails about an account, sent after the change is stored."""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def send_password_notification(user, created: bool) -> None:
    """
    Tell the account owner that a password was created or changed. Never let a
    mail failure undo the change: the password is already stored.
    """
    context = {
        "user": user,
        "created": created,
        "login_url": f"{settings.FRONTEND_BASE_URL}/login",
    }
    subject = (
        "Votre mot de passe Hypertube a été créé"
        if created
        else "Votre mot de passe Hypertube a été modifié"
    )

    try:
        message = EmailMultiAlternatives(
            subject=subject,
            body=render_to_string("auth_app/password_notification_email.txt", context),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        message.attach_alternative(
            render_to_string("auth_app/password_notification_email.html", context),
            "text/html",
        )
        message.send(fail_silently=False)
    except Exception:
        logger.exception("Unable to send the password notification to %s", user.email)
