# Generated by Django 2.1.2 on 2018-11-01 09:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("pages", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="page",
            name="html",
            field=models.TextField(blank=True, default=""),
        )
    ]
