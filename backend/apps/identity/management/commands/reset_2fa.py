from django.core.management.base import BaseCommand, CommandError

from apps.audit.service import record
from apps.identity import twofactor
from apps.identity.models import User, normalize_email


class Command(BaseCommand):
    help = "Сбрасывает двухфакторную защиту сотрудника (нет телефона и кодов, в том числе у главного админа)."

    def add_arguments(self, parser):
        parser.add_argument("email")

    def handle(self, *args, **options):
        user = User.objects.filter(email=normalize_email(options["email"]), is_staff=True).first()
        if user is None:
            raise CommandError("Сотрудник с таким e-mail не найден.")
        twofactor.reset_two_factor(user)
        record(actor=None, action="staff.2fa_reset_cli", object_type="staff", object_id=user.pk,
               note="сброс из командной строки сервера")
        self.stdout.write(self.style.SUCCESS("Защита сброшена: при следующем входе нужно настроить приложение заново."))
