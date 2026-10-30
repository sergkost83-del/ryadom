"""Единое место, где решается, что житель вправе видеть.

Правило: доступ к закрытым данным дома даёт только ПОДТВЕРЖДЁННОЕ членство в этом доме.
Новые закрытые данные (чаты, парковка, поездки) обязаны получать выборку через эту функцию.
"""

from .models import Membership, Notice


def confirmed_building_ids(user):
    if user is None or not user.is_authenticated:
        return Membership.objects.none().values_list("building_id", flat=True)
    return Membership.objects.filter(user=user, status=Membership.STATUS_CONFIRMED).values_list(
        "building_id", flat=True
    )


def has_confirmed_membership(user):
    return confirmed_building_ids(user).exists()


def notices_visible_to(user):
    return Notice.objects.filter(is_published=True, building_id__in=confirmed_building_ids(user))


def moderated_community_ids(user):
    """Какими ЖК вправе управлять сотрудник.

    None — всеми (главный администратор); список — только перечисленными (модератор); пустой список — ничем.
    Проверяется на сервере при каждом обращении к данным в админке.
    """
    from .models import ModeratorAssignment

    if user is None or not user.is_authenticated or not user.is_active or not user.is_staff:
        return []
    if user.is_superuser:
        return None
    return list(ModeratorAssignment.objects.filter(user=user).values_list("community_id", flat=True))


def can_moderate_building(user, building):
    ids = moderated_community_ids(user)
    return ids is None or building.street.community_id in ids
