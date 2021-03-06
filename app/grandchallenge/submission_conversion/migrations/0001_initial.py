# Generated by Django 2.0.8 on 2018-08-27 06:25

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("datasets", "0002_annotationset_submission"),
        ("evaluation", "0007_auto_20180815_1321"),
    ]

    operations = [
        migrations.CreateModel(
            name="SubmissionToAnnotationSetJob",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                (
                    "status",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (0, "The task is waiting for execution"),
                            (1, "The task has been started"),
                            (
                                2,
                                "The task is to be retried, possibly because of failure",
                            ),
                            (
                                3,
                                "The task raised an exception, or has exceeded the retry limit",
                            ),
                            (4, "The task executed successfully"),
                            (5, "The task was cancelled"),
                        ],
                        default=0,
                    ),
                ),
                ("output", models.TextField()),
                (
                    "base",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="datasets.ImageSet",
                    ),
                ),
                (
                    "submission",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="evaluation.Submission",
                    ),
                ),
            ],
            options={"abstract": False},
        )
    ]
