from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("movies_app", "0004_renditions"),
    ]

    operations = [
        migrations.AddField(
            model_name="movie",
            name="rank",
            field=models.FloatField(db_index=True, default=0),
        ),
    ]
