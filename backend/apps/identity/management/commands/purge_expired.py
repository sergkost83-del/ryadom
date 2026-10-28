from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from django.conf import settings

from apps.identity.models import AuthThrottle, EmailLoginCode, RefreshToken, Session, User


class Command(BaseCommand):
    help = "Удаляет устаревшие коды входа, счётчики попыток, токены и завершённые сессии. Запускать ежедневно."

    def handle(self, *args, **options):
        now = timezone.now()
        codes = EmailLoginCode.objects.filter(created_at__lt=now - timedelta(days=1)).delete()[0]
        throttles = AuthThrottle.objects.filter(window_start__lt=now - timedelta(days=1)).delete()[0]
        tokens = RefreshToken.objects.filter(expires_at__lt=now).delete()[0]
        sessions = Session.objects.filter(revoked_at__lt=now - timedelta(days=30)).delete()[0]
        erased = self._erase_accounts(now)
        self.stdout.write(
            f"Удалено: кодов {codes}, счётчиков {throttles}, токенов {tokens}, сессий {sessions}, "
            f"аккаунтов с истёкшим сроком удаления {erased}."
        )

    @staticmethod
    def _erase_accounts(now):
        """Окончательно стирает аккаунты, у которых истёк срок после запроса на удаление."""
        limit = now - timedelta(days=settings.ACCOUNT_ERASURE_DAYS)
        users = list(User.objects.filter(deletion_requested_at__lt=limit, is_active=False))
        for user in users:
            EmailLoginCode.objects.filter(email=user.email).delete()
            user.delete()  # каскадом: сессии, токены, согласия, членства
        return len(users)
