"""Чаты: общий чат ЖК и чат дома. Доступ — только подтверждённым жителям (см. access.py)."""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.communities.models import Building, Community


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Room(BaseModel):
    """kind = 'house' — чат дома (building задан); kind = 'common' — общий чат ЖК (building пусто)."""

    community = models.ForeignKey(Community, on_delete=models.PROTECT, related_name="chat_rooms")
    building = models.ForeignKey(Building, on_delete=models.PROTECT, null=True, blank=True, related_name="chat_rooms")
    kind = models.CharField(max_length=10)
    title = models.CharField(max_length=200)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["building"], condition=Q(kind="house"), name="chat_room_one_house_per_building"
            ),
            models.UniqueConstraint(
                fields=["community"], condition=Q(kind="common"), name="chat_room_one_common_per_community"
            ),
        ]

    def __str__(self):
        return self.title


class Message(BaseModel):
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="messages")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="chat_messages"
    )
    body = models.CharField(max_length=1000)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["room", "created_at"], name="chat_message_room_created")]

    def hide(self, by):
        self.deleted_at = timezone.now()
        self.deleted_by = by
        self.save(update_fields=["deleted_at", "deleted_by", "updated_at"])

    def __str__(self):
        return f"сообщение в чате {self.room_id}"


class Report(BaseModel):
    """Жалоба на сообщение. Один человек — одна жалоба на сообщение."""

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_reports")
    reason = models.CharField(max_length=200)
    status = models.CharField(max_length=20, default="open")
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["message", "reporter"], name="chat_report_unique"),
        ]


class Block(BaseModel):
    """Блокировка автора: его сообщения перестают показываться только этому пользователю."""

    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_blocks_made")
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_blocks_received")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["blocker", "blocked"], name="chat_block_unique"),
        ]
