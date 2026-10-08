"""Global & Local Events: scope, attendance mode, join links and registrations.

Adds everything the events page needs to show both worldwide and nearby
opportunities and to let a farmer tap Join (Google Meet / Zoom / WhatsApp /
in person) or Register in one click.
"""

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core_up", "0002_farm_user_profile_completed_diseasereport_croprecord_and_more"),
    ]

    operations = [
        # ---------- Event: audience, attendance and registration ----------
        migrations.AddField(
            model_name="event",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="event",
            name="host",
            field=models.CharField(blank=True, help_text="Organisation running the event", max_length=200),
        ),
        migrations.AddField(
            model_name="event",
            name="scope",
            field=models.CharField(
                choices=[("local", "Local"), ("global", "Global")],
                db_index=True,
                default="local",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="event",
            name="country",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="event",
            name="region",
            field=models.CharField(blank=True, help_text="State / province / county", max_length=100),
        ),
        migrations.AddField(
            model_name="event",
            name="is_online",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="event",
            name="join_mode",
            field=models.CharField(
                choices=[
                    ("google_meet", "Google Meet"),
                    ("zoom", "Zoom"),
                    ("teams", "Microsoft Teams"),
                    ("whatsapp", "WhatsApp Group"),
                    ("livestream", "Livestream / YouTube"),
                    ("website", "Register on host website"),
                    ("in_person", "In person (venue)"),
                    ("phone", "Phone / Dial-in"),
                ],
                default="website",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="event",
            name="join_url",
            field=models.URLField(blank=True, help_text="Direct Google Meet / Zoom / livestream link"),
        ),
        migrations.AddField(
            model_name="event",
            name="access_link",
            field=models.CharField(blank=True, help_text="Link or dial-in shown to farmers", max_length=255),
        ),
        migrations.AddField(
            model_name="event",
            name="access_code",
            field=models.CharField(blank=True, help_text="Passcode / dial-in PIN, shown after registering", max_length=100),
        ),
        migrations.AddField(
            model_name="event",
            name="whatsapp_link",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="event",
            name="registration_required",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="event",
            name="registration_url",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="event",
            name="registration_deadline",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="event",
            name="capacity",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="event",
            name="cost",
            field=models.CharField(
                choices=[("free", "Free"), ("paid", "Paid"), ("sponsored", "Sponsored / Invitation only")],
                default="free",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="event",
            name="image_url",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="event",
            name="source_url",
            field=models.URLField(blank=True, help_text="Official event page, for verification"),
        ),
        migrations.AddField(
            model_name="event",
            name="tags",
            field=models.CharField(blank=True, help_text="Comma separated keywords", max_length=255),
        ),
        migrations.AlterField(
            model_name="event",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("training", "Training / Workshop"),
                    ("webinar", "Webinar"),
                    ("conference", "Conference / Summit"),
                    ("expo", "Exhibition / Expo"),
                    ("field_day", "Field Day / Demo"),
                    ("grant", "Grant / Funding Call"),
                ],
                default="training",
                max_length=50,
            ),
        ),
        migrations.AlterModelOptions(
            name="event",
            options={
                "ordering": ["start_date"],
                "verbose_name": "Event",
                "verbose_name_plural": "Events",
            },
        ),
        migrations.AddIndex(
            model_name="event",
            index=models.Index(fields=["scope", "start_date"], name="core_up_eve_scope_6a0bd2_idx"),
        ),
        # ---------- Registrations ----------
        migrations.CreateModel(
            name="EventRegistration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("full_name", models.CharField(max_length=150)),
                ("phone", models.CharField(max_length=20)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("county", models.CharField(blank=True, max_length=100)),
                ("organisation", models.CharField(blank=True, max_length=150)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("registered", "Registered"),
                            ("confirmed", "Confirmed"),
                            ("attended", "Attended"),
                            ("cancelled", "Cancelled"),
                            ("waitlist", "Waitlisted"),
                        ],
                        default="registered",
                        max_length=20,
                    ),
                ),
                ("wants_reminder", models.BooleanField(default=True)),
                ("reference", models.CharField(blank=True, max_length=12, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="registrations",
                        to="core_up.event",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="event_registrations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Event Registration",
                "verbose_name_plural": "Event Registrations",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="eventregistration",
            constraint=models.UniqueConstraint(
                fields=("event", "phone"),
                name="unique_event_registration_phone",
            ),
        ),
    ]
