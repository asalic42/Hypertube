import uuid

from django.db import models

from users_app.validators import validate_profile_picture_upload


def profile_picture_upload_to(instance, filename):
    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'png'
    return f"profile_pics/{uuid.uuid4().hex[:8]}-avatar.{extension}"


class PublicUser(models.Model):
    username = models.CharField(max_length=128, unique=True)
    firstname = models.CharField(max_length=128, blank=True)
    lastname = models.CharField(max_length=128, blank=True)
    email = models.EmailField(unique=True)
    profilePic = models.ImageField(
        upload_to=profile_picture_upload_to,
        blank=True,
        null=True,
        validators=[validate_profile_picture_upload],
    )
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('fr', 'French'),
        ('es', 'Spanish'),
        ('de', 'German'),
        ('it', 'Italian'),
        ('pt', 'Portuguese'),
        ('ru', 'Russian'),
        ('zh', 'Chinese'),
        ('ja', 'Japanese'),
        ('ko', 'Korean'),
    ]
    preferredLanguage = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='en')
