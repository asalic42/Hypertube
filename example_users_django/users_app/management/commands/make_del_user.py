from django.core.management.base import BaseCommand
from users_app.models import PublicUser

class Command(BaseCommand):
    help = 'Delete accounts inactive for three years'
    
    def handle(self, *args, **kwargs):
        PublicUser.objects.create(username='deleted_account',
                                  profilePic='/media/default_avatars/deleted.jpg')
