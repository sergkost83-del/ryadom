from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.identity.models import AuthThrottle, EmailLoginCode, RefreshToken, Session


class Command(BaseCommand):
    help = "Удаляет устаревшие коды входа, счётчики попыток, токены и завершённые сессии. Запускать ежедневно."

    def handle(self, *args, **options):
        now = timezone.now()
        codes = EmailLoginCode.objects.filter(created_at__lt=now - timedelta(days=1)).delete()[0]
        throttles = AuthThrottle.objects.filter(window_start__lt=now - timedelta(days=1)).delete()[0]
        tokens = RefreshToken.objects.filter(expires_at__lt=now).delete()[0]
        sessions = Session.objects.filter(revoked_at__lt=now - timedelta(days=30)).delete()[0]
        self.stdout.write(
            f"Удалено: кодов {codes}, счётчиков {throttles}, токенов {tokens}, сессий {sessions}."
        )
