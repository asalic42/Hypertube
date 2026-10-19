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
            "username",
            "firstname",
            "lastname",
            "email",
            "avatar",
            "preferredLanguage",
        ]


class PublicUserListSerializer(serializers.ModelSerializer):
    """What the user list exposes: enough to find and name someone, nothing private."""

    class Meta:
        model = PublicUser
        fields = ["id", "username"]


class NameField(serializers.CharField):
    """A first or last name: required, not blank, surrounding spaces removed."""

    def __init__(self, **kwargs):
        kwargs.setdefault("max_length", 128)
        kwargs.setdefault("allow_blank", False)
        super().__init__(**kwargs)


class PublicUserCreateSerializer(serializers.ModelSerializer):
    """The caller's own profile: username and email come from the token, not the body."""

    firstname = NameField()
    lastname = NameField()
    avatar = AvatarImageField(required=False)

    class Meta:
        model = PublicUser
        fields = [
            "firstname",
            "lastname",
            "preferredLanguage",
            "avatar",
        ]

    def create(self, validated_data):
        file = validated_data.pop("avatar", None)
        user = PublicUser.objects.create(**validated_data)
        if file:
            try:
                save_avatar(user, file)
            except Exception:
                user.delete()
                raise AvatarSaveError()
        return user


class PublicUserResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    user = PublicUserSerializer()


class PublicUserAvatarResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    # Null when the user has no picture.
    avatar_url = serializers.URLField(allow_null=True)


class PublicUserUpdateSerializer(serializers.ModelSerializer):
    # Optional on a partial update, but a name can never be emptied.
    firstname = NameField(required=False)
    lastname = NameField(required=False)

    class Meta:
        model = PublicUser
        fields = [
            "firstname", 
            "lastname", 
            "email",
            "preferredLanguage"
        ]

    def validate(self, attrs):
        # With form data, DRF reads an empty optional field as "not sent".
        # An explicit empty name is a request to erase it, which is refused.
        for name in ("firstname", "lastname"):
            if name in self.initial_data and not str(self.initial_data.get(name) or "").strip():
                raise serializers.ValidationError({name: "This field may not be blank."})
        return attrs


class PublicUserAvatarUpdateSerializer(serializers.Serializer):
    avatar = AvatarImageField(required=True)


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField()


class PublicUserListResponseSerializer(serializers.Serializer):
    users = PublicUserListSerializer(many=True)


class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()
    service = serializers.CharField()
