from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("movies_app", "0006_download_video_profile"),
    ]

    operations = [
        migrations.AddField(
            model_name="subtitle",
            name="aligned",
            field=models.BooleanField(default=False),
        ),
    ]
