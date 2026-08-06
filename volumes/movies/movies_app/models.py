from django.db import models

class Movie(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    release_date = models.DateField()
    director = models.CharField(max_length=255)
    genre = models.CharField(max_length=100)
    rating = models.FloatField()

    def __str__(self):
        return self.title