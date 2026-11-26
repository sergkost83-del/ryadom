import getpass

from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_password

from apps.audit.service import record
from apps.identity.models import User, normalize_email


class Command(BaseCommand):
    help = "Задаёт пароль сотруднику (модератору), чтобы он мог войти в админку. Пароль вводится в консоли."

    def add_arguments(self, parser):
        parser.add_argument("email")

    def handle(self, *args, **options):
        user = User.objects.filter(email=normalize_email(options["email"])).first()
        if user is None or not user.is_staff:
            raise CommandError("Сотрудник с таким e-mail не найден (сначала назначьте модератора).")
        password = getpass.getpass("Новый пароль (не короче 12 символов): ")
        if password != getpass.getpass("Повторите пароль: "):
            raise CommandError("Пароли не совпадают.")
        try:
            validate_password(password, user=user)
        except Exception as exc:  # noqa: BLE001
            raise CommandError("Пароль не подходит: " + " ".join(getattr(exc, "messages", [str(exc)]))) from None
        user.set_password(password)
        user.save(update_fields=["password"])
        record(actor=None, action="staff.password_set", object_type="staff", object_id=user.pk,
               note="пароль задан из командной строки сервера")
        self.stdout.write(self.style.SUCCESS("Пароль задан. При первом входе в админку настройте защиту."))
