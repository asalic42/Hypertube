from django.db import migrations, models


class Migration(migrations.Migration):
    """
    The profile id becomes the account id issued by the auth service, which the
    token carries. The old serial ids cannot be mapped to accounts from here,
    so the table is recreated: a profile is made again from the token the next
    time its owner shows up.
    """

    dependencies = [
        ("users_app", "0001_initial"),
    ]

    operations = [
        migrations.DeleteModel(name="PublicUser"),
        migrations.CreateModel(
            name="PublicUser",
            fields=[
                ("id", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ("username", models.CharField(max_length=128, unique=True)),
                ("firstname", models.CharField(blank=True, max_length=128)),
                ("lastname", models.CharField(blank=True, max_length=128)),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("avatar", models.CharField(blank=True, default="", max_length=256)),
                (
                    "preferredLanguage",
                    models.CharField(
                        choices=[
                            ("en", "English"), ("fr", "French"), ("es", "Spanish"), ("de", "German"), ("it", "Italian"),
                            ("pt", "Portuguese"), ("ru", "Russian"), ("zh", "Chinese"), ("ja", "Japanese"), ("ko", "Korean"),
                        ],
                        default="en",
                        max_length=2,
                    ),
                ),
            ],
        ),
    ]
