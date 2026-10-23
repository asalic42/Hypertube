from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from auth_app.managers import normalize_email
from auth_app.models import ApiClient
from auth_app.validators import validate_username

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "date_joined",
        )
        read_only_fields = fields
    

class UserUpdateSerializer(serializers.ModelSerializer):
    """What a user may change on their own account: the email, which is the login."""

    class Meta:
        model = User
        fields = ("email",)

    def validate_email(self, value):
        value = normalize_email(value)
        if User.objects.filter(email__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("This email already has an account")
        return value


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    password_confirmation = serializers.CharField(
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
        try:
            value = validate_username(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages[0])
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(
                "This username already exists"
            )
        return value

    def validate_email(self, value):
        value = normalize_email(value)
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "This email already has an account"
            )
        return value


    def validate(self, attributes):
        password = attributes.get("password")
        password_confirmation = attributes.pop(
            "password_confirmation"
            , None,
        )

        if password != password_confirmation:
            raise serializers.ValidationError (
                {
                    "password_confirmation":
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
        # The other services identify the caller from these two claims.
        token["username"] = user.username
        token["email"] = user.email
        return token

    def validate(self, attributes):
        data = super().validate(attributes)
        data["user"] = UserSerializer(self.user).data
        return data


class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()
    service = serializers.CharField()


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True)


class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    confirm_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate(self, attributes):
        new_password = attributes.get("new_password")
        confirm_password = attributes.pop(
            "confirm_password",
            None,
        )

        if new_password != confirm_password:
            raise serializers.ValidationError(
                {
                    "confirm_password":
                        "Passwords do not match."
                }
            )

        validate_password(
            new_password,
            user=self.context.get("user"),
        )

        return attributes


class OAuthTokenRequestSerializer(serializers.Serializer):
    """
    A token request as RFC 6749 shapes it, form-encoded or JSON. The client
    credentials may also come in an HTTP Basic Authorization header.
    """

    grant_type = serializers.ChoiceField(choices=("client_credentials", "password"))
    # A string, not a UUIDField: a malformed id is refused as an unknown client, not as a bad request.
    client_id = serializers.CharField(required=False, max_length=64)
    client_secret = serializers.CharField(required=False, trim_whitespace=False)
    username = serializers.CharField(required=False)
    password = serializers.CharField(required=False, trim_whitespace=False)


class OAuthTokenResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    token_type = serializers.CharField(default="Bearer")
    expires_in = serializers.IntegerField(help_text="Seconds before the token expires.")


class OAuthErrorSerializer(serializers.Serializer):
    error = serializers.ChoiceField(
        choices=("invalid_request", "invalid_client", "invalid_grant", "unsupported_grant_type"),
    )
    error_description = serializers.CharField()


class ApiClientSerializer(serializers.ModelSerializer):
    client_id = serializers.UUIDField(source="id", read_only=True)

    class Meta:
        model = ApiClient
        fields = ("client_id", "name", "created_at", "last_used_at")
        read_only_fields = fields


class ApiClientCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiClient
        fields = ("name",)

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value


class ApiClientCreatedSerializer(ApiClientSerializer):
    """The one answer that carries the secret: it is not stored and cannot be shown again."""

    client_secret = serializers.CharField(read_only=True)

    class Meta(ApiClientSerializer.Meta):
        fields = (*ApiClientSerializer.Meta.fields, "client_secret")
        read_only_fields = fields
