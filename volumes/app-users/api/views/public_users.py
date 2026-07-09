from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView
from api.models import PublicUser
from api.serializers import (
    MessageSerializer,
    PublicUserAvatarUpdateSerializer,
    PublicUserCreateSerializer,
    PublicUserDetailResponseSerializer,
    PublicUserListResponseSerializer,
    PublicUserSerializer,
    PublicUserUpdateSerializer,
)

class PublicUserList(APIView):
    authentication_classes = []
    permission_classes = []
    """ retrieve a list of all users from the database """

    @extend_schema(
        tags=["Public users"],
        responses=PublicUserListResponseSerializer,
        description="Retourne la liste des utilisateurs publics.",
    )
    def get(self, request):
        users = PublicUser.objects.all()
        return Response({"users": PublicUserSerializer(users, many=True).data})

class PublicUserCreate(APIView):
    authentication_classes = []
    permission_classes = []
    """ create a new user in the database """

    @extend_schema(
        tags=["Public users"],
        request=PublicUserCreateSerializer,
        responses={201: MessageSerializer},
        description="Cree un utilisateur public a partir d'un payload JSON.",
    )
    def post(self, request):
        serializer = PublicUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "User created successfully"}, status=201)

class PublicUserRetrieveDetail(APIView):
    authentication_classes = []
    permission_classes = []
    """ retrieve a specific user from the database """

    @extend_schema(
        tags=["Public users"],
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

class PublicUserUpdate(APIView):
    authentication_classes = []
    permission_classes = []
    """ update a specific user in the database """

    @extend_schema(
        tags=["Public users"],
        request=PublicUserUpdateSerializer,
        responses=MessageSerializer,
        description="Met a jour partiellement un utilisateur public (PATCH).",
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
        responses=MessageSerializer,
        description="Supprime un utilisateur public via son username.",
    )
    def delete(self, request, username):
        user = get_object_or_404(PublicUser, username=username)
        user.delete()
        return Response({"message": "User deleted successfully"})
