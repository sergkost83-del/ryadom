import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def base_fields():
    return [
        ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
        ("created_at", models.DateTimeField(auto_now_add=True)),
        ("updated_at", models.DateTimeField(auto_now=True)),
    ]


def user_fk(related_name, *, nullable=True, cascade=False):
    kwargs = {
        "on_delete": django.db.models.deletion.CASCADE if cascade else django.db.models.deletion.SET_NULL,
        "related_name": related_name,
        "to": settings.AUTH_USER_MODEL,
    }
    if nullable:
        kwargs.update(blank=True, null=True)
    return models.ForeignKey(**kwargs)


class Migration(migrations.Migration):
    dependencies = [
        ("communities", "0003_notice"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ModeratorAssignment",
            fields=base_fields()
            + [
                (
                    "community",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="moderator_assignments",
                        to="communities.community",
                    ),
                ),
                ("created_by", user_fk("+")),
                ("user", user_fk("moderator_assignments", nullable=False, cascade=True)),
            ],
        ),
        migrations.AddConstraint(
            model_name="moderatorassignment",
            constraint=models.UniqueConstraint(fields=("user", "community"), name="communities_moderator_unique"),
        ),
        migrations.CreateModel(
            name="HouseInvite",
            fields=base_fields()
            + [
                ("code_hash", models.CharField(max_length=64, unique=True)),
                ("expires_at", models.DateTimeField()),
                ("note", models.CharField(blank=True, max_length=120)),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                (
                    "building",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="invites",
                        to="communities.building",
                    ),
                ),
                ("created_by", user_fk("+")),
                ("revoked_by", user_fk("+")),
                ("used_by", user_fk("+")),
            ],
        ),
        migrations.CreateModel(
            name="AddressChangeRequest",
            fields=base_fields()
            + [
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Ожидает решения"),
                            ("approved", "Одобрена"),
                            ("rejected", "Отклонена"),
                            ("cancelled", "Отменена"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                ("comment", models.CharField(blank=True, max_length=200)),
                (
                    "from_building",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="communities.building",
                    ),
                ),
                (
                    "to_building",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="communities.building",
                    ),
                ),
                ("decided_by", user_fk("+")),
                (
                    "via_invite",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="communities.houseinvite",
                    ),
                ),
                ("user", user_fk("address_change_requests", nullable=False, cascade=True)),
            ],
        ),
        migrations.AddConstraint(
            model_name="addresschangerequest",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status", "pending")),
                fields=("user",),
                name="communities_addresschange_one_pending_per_user",
            ),
        ),
    ]
