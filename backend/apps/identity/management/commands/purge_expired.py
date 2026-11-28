from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from django.conf import settings

from apps.audit.service import record
from apps.communities.models import AddressChangeRequest, Membership
from apps.identity.models import AuthThrottle, Consent, EmailLoginCode, RefreshToken, Session, User


class Command(BaseCommand):
    help = "Удаляет устаревшие коды входа, счётчики попыток, токены и завершённые сессии. Запускать ежедневно."

    def handle(self, *args, **options):
        now = timezone.now()
        codes = EmailLoginCode.objects.filter(created_at__lt=now - timedelta(days=1)).delete()[0]
        throttles = AuthThrottle.objects.filter(window_start__lt=now - timedelta(days=1)).delete()[0]
        tokens = RefreshToken.objects.filter(expires_at__lt=now).delete()[0]
        sessions = Session.objects.filter(revoked_at__lt=now - timedelta(days=30)).delete()[0]
        erased = self._erase_accounts(now)
        phones = self._clear_phones_without_consent()
        memberships, address_requests = self._prune_closed_requests(now)
        self.stdout.write(
            f"Удалено: кодов {codes}, счётчиков {throttles}, токенов {tokens}, сессий {sessions}, "
            f"аккаунтов с истёкшим сроком удаления {erased}, телефонов без согласия {phones}, "
            f"закрытых заявок на адрес {memberships}, заявок на смену адреса {address_requests}."
        )

    @staticmethod
    def _clear_phones_without_consent():
        """Номер телефона хранится только при действующем согласии на него."""
        with_consent = Consent.objects.filter(consent_type="phone", withdrawn_at__isnull=True).values("user_id")
        return User.objects.exclude(phone="").exclude(id__in=with_consent).update(phone="")

    @staticmethod
    def _prune_closed_requests(now):
        """Закрытые заявки на адрес и смену адреса старше срока хранения удаляются."""
        cutoff = now - timedelta(days=settings.REQUEST_RETENTION_DAYS)
        memberships = Membership.objects.filter(
            status__in=[Membership.STATUS_REJECTED, Membership.STATUS_ENDED], updated_at__lt=cutoff
        ).delete()[0]
        address_requests = AddressChangeRequest.objects.filter(
            status__in=[
                AddressChangeRequest.STATUS_APPROVED,
                AddressChangeRequest.STATUS_REJECTED,
                AddressChangeRequest.STATUS_CANCELLED,
            ],
            updated_at__lt=cutoff,
        ).delete()[0]
        return memberships, address_requests

    @staticmethod
    def _erase_accounts(now):
        """Окончательно стирает аккаунты, у которых истёк срок после запроса на удаление."""
        limit = now - timedelta(days=settings.ACCOUNT_ERASURE_DAYS)
        users = list(User.objects.filter(deletion_requested_at__lt=limit, is_active=False))
        for user in users:
            EmailLoginCode.objects.filter(email=user.email).delete()
            user_id = user.pk
            user.delete()  # каскадом: сессии, токены, согласия, членства
            record(actor=None, action="account.erased", object_type="user", object_id=user_id,
                   note="окончательное стирание после срока удаления")
        return len(users)
