from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class UsernameBackend(ModelBackend):
    """
    Logs users in with their username. The model's natural key is the email
    (it is unique and used for password resets), so the default backend would
    look the login up in the wrong column.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        try:
            user = User.objects.get(username__iexact=username.strip())
        except User.DoesNotExist:
            # Same cost as a real check, so a missing username is not faster to probe.
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
