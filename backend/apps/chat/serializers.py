from rest_framework import serializers

from .models import Message, Room


def room_payload(room: Room):
    return {"id": str(room.id), "kind": room.kind, "title": room.title}


def message_payload(message: Message, viewer):
    author = message.author
    return {
        "id": str(message.id),
        "body": message.body,
        "created_at": message.created_at,
        "mine": author is not None and author.pk == viewer.pk,
        "author": {
            "id": str(author.pk),
            "display_name": author.display_name or "Сосед",
            "avatar_id": author.avatar_id,
        }
        if author is not None
        else None,
    }


class BodySerializer(serializers.Serializer):
    body = serializers.CharField(max_length=2000, allow_blank=True)


class ReportSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=200, allow_blank=True)
