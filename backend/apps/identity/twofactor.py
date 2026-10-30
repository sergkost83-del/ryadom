"""Двухфакторная защита сотрудников: приложение-аутентификатор + резервные коды."""

import hmac
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from . import totp
from .models import BackupCode, TOTPDevice

SESSION_KEY = "ryadom_2fa_verified_at"


def is_verified(request):
    raw = request.session.get(SESSION_KEY)
    if not raw:
        return False
    try:
        moment = datetime.fromisoformat(raw)
    except ValueError:
        return False
    return timezone.now() - moment < timedelta(hours=settings.ADMIN_2FA_SESSION_HOURS)


def mark_verified(request):
    request.session[SESSION_KEY] = timezone.now().isoformat()
    request.session.cycle_key()


def confirmed_device(user):
    return TOTPDevice.objects.filter(user=user, confirmed_at__isnull=False).first()


def pending_device(user):
    """Неподтверждённое устройство (между показом QR и вводом кода). Секрет не меняется при перезагрузке."""
    device = TOTPDevice.objects.filter(user=user, confirmed_at__isnull=True).first()
    if device is None:
        device = TOTPDevice.objects.create(user=user, secret=totp.generate_secret())
    return device


def confirm_device(user, code):
    device = TOTPDevice.objects.filter(user=user, confirmed_at__isnull=True).first()
    if device is None:
        return False
    step = totp.verify_totp(device.secret, code)
    if step is None:
        return False
    device.confirmed_at = timezone.now()
    device.last_used_step = step
    device.save(update_fields=["confirmed_at", "last_used_step"])
    return True


def verify_code(user, code):
    """Принимает код из приложения или резервный код. Возвращает 'totp', 'backup' или None."""
    device = confirmed_device(user)
    if device is None:
        return None
    normalized = totp.normalize_code(code)
    if len(normalized) == totp.DIGITS and normalized.isdigit():
        with transaction.atomic():
            locked = TOTPDevice.objects.select_for_update().get(pk=device.pk)
            step = totp.verify_totp(locked.secret, normalized, last_step=locked.last_used_step)
            if step is None:
                return None
            locked.last_used_step = step
            locked.save(update_fields=["last_used_step"])
        return "totp"
    expected = totp.hash_secret_code(settings.SECRET_KEY, "backup", normalized)
    with transaction.atomic():
        for row in BackupCode.objects.select_for_update().filter(user=user, used_at__isnull=True):
            if hmac.compare_digest(row.code_hash, expected):
                row.used_at = timezone.now()
                row.save(update_fields=["used_at"])
                return "backup"
    return None


def issue_backup_codes(user):
    """Выпускает новый набор кодов (старые становятся недействительными). Открытые коды показываются один раз."""
    codes = [totp.generate_group_code(2, 5) for _ in range(settings.BACKUP_CODES_COUNT)]
    with transaction.atomic():
        BackupCode.objects.filter(user=user).delete()
        BackupCode.objects.bulk_create(
            [BackupCode(user=user, code_hash=totp.hash_secret_code(settings.SECRET_KEY, "backup", c)) for c in codes]
        )
    return codes


def remaining_backup_codes(user):
    return BackupCode.objects.filter(user=user, used_at__isnull=True).count()


def reset_two_factor(user):
    """Сбрасывает защиту (потерян телефон и коды): при следующем входе сотрудник настроит её заново."""
    TOTPDevice.objects.filter(user=user).delete()
    BackupCode.objects.filter(user=user).delete()
