from rest_framework import permissions
import jwt
from django.conf import settings


def is_ms(request, ms):
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return False

    try:
        token_type, token = auth_header.split()
        if token_type != 'Bearer':
            return False

        decoded_token = jwt.decode(
            token,
            settings.SIMPLE_JWT['VERIFYING_KEY'],
            algorithms=[settings.SIMPLE_JWT['ALGORITHM']]
        )

        service_name = decoded_token.get('service_name')
        if service_name != ms:
            return False
        return True

    except (ValueError, jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return False

class IsAuth(permissions.BasePermission):
    def has_permission(self, request, view):
        return is_ms(request, 'auth')

class IsAvatarManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return is_ms(request, 'avatar_manager')

class IsMatchmaking(permissions.BasePermission):
    def has_permission(self, request, view):
        return is_ms(request, 'matchmaking')


class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        print(obj.username)
        print(request.user.username)
        return obj.username == request.user.username 

class IsAuthenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated

class IsAuthOrAuthenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user:
            return request.user.is_authenticated 
        return is_ms(request, 'auth') 
