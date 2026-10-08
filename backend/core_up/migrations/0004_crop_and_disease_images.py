"""Crop and disease photo uploads.

Adds image fields to crop records and disease reports, plus a DiseasePhoto
model for extra angles of the same affected plant. Farmers upload straight from
a phone camera, so the API accepts multipart requests for these endpoints.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core_up", "0003_event_scope_join_and_registrations"),
    ]

    operations = [
        # ---------- Crop records: field photo ----------
        migrations.AddField(
            model_name="croprecord",
            name="image",
            field=models.ImageField(
                blank=True,
                help_text="Photo of the crop or field",
                null=True,
                upload_to="crops/%Y/%m/",
            ),
        ),
        migrations.AddField(
            model_name="croprecord",
            name="photo_url",
            field=models.URLField(blank=True, help_text="Alternative: link to an image"),
        ),
        # ---------- Disease reports: photo + context + analysis flag ----------
        migrations.AddField(
            model_name="diseasereport",
            name="image",
            field=models.ImageField(
                blank=True,
                help_text="Main photo of the affected plant",
                null=True,
                upload_to="diseases/%Y/%m/",
            ),
        ),
        migrations.AddField(
            model_name="diseasereport",
            name="photo_stage",
            field=models.CharField(
                blank=True,
                choices=[
                    ("leaf", "Leaf / close-up"),
                    ("whole_plant", "Whole plant"),
                    ("stem", "Stem"),
                    ("fruit", "Fruit / pod"),
                    ("root", "Root"),
                    ("field", "Whole field"),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="diseasereport",
            name="variety",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="diseasereport",
            name="growth_stage",
            field=models.CharField(
                blank=True, help_text="e.g. seedling, flowering", max_length=100
            ),
        ),
        migrations.AddField(
            model_name="diseasereport",
            name="affected_area",
            field=models.CharField(
                blank=True, help_text="e.g. about a quarter of the field", max_length=100
            ),
        ),
        migrations.AddField(
            model_name="diseasereport",
            name="needs_analysis",
            field=models.BooleanField(
                default=False,
                help_text="Queued for disease analysis — no diagnosis recorded yet",
            ),
        ),
        migrations.AlterField(
            model_name="diseasereport",
            name="photo_url",
            field=models.URLField(blank=True, help_text="Alternative: link to an image"),
        ),
        # ---------- Extra photos per report ----------
        migrations.CreateModel(
            name="DiseasePhoto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="diseases/%Y/%m/")),
                (
                    "photo_stage",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("leaf", "Leaf / close-up"),
                            ("whole_plant", "Whole plant"),
                            ("stem", "Stem"),
                            ("fruit", "Fruit / pod"),
                            ("root", "Root"),
                            ("field", "Whole field"),
                        ],
                        max_length=20,
                    ),
                ),
                ("caption", models.CharField(blank=True, max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "report",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="photos",
                        to="core_up.diseasereport",
                    ),
                ),
            ],
            options={"ordering": ["id"]},
        ),
    ]
