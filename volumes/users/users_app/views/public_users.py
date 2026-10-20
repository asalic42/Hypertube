import logging

from django.core.files.storage import default_storage
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users_app.models import PublicUser
from users_app.permissions import IsOwnerOrReadOnly, is_owner
from users_app.serializers import (
    MessageSerializer,
    PublicUserAvatarResponseSerializer,
    PublicUserAvatarUpdateSerializer,
    PublicUserCreateSerializer,
    PublicUserListResponseSerializer,
    PublicUserListSerializer,
    PublicUserResponseSerializer,
    PublicUserSerializer,
    PublicUserUpdateSerializer,
)
from users_app.services.avatars import (
    PresignedUrlError,
    delete_avatar,
    get_presigned_url,
    save_avatar,
)

logger = logging.getLogger(__name__)


def _profile(user, request):
    """A profile as the caller may see it: the email only for its owner."""
    data = PublicUserSerializer(user).data
    if not is_owner(request, user.username):
        data.pop("email", None)
    return data


def _response(message, user, request, status_code=status.HTTP_200_OK):
    return Response({"message": message, "user": _profile(user, request)}, status=status_code)


def _get_profile(request, username):
    """
    The profile at `username`. The owner's own profile is created from the
    token when it does not exist yet, so an account always has one.
    """
    email = getattr(request.user, "email", "")
    if is_owner(request, username) and email:
        user, created = PublicUser.objects.get_or_create(username=username, defaults={"email": email})
        if not created and user.email != email:
            _sync_email(user, email)
        return user
    return get_object_or_404(PublicUser, username=username)


def _sync_email(user, email):
    """
    The auth service owns the email and puts it in the token: the copy kept
    here follows it. Only a stale profile left by a deleted account can hold
    the same address; it is left alone and logged rather than crash the request.
    """
    try:
        with transaction.atomic():
            PublicUser.objects.filter(pk=user.pk).update(email=email)
    except IntegrityError:
        logger.warning("profile %s keeps email %s: %s is held by another profile", user.username, user.email, email)
        return
    user.email = email


class PublicUserView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    @extend_schema(
        tags=["Public users"],
        operation_id="get_public_user",
        responses={200: PublicUserResponseSerializer, 404: OpenApiResponse(description="Unknown user.")},
        description="Le profil public d'un utilisateur. L'email n'est renvoyé qu'à son propriétaire.",
    )
    def get(self, request, username):
        return _response("User retrieved successfully", _get_profile(request, username), request)

    @extend_schema(
        tags=["Public users"],
        operation_id="update_public_user",
        request={"multipart/form-data": PublicUserUpdateSerializer},
        responses={200: PublicUserResponseSerializer, 403: OpenApiResponse(description="Not your profile.")},
        description="Met à jour partiellement son propre profil.",
    )
    def patch(self, request, username):
        user = _get_profile(request, username)
        serializer = PublicUserUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return _response("User updated successfully", user, request)

    @extend_schema(
        tags=["Public users"],
        operation_id="delete_public_user",
        responses={200: MessageSerializer, 403: OpenApiResponse(description="Not your profile.")},
        description="Supprime son propre profil et sa photo.",
    )
    def delete(self, request, username):
        user = get_object_or_404(PublicUser, username=username)
        delete_avatar(user)
        user.delete()
        return Response({"message": "User deleted successfully"})


class PublicUserListCreate(APIView):
    @extend_schema(
        tags=["Public users"],
        operation_id="list_public_users",
        responses=PublicUserListResponseSerializer,
        description="La liste des utilisateurs : identifiant et nom seulement.",
    )
    def get(self, request):
        users = PublicUser.objects.order_by("username")
        return Response({"users": PublicUserListSerializer(users, many=True).data})

    @extend_schema(
        tags=["Public users"],
        operation_id="create_public_user",
        request={"multipart/form-data": PublicUserCreateSerializer},
        responses={
            201: PublicUserResponseSerializer,
            400: OpenApiResponse(description="Validation error"),
            409: OpenApiResponse(description="The profile already exists."),
        },
        description="Crée le profil public du compte connecté. Nom et email viennent du jeton.",
    )
    def post(self, request):
        username = getattr(request.user, "username", "")
        email = getattr(request.user, "email", "")
        if not username or not email:
            return Response({"detail": "The token does not identify an account."}, status=status.HTTP_403_FORBIDDEN)
        if PublicUser.objects.filter(username=username).exists():
            return Response({"detail": "The profile already exists."}, status=status.HTTP_409_CONFLICT)
        serializer = PublicUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save(username=username, email=email)
        return _response("User created successfully", user, request, status.HTTP_201_CREATED)


class PublicUserAvatarView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    throttle_scope = "avatar"

    @extend_schema(
        tags=["Public users"],
        operation_id="get_public_user_avatar",
        responses={
            200: PublicUserAvatarResponseSerializer,
            404: OpenApiResponse(description="Unknown user."),
            503: OpenApiResponse(description="Unable to retrieve user avatar right now."),
        },
        description=(
            "Renvoie l'url temporaire de l'image de profil d'un utilisateur public, "
            "ou `avatar_url: null` quand il n'en a pas."
        ),
    )
    def get(self, request, username):
        user = get_object_or_404(PublicUser, username=username)
        if not user.avatar:
            # A missing picture is the normal case, not an error the browser should log.
            return Response({"message": "User has no profile avatar.", "avatar_url": None})
        try:
            url = get_presigned_url(bucket_name=default_storage.bucket_name, object_key=user.avatar, expiration=3600)
        except PresignedUrlError:
            return Response({"message": "Unable to retrieve user avatar right now."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"message": "User avatar retrieved successfully.", "avatar_url": url})

    @extend_schema(
        tags=["Public users"],
        operation_id="update_public_user_avatar",
        request={"multipart/form-data": PublicUserAvatarUpdateSerializer},
        responses={200: MessageSerializer, 403: OpenApiResponse(description="Not your profile.")},
        description="Remplace sa propre photo de profil.",
    )
    def patch(self, request, username):
        serializer = PublicUserAvatarUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = _get_profile(request, username)
        old_key = user.avatar or None
        new_key = save_avatar(user, serializer.validated_data["avatar"])
        if old_key and old_key != new_key:
            default_storage.delete(old_key)
        return Response({"message": "User avatar updated successfully"})

    @extend_schema(
        tags=["Public users"],
        operation_id="delete_public_user_avatar",
        responses={
            200: MessageSerializer,
            403: OpenApiResponse(description="Not your profile."),
            404: OpenApiResponse(description="User has no avatar to delete"),
        },
        description="Supprime sa propre photo de profil.",
    )
    def delete(self, request, username):
        user = get_object_or_404(PublicUser, username=username)
        if not user.avatar:
            return Response({"message": "User has no avatar to delete"}, status=status.HTTP_404_NOT_FOUND)
        delete_avatar(user)
        return Response({"message": "User avatar deleted successfully"})
