from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError

from apps.communities.roles import MODERATOR_GROUP

# Модератор подтверждает адреса, решает заявки на смену адреса, выдаёт приглашения, публикует объявления,
# модерирует чаты своего ЖК. Привязки к ЖК, журнал аудита, пользователи, сессии и согласия ему недоступны.
MODERATOR_PERMISSIONS = {
    "communities": {
        "membership": ["view", "change"],
        "addresschangerequest": ["view", "change"],
        "houseinvite": ["view", "add", "change"],
        "notice": ["view", "add", "change", "delete"],
        "building": ["view"],
        "street": ["view"],
        "community": ["view"],
    },
    "chat": {
        "room": ["view"],
        "message": ["view", "change"],
        "report": ["view", "change"],
    },
}


class Command(BaseCommand):
    help = "Создаёт или обновляет группу «Модераторы» с минимально необходимыми правами. Безопасно запускать повторно."

    def handle(self, *args, **options):
        group, _ = Group.objects.get_or_create(name=MODERATOR_GROUP)
        permissions = []
        for app_label, models_actions in MODERATOR_PERMISSIONS.items():
            for model, actions in models_actions.items():
                for action in actions:
                    codename = f"{action}_{model}"
                    try:
                        permissions.append(Permission.objects.get(content_type__app_label=app_label, codename=codename))
                    except Permission.DoesNotExist:
                        raise CommandError(f"Не найдено право {app_label}.{codename}. Выполните migrate.") from None
        group.permissions.set(permissions)
        self.stdout.write(self.style.SUCCESS(f"Группа «{MODERATOR_GROUP}»: прав {len(permissions)}."))
