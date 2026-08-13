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

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]
    EMAIL_FIELD = "email"

    class Meta:
        db_table = "auth"
        ordering = ("-date_joined",)

    def __str__(self) -> str:
        return self.username
