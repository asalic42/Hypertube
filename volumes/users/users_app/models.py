from django.db import models

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

class PublicUser(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    firstname = models.CharField(max_length=128, blank=True)
    lastname = models.CharField(max_length=128, blank=True)
    avatar = models.CharField(max_length=256, blank=True, default="")
    preferredLanguage = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='en')

