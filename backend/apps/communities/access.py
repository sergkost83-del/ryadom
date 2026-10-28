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
