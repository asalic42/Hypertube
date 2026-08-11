import uuid
from django.db import models
from django.core.files.storage import default_storage
from users_app.validators import validate_avatar_upload


def profile_avatar_upload_to(instance, filename):
    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'png'
    return f"avatars/{uuid.uuid4().hex[:8]}-avatar.{extension}"


class PublicUser(models.Model):
    username = models.CharField(max_length=128, unique=True)
    firstname = models.CharField(max_length=128, blank=True)
    lastname = models.CharField(max_length=128, blank=True)
    email = models.EmailField(unique=True)
    avatar = models.CharField(max_length=256, blank=True, default="")
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
    return user.avatar if user.avatar else None


def save_avatar(user, file):
    """ saves the profile avatar to the storage and updates the user model 
        :param user: PublicUser instance
        :param file: file object to be saved
        :return: the storage key of the saved file
    """
    key = profile_avatar_upload_to(user, file.name)
    default_storage.save(key, file)
    try:
        user.avatar = key
        user.save(update_fields=["avatar"])
    except Exception:
        default_storage.delete(key)
        raise
    return key
