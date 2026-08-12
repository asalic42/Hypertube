from rest_framework import serializers

from users_app.models import PublicUser
from users_app.services.avatars import save_avatar
from users_app.validators import validate_avatar_upload


class AvatarImageField(serializers.ImageField):
    def __init__(self, **kwargs):
        kwargs.setdefault("write_only", True)
        kwargs.setdefault("validators", [validate_avatar_upload])
        super().__init__(**kwargs)


class PublicUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicUser
        fields = [
            "id",
            "username",
            "firstname",
            "lastname",
            "email",
            "avatar",
            "preferredLanguage",
        ]


class PublicUserCreateSerializer(serializers.ModelSerializer):
    avatar = AvatarImageField(required=False)

    class Meta:
        model = PublicUser
        fields = [
            "username",
            "firstname",
            "lastname",
            "email",
            "preferredLanguage",
            "avatar",
        ]

    def create(self, validated_data):
        file = validated_data.pop("avatar", None)
        user = PublicUser.objects.create(**validated_data)
        if file:
            save_avatar(user, file)
        return user


class PublicUserResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    user = PublicUserSerializer()


class PublicUserAvatarResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    avatar_url = serializers.URLField()


class PublicUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicUser
        fields = [
            "firstname", 
            "lastname", 
            "preferredLanguage"
        ]


class PublicUserAvatarUpdateSerializer(serializers.Serializer):
    avatar = AvatarImageField(required=True)


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField()


class PublicUserListResponseSerializer(serializers.Serializer):
    users = PublicUserSerializer(many=True)


class PublicUserDetailResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    user = PublicUserSerializer()
