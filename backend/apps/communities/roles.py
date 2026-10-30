from django.contrib.auth.models import Group

from apps.identity.twofactor import reset_two_factor

MODERATOR_GROUP = "Модераторы"


def promote_to_moderator(user):
    """Даёт доступ сотруднику в админку. Видимые данные ограничиваются привязкой к ЖК (отдельно)."""
    group, _ = Group.objects.get_or_create(name=MODERATOR_GROUP)
    user.groups.add(group)
    if not user.is_staff:
        user.is_staff = True
        user.save(update_fields=["is_staff"])


def demote_moderator(user):
    """Снимает роль: убирает группу, привязки к ЖК и двухфакторную защиту. Главного администратора не трогает."""
    from .models import ModeratorAssignment

    if user.is_superuser:
        return False
    user.groups.remove(*user.groups.filter(name=MODERATOR_GROUP))
    ModeratorAssignment.objects.filter(user=user).delete()
    reset_two_factor(user)
    user.is_staff = False
    user.save(update_fields=["is_staff"])
    return True
