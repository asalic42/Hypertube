from typing import Any

from django.contrib.auth.base_user import BaseUserManager


def normalize_email(value: str) -> str:
    """The form an email is stored and compared in: trimmed, lower case."""
    return (value or "").strip().lower()


class UserManager(BaseUserManager):
    use_in_migrations = True

    def get_by_natural_key(self, username):
        # The login: a username typed with capitals is the same account.
        return self.get(username__iexact=(username or "").strip())

    def create_user(
        self,
        email: str,
        username: str,
        password: str | None = None,
        **extra_fields: Any,
    ):
        if not email:
            raise ValueError("Email is required.")

        if not username:
            raise ValueError("Username is required.")

        email = normalize_email(email)
        username = username.strip()

        user = self.model(
            email=email,
            username=username,
            **extra_fields,
        )

        user.set_password(password)
        user.save(using=self._db)

        return user