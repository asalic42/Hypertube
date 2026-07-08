from os.path import exists
from django.utils.timezone import now
import requests
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework import status
from rest_framework.views import APIView, Response
from .models import PublicUser
from .serializers import PublicUserDetailSerializer, PublicUserListSerializer
from .permissions import (
    IsAuth,
    IsOwner,
    IsAvatarManager,
    IsMatchmaking,
    IsAuthOrAuthenticated,
)
from .authentification import CustomAuthentication
from ms_client.ms_client import (
    MicroServiceClient,
    RequestsFailed,
    InvalidCredentialsException,
)
from .trad import translate

# Create your views here.


class PublicUserList(generics.ListAPIView):
    permission_classes = [IsAuthOrAuthenticated]
    queryset = PublicUser.objects.all().exclude(username="deleted_account")
    serializer_class = PublicUserListSerializer
    lookup_field = "username"

    def get_queryset(self):
        queryset = super().get_queryset()

        allowed_order_fields = [
            "username",
            "account_creation",
            "single_games_pong_won",
            "single_games_pong_lost",
            "single_games_c4_won",
            "single_games_c4_lost",
            "tournaments_pong_won",
            "tournaments_pong_lost",
            "tournaments_c4_won",
            "tournaments_c4_lost",
            "total_tournaments_pong",
            "total_tournaments_c4",
            "total_single_games_pong",
            "total_single_games_c4",
            "tournament_pong_win_rate",
            "tournament_c4_win_rate",
            "single_games_pong_win_rate",
            "single_games_c4_win_rate",
        ]
        order_by = self.request.query_params.get("order_by")
        if order_by in allowed_order_fields:
            return PublicUser.objects.all().exclude(username='deleted_account').order_by(order_by)
        return queryset


class PublicUserRetrieveDetail(generics.RetrieveAPIView):
    permission_classes = [IsAuthOrAuthenticated]
    queryset = PublicUser.objects.all()
    serializer_class = PublicUserDetailSerializer
    lookup_field = "username"


class PublicUserCreate(generics.CreateAPIView):
    permission_classes = [IsAuth]
    queryset = PublicUser.objects.all()
    serializer_class = PublicUserDetailSerializer


class PublicUserUpdate(APIView):
    permission_classes = [IsAuth]
    queryset = PublicUser.objects.all().exclude(username="deleted_account")

    def patch(self, request, username):
        instance = get_object_or_404(PublicUser, username=username)
        old_username = instance.username
        new_username = request.data.get('username')
        instance.username = new_username
        if instance.profilePic != '/media/default_avatars/default_00.jpg':
            old_path = instance.profilePic
            new_path = new_username.join(old_path.rsplit(old_username, 1))
            instance.profilePic = new_path
        instance.save()
        print(f'{instance.profilePic}')
        return Response({'Ok':'Kr'}, status=status.HTTP_200_OK)


class PublicUserDelete(generics.DestroyAPIView):
    permission_classes = [IsAuth]
    queryset = PublicUser.objects.all().exclude(username="deleted_account")
    serializer_class = PublicUserDetailSerializer
    lookup_field = "username"


class PublicUserIncrement(APIView):
    lookup_field = "username"
    permission_classes = [IsMatchmaking]

    def patch(self, request, username, lookupfield):
        lang = request.headers.get("lang")
        try:
            user = PublicUser.objects.get(username=username)
        except PublicUser.DoesNotExist:
            message = translate(lang, "user_does_not_exist_error")
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)

        allowedFields = {
            "single_games_pong_won": "single_games_pong_won",
            "single_games_pong_lost": "single_games_pong_lost",
            "single_games_c4_won": "single_games_c4_won",
            "single_games_c4_lost": "single_games_c4_lost",
            "tournaments_pong_won": "tournaments_pong_won",
            "tournaments_pong_lost": "tournaments_pong_lost",
            "tournaments_c4_won": "tournaments_c4_won",
            "tournaments_c4_lost": "tournaments_c4_lost",
        }
        if lookupfield not in allowedFields:
            message = translate(lang, "field_not_found_error")
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)

        current_value = getattr(user, lookupfield, None)
        if current_value is None:
            message = translate(lang, "field_not_found_error")
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)

        setattr(user, lookupfield, current_value + 1)
        user.save()

        return Response(
            {lookupfield: getattr(user, lookupfield, None)}, status=status.HTTP_200_OK
        )


class PublicUserAddFriend(APIView):
    lookup_field = "username"
    permission_classes = [IsOwner]

    def patch(self, request, username, friendusername):
        lang = request.headers.get("lang")
        if username == friendusername:
            return Response(status=status.HTTP_304_NOT_MODIFIED)
        if friendusername == "deleted_account":
            message = translate(lang, "user_does_not_exist_error")
            return Response({"Error": message}, status=status.HTTP_409_CONFLICT)
        try:
            user = PublicUser.objects.get(username=username)
        except PublicUser.DoesNotExist:
            message = translate(lang, "user_does_not_exist_error")
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)
        cur_friends = getattr(user, "friends", None)
        try:
            new_friend = PublicUser.objects.get(username=friendusername)
        except PublicUser.DoesNotExist:
            message = translate(lang, "new_friend_not_exist_error")
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)
        if user.friends.filter(username=friendusername).exists():
            message = translate(lang, "already_friend")
            return Response({"error" : message}, status=status.HTTP_409_CONFLICT)
        if cur_friends is None:
            message = translate(lang, "field_not_found_error")
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)
        user.friends.add(new_friend)
        user.save()

        message = translate(lang, "added_friend_success")
        return Response({"OK": message}, status=status.HTTP_200_OK)


class PublicUserListFriends(generics.ListAPIView):
    serializer_class = PublicUserListSerializer
    lookup_field = "username"
    permission_classes = [IsOwner]

    def get_queryset(self):
        username = self.kwargs.get("username")
        user = get_object_or_404(PublicUser, username=username)
        return user.friends.all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class PublicUserRemoveFriend(APIView):
    permission_classes = [IsOwner]
    lookup_field = "username"

    def delete(self, request, username, friendusername):
        lang = request.headers.get("lang")
        if username == friendusername:
            return Response(status=status.HTTP_304_NOT_MODIFIED)
        try:
            user = PublicUser.objects.get(username=username)
        except PublicUser.DoesNotExist:
            message = translate(lang, "user_does_not_exist_error")
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)
        self.check_object_permissions(request, user)
        cur_friends = getattr(user, "friends", None)
        try:
            delete_friend = PublicUser.objects.get(username=friendusername)
        except PublicUser.DoesNotExist:
            message = translate(lang, "new_friend_not_exist_error")
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)
        if not user.friends.filter(username=friendusername).exists():
            return Response(status=status.HTTP_304_NOT_MODIFIED)
        if cur_friends is None:
            message = translate(lang, "field_not_found_error")
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)
        user.friends.remove(delete_friend)
        user.save()

        message = translate(lang, "delete_friend_success")
        return Response({"OK": message}, status=status.HTTP_200_OK)


class PublicUserUpdateAvatar(APIView):
    permission_classes = [IsAvatarManager]
    lookup_field = "username"

    def patch(self, request, username):
        lang = request.headers.get("lang")
        try:
            user = PublicUser.objects.get(username=username)
        except PublicUser.DoesNotExist:
            message = translate(lang, "user_does_not_exist_error")
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)
        path = request.data.get("avatar_path")
        if path is None:
            message = translate(lang, "invalid_body_error")
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)
        user.profilePic = path
        user.save()
        message = translate(lang, "new_avatar_update_success")
        return Response({"OK": message}, status=status.HTTP_200_OK)


class PublicUserSetDefaultAvatar(APIView):
    permission_classes = [IsOwner]
    lookup_field = "username"

    def patch(self, request, username):
        lang = request.headers.get("lang")
        try:
            user = PublicUser.objects.get(username=username)
        except PublicUser.DoesNotExist:
            message = translate(lang, "user_does_not_exist_error")
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)
        self.check_object_permissions(request, user)
        path = "/media/default_avatars/default_00.jpg"
        try:
            sender = MicroServiceClient()
            sender.send_requests(
                urls=[
                    f"http://avatars:8443/api/avatars/",
                ],
                method="delete",
                expected_status=[204, 304],
                body={"username": f"{user.username}"},
            )
        except (RequestsFailed, InvalidCredentialsException):
            message = translate(lang, "update_avatar_error")
            return Response(
                {"error": message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        user.profilePic = path
        user.save()
        message = translate(lang, "reset_avatar_success")
        return Response({"OK": message}, status=status.HTTP_200_OK)


class PublicUserSetLastSeenOnline(APIView):
    lookup_field = "username"
    permission_classes = [IsMatchmaking]

    def patch(self, request, username):
        lang = request.headers.get("lang")
        try:
            user = PublicUser.objects.get(username=username)
        except PublicUser.DoesNotExist:
            message = translate(lang, "user_does_not_exist_error")
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)
        user.last_seen_online = now()
        user.save()
        message = translate(lang, "log_time_update_success")
        return Response({"OK": message}, status=status.HTTP_200_OK)
