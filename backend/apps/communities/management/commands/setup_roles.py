from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError

from apps.communities.roles import MODERATOR_GROUP

# Модератор подтверждает адреса, решает заявки на смену адреса, выдаёт приглашения и публикует объявления своего ЖК.
# Привязки к ЖК, журнал аудита, пользователи, сессии и согласия ему недоступны; данные ограничены его ЖК.
MODERATOR_PERMISSIONS = {
    "membership": ["view", "change"],
    "addresschangerequest": ["view", "change"],
    "houseinvite": ["view", "add", "change"],
    "notice": ["view", "add", "change", "delete"],
    "building": ["view"],
    "street": ["view"],
    "community": ["view"],
}


class Command(BaseCommand):
    help = "Создаёт или обновляет группу «Модераторы» с минимально необходимыми правами. Безопасно запускать повторно."

    def handle(self, *args, **options):
        group, _ = Group.objects.get_or_create(name=MODERATOR_GROUP)
        permissions = []
        for model, actions in MODERATOR_PERMISSIONS.items():
            for action in actions:
                codename = f"{action}_{model}"
                try:
                    permissions.append(
                        Permission.objects.get(content_type__app_label="communities", codename=codename)
                    )
                except Permission.DoesNotExist:
                    raise CommandError(f"Не найдено право communities.{codename}. Выполните migrate.") from None
        group.permissions.set(permissions)
        self.stdout.write(self.style.SUCCESS(f"Группа «{MODERATOR_GROUP}»: прав {len(permissions)}."))
