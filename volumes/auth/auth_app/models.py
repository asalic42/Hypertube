import uuid

from django.contrib.auth.models import AbstractBaseUser
from django.db import models
from django.utils import timezone

from .managers import UserManager


# TO DO : THINK ABOUT ADMIN FIELD FOR USER MODEL IF WE 
# KEEP THE DJANGO ADMIN VIEW AVAILABLE FROM THE FRONTEND

class User(AbstractBaseUser):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    username = models.CharField(
        max_length=30,
        unique=True,
    )

    email = models.EmailField(
        unique=True,
    )

    date_joined = models.DateTimeField(
        default=timezone.now,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]
    EMAIL_FIELD = "email"

    class Meta:
        db_table = "auth"
        ordering = ("-date_joined",)

    def __str__(self) -> str:
        return self.username


class OAuthAccount(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="oauth_accounts",
    )

    provider = models.CharField(
        max_length=32,
    )

    provider_user_id = models.CharField(
        max_length=255,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "oauth_account"
        constraints = [
            models.UniqueConstraint(
                fields=("provider", "provider_user_id"),
                name="uniq_provider_account",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.provider_user_id}"


class ApiClient(models.Model):
    """
    Credentials a user issues to a program so it can call the API in their
    name: the client id and a secret, shown once and stored hashed. The
    OAuth2 token endpoint turns them into an access token for that user.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="api_clients",
    )

    name = models.CharField(
        max_length=64,
    )

    secret_hash = models.CharField(
        max_length=128,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "api_client"
        ordering = ("created_at",)

    def __str__(self) -> str:
        return f"{self.name} ({self.user.username})"
