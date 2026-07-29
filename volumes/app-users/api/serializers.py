from rest_framework import serializers

from api.models import PublicUser


class PublicUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicUser
        fields = [
            "username",
            "firstname",
            "lastname",
            "email",
            "profilePic",
            "preferredLanguage",
        ]


class PublicUserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicUser
        fields = [
            "username",
            "firstname",
            "lastname",
            "email",
            "profilePic",
            "preferredLanguage",
        ]


class PublicUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicUser
        fields = ["firstname", "lastname", "email", "profilePic", "preferredLanguage"]


class PublicUserAvatarUpdateSerializer(serializers.Serializer):
    profilePic = serializers.URLField(required=True)


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField()


class PublicUserListResponseSerializer(serializers.Serializer):
    users = PublicUserSerializer(many=True)


class PublicUserDetailResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    user = PublicUserSerializer()
