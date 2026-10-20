"""Calls to the other services, made as the user with their own bearer token."""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TIMEOUT = 5


class RemoteError(Exception):
    """A service that holds the user's data could not erase it."""


def _delete(url, authorization, accepted=(204, 200, 404)):
    try:
        response = requests.delete(url, headers={"Authorization": authorization}, timeout=TIMEOUT)
    except requests.RequestException as error:
        raise RemoteError(f"{url}: {error}") from error
    if response.status_code not in accepted:
        raise RemoteError(f"{url}: {response.status_code} {response.text[:200]}")


def delete_user_data(username, authorization):
    """
    Erase what the users and movies services hold about an account: profile
    and picture, comments and watch history. A missing profile is fine.
    Raises RemoteError when any service could not do it, so the caller can
    keep the account rather than leave orphaned data behind.
    """
    _delete(f"{settings.USERS_SERVICE_BASE_URL}/api/users/{username}/", authorization)
    _delete(f"{settings.MOVIES_SERVICE_BASE_URL}/api/movies/me/", authorization)
