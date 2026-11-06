from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAuthorOrReadOnly(BasePermission):
    """Any authenticated user reads a comment, only its author changes it."""

    def has_object_permission(self, request, view, obj):
        return request.method in SAFE_METHODS or str(obj.user_id) == str(request.user.id)
