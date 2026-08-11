from rest_framework import serializers

from users_app.models import PublicUser, profile_picture_upload_to
from users_app.validators import validate_profile_picture_upload

from django.core.files.storage import default_storage


class PublicUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicUser
        fields = [
            "id",
            "username",
            "firstname",
            "lastname",
            "email",
            "profilePic",
            "preferredLanguage",
        ]


class PublicUserCreateSerializer(serializers.ModelSerializer):
    profilePic = serializers.FileField(
        required=False,
        validators=[validate_profile_picture_upload],
        write_only=True
    )

    class Meta:
        model = PublicUser
        fields = [
            "username",
            "firstname",
            "lastname",
            "email",
            "preferredLanguage",
            "profilePic",
        ]

    def create(self, validated_data):
        file = validated_data.pop("profilePic", None)
        user = PublicUser.objects.create(**validated_data)
        if file:
            key = profile_picture_upload_to(user, file.name)
            default_storage.save(key, file) # bucket s3 storage
            user.profilePic = key # save storage key to user model
            user.save(update_fields=["profilePic"])
        return user


class PublicUserCreateResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    user = PublicUserSerializer()


class PublicUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicUser
        fields = [
            "firstname", 
            "lastname", 
            "email", 
            "profilePic", 
            "preferredLanguage"
        ]


class PublicUserAvatarUpdateSerializer(serializers.Serializer):
    profilePic = serializers.ImageField(
        required=True,
        validators=[validate_profile_picture_upload],
    )


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField()


class PublicUserListResponseSerializer(serializers.Serializer):
    users = PublicUserSerializer(many=True)


class PublicUserDetailResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    user = PublicUserSerializer()
