# Generated by Django 2.1.5 on 2019-01-29 15:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("challenges", "0017_auto_20181214_1256")]

    operations = [
        migrations.AddField(
            model_name="challenge",
            name="educational_challenge",
            field=models.BooleanField(
                default=False, help_text="It is an educational challange"
            ),
        ),
        migrations.AddField(
            model_name="externalchallenge",
            name="educational_challenge",
            field=models.BooleanField(
                default=False, help_text="It is an educational challange"
            ),
        ),
    ]