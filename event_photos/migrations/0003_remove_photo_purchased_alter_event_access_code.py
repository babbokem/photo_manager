# Generated by Django 5.1.4 on 2024-12-24 16:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "event_photos",
            "0002_remove_event_date_event_date_created_photo_purchased_and_more",
        ),
    ]

    operations = [
        migrations.RemoveField(
            model_name="photo",
            name="purchased",
        ),
        migrations.AlterField(
            model_name="event",
            name="access_code",
            field=models.CharField(default="c78b8e6782", max_length=20, unique=True),
        ),
    ]
