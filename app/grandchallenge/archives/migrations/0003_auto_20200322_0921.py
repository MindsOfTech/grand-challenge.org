# Generated by Django 3.0.2 on 2020-03-22 09:21

import django.db.models.deletion
import django_extensions.db.fields
from django.db import migrations, models

import grandchallenge.challenges.models
import grandchallenge.core.storage


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0011_update_proxy_permissions"),
        ("workstation_configs", "0003_auto_20200110_1358"),
        ("workstations", "0008_workstation_public"),
        ("archives", "0002_auto_20200321_1044"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="archive",
            options={
                "ordering": ("created",),
                "permissions": [("upload_archive", "Can upload to archive")],
            },
        ),
        migrations.AddField(
            model_name="archive",
            name="description",
            field=models.TextField(
                blank=True, null=True, verbose_name="description"
            ),
        ),
        migrations.AddField(
            model_name="archive",
            name="detail_page_markdown",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="archive",
            name="editors_group",
            field=models.OneToOneField(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="editors_of_archive",
                to="auth.Group",
            ),
        ),
        migrations.AddField(
            model_name="archive",
            name="logo",
            field=models.ImageField(
                null=True,
                storage=grandchallenge.core.storage.PublicS3Storage(),
                upload_to=grandchallenge.challenges.models.get_logo_path,
            ),
        ),
        migrations.AddField(
            model_name="archive",
            name="public",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="archive",
            name="slug",
            field=django_extensions.db.fields.AutoSlugField(
                blank=True,
                editable=False,
                populate_from="title",
                verbose_name="slug",
            ),
        ),
        migrations.AddField(
            model_name="archive",
            name="uploaders_group",
            field=models.OneToOneField(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="uploaders_of_archive",
                to="auth.Group",
            ),
        ),
        migrations.AddField(
            model_name="archive",
            name="users_group",
            field=models.OneToOneField(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="users_of_archive",
                to="auth.Group",
            ),
        ),
        migrations.AddField(
            model_name="archive",
            name="workstation",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="workstations.Workstation",
            ),
        ),
        migrations.AddField(
            model_name="archive",
            name="workstation_config",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="workstation_configs.WorkstationConfig",
            ),
        ),
        migrations.AlterField(
            model_name="archive",
            name="title",
            field=models.CharField(max_length=255, verbose_name="title"),
        ),
    ]
