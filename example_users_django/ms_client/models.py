from django.db import models

# Create your models here.

class Token(models.Model):
    serviceName = models.CharField(max_length=255)
    token = models.TextField()
