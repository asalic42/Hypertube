from django.db import migrations


class Migration(migrations.Migration):
    """The prototype Movie table is replaced by the catalogue models of 0003."""

    dependencies = [
        ("movies_app", "0001_initial"),
    ]

    operations = [
        migrations.DeleteModel(name="Movie"),
    ]
