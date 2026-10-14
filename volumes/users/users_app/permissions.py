from rest_framework.permissions import SAFE_METHODS, BasePermission


def is_owner(request, username):
    """True when the token belongs to the profile at `username`."""
    return bool(username) and getattr(request.user, "username", "") == username


class IsOwnerOrReadOnly(BasePermission):
    """
    Anyone authenticated may read a profile; only its owner may change or
    delete it. The identity comes from the token, never from the request body.
    """

    message = "You may only change your own profile."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return is_owner(request, view.kwargs.get("username"))
