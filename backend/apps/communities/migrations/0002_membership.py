import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("communities", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Membership",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "role",
                    models.CharField(choices=[("resident", "Житель")], default="resident", max_length=20),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Ожидает подтверждения"),
                            ("confirmed", "Подтверждён"),
                            ("rejected", "Отклонён"),
                            ("ended", "Завершён"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("valid_from", models.DateTimeField(default=django.utils.timezone.now)),
                ("valid_to", models.DateTimeField(blank=True, null=True)),
                (
                    "building",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="memberships",
                        to="communities.building",
                    ),
                ),
                (
                    "confirmed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memberships",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="membership",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status__in", ["pending", "confirmed"])),
                fields=("user",),
                name="communities_membership_one_active_per_user",
            ),
        ),
    ]
