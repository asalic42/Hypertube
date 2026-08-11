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
    profilePic = models.CharField(max_length=256, blank=True, default="")
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


def get_bucket_file_key(username):
    """ returns the s3 bucket file key for a given username """
    user = PublicUser.objects.get(username=username)
    return user.profilePic