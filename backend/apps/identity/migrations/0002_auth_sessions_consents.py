import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="avatar_id",
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="user",
            name="phone",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="user",
            name="account_type",
            field=models.CharField(default="adult", max_length=20),
        ),
        migrations.AddField(
            model_name="user",
            name="age_confirmed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="EmailLoginCode",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("email", models.EmailField(max_length=254)),
                ("code_hash", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("expires_at", models.DateTimeField()),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("used_at", models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.AddIndex(
            model_name="emaillogincode",
            index=models.Index(fields=["email", "created_at"], name="identity_code_email_created"),
        ),
        migrations.CreateModel(
            name="AuthThrottle",
            fields=[
                ("key", models.CharField(max_length=64, primary_key=True, serialize=False)),
                ("count", models.PositiveIntegerField(default=0)),
                ("window_start", models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name="Session",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("device_name", models.CharField(blank=True, max_length=60)),
                ("user_agent", models.CharField(blank=True, max_length=200)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("last_seen_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="RefreshToken",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("token_hash", models.CharField(max_length=64, unique=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("expires_at", models.DateTimeField()),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="refresh_tokens",
                        to="identity.session",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Consent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("consent_type", models.CharField(max_length=30)),
                ("version", models.CharField(max_length=40)),
                ("accepted_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("withdrawn_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="consents",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="consent",
            constraint=models.UniqueConstraint(
                fields=("user", "consent_type", "version"), name="identity_consent_unique"
            ),
        ),
    ]
