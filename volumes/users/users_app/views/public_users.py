import logging

from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users_app.models import PublicUser
from users_app.permissions import IsOwnerOrReadOnly, caller_id, is_owner
from users_app.serializers import (
    CREDENTIAL_FIELDS,
    MessageSerializer,
    PublicUserAvatarResponseSerializer,
    PublicUserAvatarUpdateSerializer,
    PublicUserCreateSerializer,
    PublicUserListResponseSerializer,
    PublicUserListSerializer,
    PublicUserResponseSerializer,
    PublicUserSerializer,
    PublicUserUpdatedSerializer,
    PublicUserUpdateSerializer,
)
from users_app.services import account
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
    if not is_owner(request, user.pk):
        data.pop("email", None)
    return data


def _response(message, user, request, status_code=status.HTTP_200_OK):
    return Response({"message": message, "user": _profile(user, request)}, status=status_code)


def _get_profile(request, user_id):
    """
    The profile at `user_id`. The owner's own profile is created from the
    token when it does not exist yet, so an account always has one.
    """
    username = getattr(request.user, "username", "")
    email = getattr(request.user, "email", "")
    if is_owner(request, user_id) and username and email:
        _forget_stale_profiles(user_id, username, email)
        user, created = PublicUser.objects.get_or_create(pk=caller_id(request), defaults={"username": username, "email": email})
        if not created and user.email != email:
            _sync_email(user, email)
        return user
    return get_object_or_404(PublicUser, pk=user_id)


def _forget_stale_profiles(user_id, username, email):
    """
    The auth service keeps usernames and emails unique among live accounts.
    A profile holding this username under another id was left by a deleted
    account whose clean-up failed: it goes, picture included. A profile holding
    this email may still be live with a copy that is out of date, so it only
    loses the address, which its owner's next visit sets right.
    """
    for stale in PublicUser.objects.filter(username=username).exclude(pk=user_id):
        logger.warning("profile %s (%s) was left by a deleted account: removed", stale.pk, stale.username)
        delete_avatar(stale)
        stale.delete()
    for holder in PublicUser.objects.filter(email=email).exclude(pk=user_id):
        logger.warning("profile %s (%s) held %s, which now belongs to %s: released", holder.pk, holder.username, email, user_id)
        PublicUser.objects.filter(pk=holder.pk).update(email=f"{holder.pk}@unknown.invalid")


def _sync_email(user, email):
    """The auth service owns the email and puts it in the token: the copy kept here follows it."""
    PublicUser.objects.filter(pk=user.pk).update(email=email)
    user.email = email


class PublicUserView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    @extend_schema(
        tags=["Public users"],
        operation_id="get_public_user",
        responses={200: PublicUserResponseSerializer, 404: OpenApiResponse(description="Unknown user.")},
        description="Le profil public d'un utilisateur. L'email n'est renvoyé qu'à son propriétaire.",
    )
    def get(self, request, id):
        return _response("User retrieved successfully", _get_profile(request, id), request)

    @extend_schema(
        tags=["Public users"],
        operation_id="update_public_user",
        request={"multipart/form-data": PublicUserUpdateSerializer, "application/json": PublicUserUpdateSerializer},
        responses={
            200: PublicUserUpdatedSerializer,
            400: OpenApiResponse(description="Validation error, from this service or from the auth service."),
            401: OpenApiResponse(description="The auth service did not accept the token."),
            403: OpenApiResponse(description="Not your profile."),
            503: OpenApiResponse(description="The auth service is unavailable: nothing was changed."),
        },
        description=(
            "Met à jour son propre profil en un appel : prénom, nom, langue, photo (`avatar`, fichier), "
            "email et mot de passe (`password` avec `current_password`). L'email et le mot de passe sont "
            "relayés au service auth, qui les possède ; la réponse porte alors un nouveau jeton d'accès "
            "dans `access`. Le username ne peut pas changer."
        ),
    )
    def patch(self, request, id):
        user = _get_profile(request, id)
        serializer = PublicUserUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        fields = serializer.validated_data
        credentials = {name: fields.pop(name) for name in CREDENTIAL_FIELDS if name in fields}
        picture = fields.pop("avatar", None)

        access = None
        if credentials:
            # The auth service decides: nothing is stored here until it has agreed.
            try:
                answer = account.update_credentials(credentials, request.META.get("HTTP_AUTHORIZATION", ""))
            except account.CredentialsRejected as refusal:
                return Response(refusal.body, status=refusal.status_code)
            except account.AuthUnavailable:
                return Response(
                    {"detail": "The account service is unavailable right now: nothing was changed."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            access = answer.get("access")
            email = answer.get("user", {}).get("email")
            if email and email != user.email:
                _forget_stale_profiles(user.pk, user.username, email)
                _sync_email(user, email)

        serializer.save()
        if picture is not None:
            old_key = user.avatar or None
            new_key = save_avatar(user, picture)
            if old_key and old_key != new_key:
                default_storage.delete(old_key)

        body = {"message": "User updated successfully", "user": _profile(user, request)}
        if access:
            body["access"] = access
        return Response(body)

    @extend_schema(
        tags=["Public users"],
        operation_id="delete_public_user",
        responses={200: MessageSerializer, 403: OpenApiResponse(description="Not your profile.")},
        description="Supprime son propre profil et sa photo.",
    )
    def delete(self, request, id):
        user = get_object_or_404(PublicUser, pk=id)
        delete_avatar(user)
        user.delete()
        return Response({"message": "User deleted successfully"})


class PublicUserListCreate(APIView):
    @extend_schema(
        tags=["Public users"],
        operation_id="list_public_users",
        responses=PublicUserListResponseSerializer,
        description="La liste des utilisateurs : identifiant (celui du compte) et nom seulement.",
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
        description="Crée le profil public du compte connecté. Id, nom et email viennent du jeton.",
    )
    def post(self, request):
        user_id = caller_id(request)
        username = getattr(request.user, "username", "")
        email = getattr(request.user, "email", "")
        if not user_id or not username or not email:
            return Response({"detail": "The token does not identify an account."}, status=status.HTTP_403_FORBIDDEN)
        if PublicUser.objects.filter(pk=user_id).exists():
            return Response({"detail": "The profile already exists."}, status=status.HTTP_409_CONFLICT)
        serializer = PublicUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _forget_stale_profiles(user_id, username, email)
        user = serializer.save(id=user_id, username=username, email=email)
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
    def get(self, request, id):
        user = get_object_or_404(PublicUser, pk=id)
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
    def patch(self, request, id):
        serializer = PublicUserAvatarUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = _get_profile(request, id)
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
    def delete(self, request, id):
        user = get_object_or_404(PublicUser, pk=id)
        if not user.avatar:
            return Response({"message": "User has no avatar to delete"}, status=status.HTTP_404_NOT_FOUND)
        delete_avatar(user)
        return Response({"message": "User avatar deleted successfully"})
