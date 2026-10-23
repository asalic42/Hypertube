from django.db import models


class PublicUser(models.Model):
    # The account id the auth service put in the token: the same person has
    # the same id in every service, so the API addresses profiles by it.
    id = models.UUIDField(primary_key=True, editable=False)
    username = models.CharField(max_length=128, unique=True)
    # Blank only for profiles created from a token before the user filled them in.
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

