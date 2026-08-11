from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from users_app.models import PublicUser
from users_app.serializers import (
    MessageSerializer,
    PublicUserAvatarUpdateSerializer,
    PublicUserCreateSerializer,
    PublicUserDetailResponseSerializer,
    PublicUserListResponseSerializer,
    PublicUserSerializer,
    PublicUserUpdateSerializer,
    PublicUserCreateResponseSerializer,
    PublicUserPictureResponseSerializer,
)
from django.core.files.storage import default_storage
from users_app.models import get_bucket_file_key
from users_app.utils import get_presigned_url


class PublicUserList(APIView):
    authentication_classes = []
    permission_classes = []
    """ retrieve a list of all users from the database """

    @extend_schema(
        tags=["Public users"],
        operation_id="list_public_users",
        responses=PublicUserListResponseSerializer,
        description="Retourne la liste des utilisateurs publics.",
    )
    def get(self, request):
        users = PublicUser.objects.all()
        return Response(
            {
                "users": PublicUserSerializer(users, many=True).data
            }
        )


class PublicUserCreate(APIView):
    authentication_classes = []
    permission_classes = []
    """ create a new user in the database """

    @extend_schema(
        tags=["Public users"],
        operation_id="create_public_user",
        request={"multipart/form-data": PublicUserCreateSerializer},
        responses={
            201: PublicUserCreateResponseSerializer,
            400: OpenApiResponse(
                response=PublicUserSerializer,
                description="Invalid user data",
            ),},
        description="Crée un utilisateur public a partir d'un payload JSON.",
    )
    def post(self, request):
        serializer = PublicUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "message": "User created successfully", 
                "user": PublicUserSerializer(serializer.instance).data
            }, 
            status=201
        )


class PublicUserRetrieveDetail(APIView):
    authentication_classes = []
    permission_classes = []
    """ retrieve a specific user from the database """

    @extend_schema(
        tags=["Public users"],
        operation_id="retrieve_public_user",
        responses=PublicUserDetailResponseSerializer,
        description="Retourne le detail d'un utilisateur public via son username.",
    )
    def get(self, request, username):
        user = get_object_or_404(PublicUser, username=username)
        return Response(
            {
                "message": "User retrieved successfully",
                "user": PublicUserSerializer(user).data,
            }
        )


class PublicUserRetrievePic(APIView):
    authentication_classes = []
    permission_classes = []
    """ retrieve a specific user's profile picture from the file database """

    @extend_schema(
        tags=["Public users"],
        operation_id="retrieve_public_user_pic",
        responses=PublicUserPictureResponseSerializer,
        description="Renvoie l'url temporaire de l'image de profil d'un utilisateur public.",
    )
    def get(self, request, username):
        try:
            url = get_presigned_url(
                bucket_name=default_storage.bucket_name,
                object_key=get_bucket_file_key(username),
                expiration=3600
            )
            response_serializer = PublicUserPictureResponseSerializer(
                data={
                    "message": "User picture retrieved successfully.",
                    "picture_url": url,
                }
            )
            response_serializer.is_valid(raise_exception=True)
            return Response(response_serializer.validated_data)
        except Exception as e:
            return Response(
                {
                    "message": "Error retrieving user picture.",
                },
                status=500
            )


class PublicUserUpdate(APIView):
    authentication_classes = []
    permission_classes = []
    """ update a specific user in the database """

    @extend_schema(
        tags=["Public users"],
        operation_id="update_public_user",
        request=PublicUserUpdateSerializer,
        responses=MessageSerializer,
        description="Met a jour partiellement un utilisateur public.",
    )
    def patch(self, request, username):
        user = get_object_or_404(PublicUser, username=username)
        serializer = PublicUserUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "User updated successfully"})


class PublicUserUpdateAvatar(APIView):
    authentication_classes = []
    permission_classes = []
    """ update a specific user's avatar in the database """

    @extend_schema(
        tags=["Public users"],
        operation_id="update_public_user_avatar",
        request=PublicUserAvatarUpdateSerializer,
        responses=MessageSerializer,
        description="Met a jour uniquement l'avatar (profilePic).",
    )
    def patch(self, request, username):
        user = get_object_or_404(PublicUser, username=username)
        serializer = PublicUserAvatarUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.profilePic = serializer.validated_data["profilePic"]
        user.save()
        return Response({"message": "User avatar updated successfully"})


class PublicUserDelete(APIView):
    authentication_classes = []
    permission_classes = []
    """ delete a specific user from the database """

    @extend_schema(
        tags=["Public users"],
        operation_id="delete_public_user",
        responses=MessageSerializer,
        description="Supprime un utilisateur public via son username.",
    )
    def delete(self, request, username):
        user = get_object_or_404(PublicUser, username=username)
        user.delete()
        return Response({"message": "User deleted successfully"})
