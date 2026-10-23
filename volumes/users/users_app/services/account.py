"""
The part of a profile the auth service owns: email and password. A profile
update relays them there, as the user, with their own bearer token.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TIMEOUT = 5
CSRF_COOKIE = "csrftoken"
CSRF_HEADER = "X-CSRFToken"


class CredentialsRejected(Exception):
    """The auth service refused the change: its answer is the user's to read."""

    def __init__(self, status_code, body):
        super().__init__(f"auth service answered {status_code}")
        self.status_code = status_code
        self.body = body


class AuthUnavailable(Exception):
    """The auth service could not be reached or failed."""


def update_credentials(fields, authorization):
    """
    PATCH /api/auth/me/ with `fields` (email, password, current_password) as
    the user. Returns the auth service's answer: the account and a fresh
    access token. The auth views are CSRF-protected like any browser-facing
    view, so a CSRF cookie is fetched first and sent back with its header.
    """
    base = settings.AUTH_SERVICE_URL
    session = requests.Session()
    try:
        session.get(f"{base}/api/auth/csrf/", timeout=TIMEOUT).raise_for_status()
        csrf_token = session.cookies.get(CSRF_COOKIE, "")
        response = session.patch(
            f"{base}/api/auth/me/",
            json=fields,
            headers={"Authorization": authorization, CSRF_HEADER: csrf_token, "Referer": f"{base}/"},
            timeout=TIMEOUT,
        )
    except requests.RequestException as error:
        logger.warning("auth service unreachable: %s", error)
        raise AuthUnavailable() from error

    if response.status_code == 200:
        return response.json()
    if response.status_code in (400, 401):
        try:
            body = response.json()
        except ValueError:
            body = {"detail": response.text[:200]}
        raise CredentialsRejected(response.status_code, body)
    logger.error("auth service answered %s to a profile update: %s", response.status_code, response.text[:200])
    raise AuthUnavailable()
