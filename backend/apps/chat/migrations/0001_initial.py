import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def base_fields():
    return [
        ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
        ("created_at", models.DateTimeField(auto_now_add=True)),
        ("updated_at", models.DateTimeField(auto_now=True)),
    ]


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("communities", "0004_moderation_invites_address_change"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Room",
            fields=base_fields()
            + [
                ("kind", models.CharField(max_length=10)),
                ("title", models.CharField(max_length=200)),
                (
                    "building",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="chat_rooms",
                        to="communities.building",
                    ),
                ),
                (
                    "community",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="chat_rooms",
                        to="communities.community",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="room",
            constraint=models.UniqueConstraint(
                condition=models.Q(("kind", "house")),
                fields=("building",),
                name="chat_room_one_house_per_building",
            ),
        ),
        migrations.AddConstraint(
            model_name="room",
            constraint=models.UniqueConstraint(
                condition=models.Q(("kind", "common")),
                fields=("community",),
                name="chat_room_one_common_per_community",
            ),
        ),
        migrations.CreateModel(
            name="Message",
            fields=base_fields()
            + [
                ("body", models.CharField(max_length=1000)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                (
                    "author",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="chat_messages",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "room",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="messages",
                        to="chat.room",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(fields=["room", "created_at"], name="chat_message_room_created"),
        ),
        migrations.CreateModel(
            name="Report",
            fields=base_fields()
            + [
                ("reason", models.CharField(max_length=200)),
                ("status", models.CharField(default="open", max_length=20)),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                (
                    "decided_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reports",
                        to="chat.message",
                    ),
                ),
                (
                    "reporter",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chat_reports",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="report",
            constraint=models.UniqueConstraint(fields=("message", "reporter"), name="chat_report_unique"),
        ),
        migrations.CreateModel(
            name="Block",
            fields=base_fields()
            + [
                (
                    "blocked",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chat_blocks_received",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "blocker",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chat_blocks_made",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="block",
            constraint=models.UniqueConstraint(fields=("blocker", "blocked"), name="chat_block_unique"),
        ),
    ]
