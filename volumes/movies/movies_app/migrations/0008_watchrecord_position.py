from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("movies_app", "0007_subtitle_aligned"),
    ]

    operations = [
        migrations.AddField(
            model_name="watchrecord",
            name="position",
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name="watchrecord",
            name="duration",
            field=models.FloatField(default=0),
        ),
    ]
