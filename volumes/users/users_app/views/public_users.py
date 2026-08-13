import logging

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from users_app.models import PublicUser
from users_app.serializers import (
    MessageSerializer,
    PublicUserAvatarUpdateSerializer,
    PublicUserCreateSerializer,
    PublicUserListResponseSerializer,
    PublicUserSerializer,
    PublicUserUpdateSerializer,
    PublicUserResponseSerializer,
    PublicUserAvatarResponseSerializer,
)
from rest_framework import serializers
from django.core.files.storage import default_storage
from users_app.services.avatars import (
    PresignedUrlError,
    get_bucket_file_key,
    create_avatar_key,
    save_avatar,
    delete_avatar,
    get_presigned_url,
)
from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView
)

class PublicUserView(APIView):
    authentication_classes = []
    permission_classes = []
    
    # GET
    @extend_schema(
        tags=["Public users"],
        operation_id="get_public_user",
        responses=PublicUserResponseSerializer,
        description="Retourne le detail d'un utilisateur public via son username.",
    )
    def get(self, request, username):
        user = get_object_or_404(PublicUser, id=user_id)
        response_serializer = PublicUserResponseSerializer(
            instance={
                "message": "User retrieved successfully",
                "user": PublicUserSerializer(user).data,
            }
        )
        return Response(response_serializer.data)

    # PATCH
    @extend_schema(
        tags=["Public users"],
        operation_id="update_public_user",
        request={"multipart/form-data": PublicUserUpdateSerializer},
        responses=PublicUserResponseSerializer,
        description="Met a jour partiellement un utilisateur public.",
    )
    def patch(self, request, username):
        user = get_object_or_404(PublicUser, id=user_id)
        serializer = PublicUserUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        response_serializer = PublicUserResponseSerializer(
            instance={
                "message": "User updated successfully",
                "user": PublicUserSerializer(user).data,
            }
        )
        return Response(response_serializer.data)

    # DELETE
    @extend_schema(
        tags=["Public users"],
        operation_id="delete_public_user",
        responses={
            200: MessageSerializer,
            404: OpenApiResponse(
                description="User not found",
            ),
        },
        description="Supprime un utilisateur public via son username.",
    )
    def delete(self, request, username):
        user = get_object_or_404(PublicUser, id=user_id)
        delete_avatar(user)
        user.delete()
        return Response({"message": "User deleted successfully"})


class PublicUserListView(ListAPIView):
    queryset = PublicUser.objects.all()
    serializer_class = PublicUserSerializer
    authentication_classes = []
    permission_classes = []

    # # GET
    # @extend_schema(
    #     tags=["Public users"],
    #     operation_id="list_public_users",
    #     responses=PublicUserListResponseSerializer,
    #     description="Retourne la liste des utilisateurs publics.",
    # )
    # def get(self, request):
    #     users = PublicUser.objects.all()
    #     return Response(
    #         {
    #             "users": PublicUserSerializer(users, many=True).data
    #         }
    #     )

    # # POST
    # @extend_schema(
    #     tags=["Public users"],
    #     operation_id="create_public_user",
    #     request={"multipart/form-data": PublicUserCreateSerializer},
    #     responses={
    #         201: PublicUserResponseSerializer,
    #         400: OpenApiResponse(description="Validation error")
    #     },
    #     description="Crée un utilisateur public a partir d'un payload JSON.",
    # )
    # def post(self, request):
    #     serializer = PublicUserCreateSerializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #     serializer.save()
    #     response_serializer = PublicUserResponseSerializer(
    #         instance={
    #             "message": "User created successfully",
    #             "user": PublicUserSerializer(serializer.instance).data
    #         }
    #     )
    #     return Response(response_serializer.data, status=201)


class PublicUserAvatarView(APIView):
    authentication_classes = []
    permission_classes = []
    
    # GET
    @extend_schema(
        tags=["Public users"],
        operation_id="get_public_user_avatar",
        responses={
            200: PublicUserAvatarResponseSerializer, 
            404: OpenApiResponse(description="User has no profile avatar."),
            503: OpenApiResponse(description="Unable to retrieve user avatar right now."),
        },
        description="Renvoie l'url temporaire de l'image de profil d'un utilisateur public.",
    )
    def get(self, request, user_id):
        key = get_bucket_file_key(user_id)
        if key:
            try:
                url = get_presigned_url(
                    bucket_name=default_storage.bucket_name,
                    object_key=key,
                    expiration=3600
                )
            except PresignedUrlError:
                return Response(
                    {"message": "Unable to retrieve user avatar right now."},
                    status=503,
                )
            response_serializer = PublicUserAvatarResponseSerializer(
                data={
                    "message": "User avatar retrieved successfully.",
                    "avatar_url": url,
                }
            )
            response_serializer.is_valid(raise_exception=True)
            return Response(response_serializer.validated_data)
        return Response({"message": "User has no profile avatar."}, status=404)

    # PATCH
    @extend_schema(
        tags=["Public users"],
        operation_id="update_public_user_avatar",
        request={"multipart/form-data": PublicUserAvatarUpdateSerializer},
        responses=MessageSerializer,
        description="Met a jour l'avatar.",
    )
    def patch(self, request, user_id):
        serializer = PublicUserAvatarUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_object_or_404(PublicUser, id=user_id)
        file = serializer.validated_data["avatar"]

        old_key = user.avatar if user.avatar else None
        new_key = save_avatar(user, file)

        if old_key and old_key != new_key:
            default_storage.delete(old_key)

        return Response(
            {
                "message": "User avatar updated successfully"
            }
        )

    # DELETE
    @extend_schema(
        tags=["Public users"],
        operation_id="delete_public_user_avatar",
        responses={
            200: MessageSerializer,
            404: OpenApiResponse(description="User has no avatar to delete"),
        },
        description="Supprime l'avatar.",
    )
    def delete(self, request, user_id):
        user = get_object_or_404(PublicUser, id=user_id)
        if user.avatar:
            delete_avatar(user)
            return Response({"message": "User avatar deleted successfully"})
        else:
            return Response({"message": "User has no avatar to delete"}, status=404)
