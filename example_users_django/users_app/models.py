from django.db import models

# Create your models here.

class PublicUser(models.Model):
    username = models.CharField(max_length=128, unique=True)
    profilePic = models.URLField(default='/media/default_avatars/default_00.jpg')
    account_creation = models.DateTimeField(auto_now_add=True)
    last_seen_online = models.DateTimeField(null=True)
    friends = models.ManyToManyField('self', symmetrical=False, blank=True)
    single_games_pong_won = models.IntegerField(default=0)
    single_games_pong_lost = models.IntegerField(default=0)
    single_games_c4_won = models.IntegerField(default=0)
    single_games_c4_lost = models.IntegerField(default=0)
    tournaments_pong_won = models.IntegerField(default=0)
    tournaments_pong_lost = models.IntegerField(default=0)
    tournaments_c4_won = models.IntegerField(default=0)
    tournaments_c4_lost = models.IntegerField(default=0)

    @property
    def is_authenticated(self):
        return True
