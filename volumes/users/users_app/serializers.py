from rest_framework import serializers
from rest_framework.exceptions import APIException

from users_app.models import PublicUser
from users_app.services.avatars import save_avatar
from users_app.validators import validate_avatar_upload


class AvatarImageField(serializers.ImageField):
    def __init__(self, **kwargs):
        kwargs.setdefault("write_only", True)
        kwargs.setdefault("validators", [validate_avatar_upload])
        super().__init__(**kwargs)


class AvatarSaveError(APIException):
    status_code = 500
    default_detail = {"avatar": "Failed to save avatar."}
    default_code = "avatar_save_error"


class PublicUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicUser
        fields = [
            "id",
            "firstname",
            "lastname",
            "avatar",
            "preferredLanguage",
        ]


class PublicUserCreateSerializer(serializers.ModelSerializer):
    avatar = AvatarImageField(required=False)

    class Meta:
        model = PublicUser
        fields = [
            "firstname",
            "lastname",
            "preferredLanguage",
        ]


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


class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()
    service = serializers.CharField()
