from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("movies_app", "0005_movie_rank"),
    ]

    operations = [
        migrations.AddField(
            model_name="download",
            name="duration",
            field=models.FloatField(blank=True, help_text="Seconds.", null=True),
        ),
        migrations.AddField(
            model_name="download",
            name="frame_rate",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="download",
            name="file_hash",
            field=models.CharField(blank=True, max_length=16),
        ),
    ]
