import uuid

from rest_framework.permissions import SAFE_METHODS, BasePermission


def caller_id(request):
    """The account id from the token, or None when the token has none."""
    try:
        return uuid.UUID(str(getattr(request.user, "id", "") or ""))
    except ValueError:
        return None


def is_owner(request, user_id):
    """True when the token belongs to the profile at `user_id`."""
    try:
        return bool(user_id) and caller_id(request) == uuid.UUID(str(user_id))
    except ValueError:
        return False


class IsOwnerOrReadOnly(BasePermission):
    """
    Anyone authenticated may read a profile; only its owner may change or
    delete it. The identity comes from the token, never from the request body.
    """

    message = "You may only change your own profile."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return is_owner(request, view.kwargs.get("id"))
