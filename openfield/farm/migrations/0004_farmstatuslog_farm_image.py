# Generated by Django 5.0.6 on 2024-07-02 02:08

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("farm", "0003_farm_farm_name_farm_farm_size"),
    ]

    operations = [
        migrations.AddField(
            model_name="farmstatuslog",
            name="farm_image",
            field=models.ImageField(blank=True, null=True, upload_to="farm_image"),
        ),
    ]
