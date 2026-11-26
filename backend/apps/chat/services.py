"""Создание чатов, отправка, жалобы и блокировки. Все правила доступа проверяются здесь."""

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.identity.services import check_throttle

from .access import confirmed_memberships, room_visible_to
from .models import Block, Message, Report, Room
from .pure import clean_body


def ensure_rooms(user):
    """Создаёт чат дома и общий чат ЖК для подтверждённых адресов пользователя, если их ещё нет."""
    for membership in confirmed_memberships(user):
        building = membership.building
        community = building.street.community
        house_title = f"{building.street.name}, {building.label}"
        Room.objects.get_or_create(
            kind="house", building=building, defaults={"community": community, "title": house_title}
        )
        Room.objects.get_or_create(
            kind="common", community=community, building=None, defaults={"title": community.name}
        )


def get_room_for(user, room_id) -> Room:
    room = Room.objects.filter(pk=room_id).first()
    if room is None or not room_visible_to(user, room):
        raise NotFound()  # чужой чат выглядит как несуществующий
    return room


def blocked_author_ids(user):
    return list(Block.objects.filter(blocker=user).values_list("blocked_id", flat=True))


def list_messages(user, room: Room, before=None, limit=30):
    limit = min(max(int(limit or 30), 1), 50)
    qs = Message.objects.filter(room=room, deleted_at__isnull=True)
    qs = qs.exclude(author_id__in=blocked_author_ids(user))
    if before is not None:
        qs = qs.filter(created_at__lt=before)
    page = list(qs.select_related("author").order_by("-created_at")[:limit])
    page.reverse()  # в ленте — от старых к новым
    return page


def post_message(user, room: Room, raw_body: str) -> Message:
    check_throttle("chat-post", str(user.pk), settings.CHAT_POSTS_PER_10_MIN, 600)
    try:
        body = clean_body(raw_body)
    except ValueError as exc:
        raise ValidationError({"body": str(exc)}) from None
    return Message.objects.create(room=room, author=user, body=body)


def delete_own_message(user, message: Message):
    if message.author_id != user.pk:
        raise PermissionDenied("Удалить можно только своё сообщение.")
    if message.deleted_at is None:
        message.hide(user)


def report_message(user, message: Message, reason: str):
    if message.author_id == user.pk:
        raise ValidationError({"message": "Нельзя пожаловаться на своё сообщение."})
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError({"reason": "Опишите причину жалобы."})
    defaults = {"reason": reason[:200]}
    return Report.objects.get_or_create(message=message, reporter=user, defaults=defaults)


def block_author(user, message: Message) -> Block:
    target = message.author
    if target is None:
        raise ValidationError({"message": "Автор удалил аккаунт."})
    if target.pk == user.pk:
        raise ValidationError({"message": "Нельзя заблокировать себя."})
    block, _ = Block.objects.get_or_create(blocker=user, blocked=target)
    return block


def unblock(user, blocked_id):
    Block.objects.filter(blocker=user, blocked_id=blocked_id).delete()


def mark_report_decided(report: Report, by, status: str):
    report.status = status
    report.decided_by = by
    report.decided_at = timezone.now()
    report.save(update_fields=["status", "decided_by", "decided_at", "updated_at"])
