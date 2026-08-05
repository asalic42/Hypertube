from django.db import models

from api.validators import validate_profile_picture_upload


class PublicUser(models.Model):
    username = models.CharField(max_length=128, unique=True)
    firstname = models.CharField(max_length=128, blank=True)
    lastname = models.CharField(max_length=128, blank=True)
    email = models.EmailField(unique=True)
    profilePic = models.ImageField(
        upload_to='profile_pics/',
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
