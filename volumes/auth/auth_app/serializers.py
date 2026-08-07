from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        field = (
            "id",
            "username",
            "email",
            "date_joined",
        )
        read_only_fields = fields
    

class RegisterSerializer(serializers.ModelSerializer):
    password = serializer.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    password_confirmation = serializer.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "password",
            "password_confirmation",
        )
        read_only_fields = (
            "id",
        )

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "This username already exists"
            )
        return value.strip()

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "This email already has an account"
            )
        return value.strip().lower()


    def validate(self, attributes):
        password = attributes.get("password")
        password_confirmation = attributes.pop(
            "password_confirmation"
            , None,
        )

        if password != password_confirmation:
            raise serializers.ValidationError (
                {
                    "password_condifrmation":
                        "Passwords do not match."
                }
            )
        
        candidate_user = User(
            email=attributes.get("email"),
            username=attributes.get("username"),
        )

        validate_password(
            password,
            user=candidate_user,
        )

        return attributes
    
    @transaction.atomic
    def create(self, validated_data):
        return User.objects.create_user(
            **validated_data,
        )


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        return token

    def validate(self, attributes):
        data = super().validate(attributes)
        data["user"] = UserSerializer(self.user).data
        return data

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.Charfield()

class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()
    service = serializers.CharField()