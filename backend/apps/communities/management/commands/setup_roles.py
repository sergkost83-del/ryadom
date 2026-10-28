from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError

MODERATOR_GROUP = "Модераторы"
# Модератор подтверждает адреса и публикует объявления домов; личные данные, сессии и согласия ему недоступны.
MODERATOR_PERMISSIONS = {
    "membership": ["view", "change"],
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
