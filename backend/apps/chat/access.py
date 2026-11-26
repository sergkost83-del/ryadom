"""Кто может видеть чат. Единственное правило: подтверждённый житель соответствующего дома или ЖК."""

from apps.communities.models import Membership

from .models import Room


def confirmed_memberships(user):
    return Membership.objects.filter(user=user, status=Membership.STATUS_CONFIRMED).select_related("building__street")


def room_visible_to(user, room: Room) -> bool:
    if user is None or not user.is_authenticated or not user.is_active:
        return False
    memberships = confirmed_memberships(user)
    if room.kind == "house":
        return memberships.filter(building_id=room.building_id).exists()
    return memberships.filter(building__street__community_id=room.community_id).exists()


def visible_rooms(user):
    """Чаты пользователя: его дом и общий чат его ЖК."""
    from django.db.models import Q

    buildings = [m.building_id for m in confirmed_memberships(user)]
    communities = [m.building.street.community_id for m in confirmed_memberships(user)]
    return Room.objects.filter(
        Q(kind="house", building_id__in=buildings) | Q(kind="common", community_id__in=communities)
    ).order_by("kind", "title")
