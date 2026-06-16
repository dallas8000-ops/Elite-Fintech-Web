# Generated manually for East Africa country field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="country",
            field=models.CharField(default="UG", max_length=2),
        ),
        migrations.AlterField(
            model_name="organization",
            name="province",
            field=models.CharField(default="CENTRAL", max_length=32),
        ),
    ]
