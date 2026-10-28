"""Бизнес-логика входа: коды, ограничения частоты, сессии. Вьюхи только вызывают эти функции."""

import logging
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, Throttled

from . import pure
from .models import AuthThrottle, EmailLoginCode, RefreshToken, Session, normalize_email

logger = logging.getLogger(__name__)

ACCESS_SALT = "ryadom.access"
REGISTER_SALT = "ryadom.register"


class InvalidCode(APIException):
    status_code = 400
    default_detail = "Неверный или просроченный код."
    default_code = "invalid_code"


class SessionInvalid(APIException):
    # Именно APIException со статусом 401: у публичных адресов DRF иначе заменил бы 401 на 403.
    status_code = 401
    default_detail = "Сессия недействительна. Войдите заново."
    default_code = "session_invalid"


class Conflict(APIException):
    status_code = 409
    default_detail = "Такой аккаунт уже существует. Войдите по коду."
    default_code = "conflict"


class MailUnavailable(APIException):
    status_code = 503
    default_detail = "Не удалось отправить письмо. Попробуйте позже."
    default_code = "mail_unavailable"


def check_throttle(scope, value, limit, window_seconds):
    """Учитывает попытку. При превышении лимита — ответ 429 с Retry-After."""
    key = pure.hash_key(scope, value)
    now = timezone.now()
    wait = None
    with transaction.atomic():
        row, _ = AuthThrottle.objects.select_for_update().get_or_create(
            key=key, defaults={"count": 0, "window_start": now}
        )
        if (now - row.window_start).total_seconds() >= window_seconds:
            row.count = 0
            row.window_start = now
        if row.count >= limit:
            wait = max(int(window_seconds - (now - row.window_start).total_seconds()) + 1, 1)
        else:
            row.count += 1
            row.save(update_fields=["count", "window_start"])
    if wait is not None:
        raise Throttled(wait=wait, detail="Слишком много попыток. Повторите позже.")


def request_login_code(email, ip):
    email = normalize_email(email)
    check_throttle("code-request-ip", ip, settings.AUTH_REQUESTS_PER_IP_HOUR, 3600)
    check_throttle("code-request-email", email, settings.AUTH_REQUESTS_PER_EMAIL_HOUR, 3600)
    now = timezone.now()
    last = EmailLoginCode.objects.filter(email=email, used_at__isnull=True).order_by("-created_at").first()
    if last and (now - last.created_at).total_seconds() < settings.AUTH_CODE_RESEND_SECONDS:
        return  # неиспользованный код отправлен недавно; ответ клиенту одинаков
    code = pure.generate_code()
    EmailLoginCode.objects.create(
        email=email,
        code_hash=pure.hash_code(settings.SECRET_KEY, email, code),
        expires_at=now + timedelta(seconds=settings.AUTH_CODE_TTL_SECONDS),
    )
    minutes = settings.AUTH_CODE_TTL_SECONDS // 60
    try:
        send_mail(
            subject="Код входа в РЯДОМ",
            message=(
                f"Ваш код входа в РЯДОМ: {code}\n\n"
                f"Код действует {minutes} минут. Никому его не сообщайте.\n"
                "Если вы не запрашивали код, просто проигнорируйте это письмо."
            ),
            from_email=None,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception:  # noqa: BLE001
        logger.error("Не удалось отправить письмо с кодом входа")
        raise MailUnavailable() from None


def verify_login_code(email, code, ip):
    """Проверяет код. Каждая попытка учитывается; после лимита ошибок код сгорает."""
    email = normalize_email(email)
    check_throttle("code-verify-ip", ip, settings.AUTH_VERIFY_PER_IP_HOUR, 3600)
    check_throttle("code-verify-email", email, settings.AUTH_VERIFY_PER_EMAIL_HOUR, 3600)
    now = timezone.now()
    ok = False
    with transaction.atomic():
        entry = (
            EmailLoginCode.objects.select_for_update()
            .filter(email=email, used_at__isnull=True, expires_at__gt=now)
            .order_by("-created_at")
            .first()
        )
        if entry is not None:
            entry.attempts += 1
            expected = pure.hash_code(settings.SECRET_KEY, email, code)
            if _same(entry.code_hash, expected):
                ok = True
                entry.used_at = now
            elif entry.attempts >= settings.AUTH_CODE_MAX_ATTEMPTS:
                entry.used_at = now
            entry.save(update_fields=["attempts", "used_at"])
    if not ok:
        raise InvalidCode()
    return email


def _same(a, b):
    import hmac

    return hmac.compare_digest(a, b)


def make_registration_token(email):
    return signing.dumps({"email": email}, salt=REGISTER_SALT)


def read_registration_token(token):
    try:
        data = signing.loads(token, salt=REGISTER_SALT, max_age=settings.AUTH_REGISTRATION_TTL_SECONDS)
        return normalize_email(data["email"])
    except (signing.BadSignature, KeyError, TypeError):
        raise InvalidCode("Подтверждение e-mail устарело. Запросите код заново.") from None


def _new_refresh(session):
    import secrets

    raw = secrets.token_urlsafe(48)
    RefreshToken.objects.create(
        session=session,
        token_hash=pure.hash_token(raw),
        expires_at=timezone.now() + timedelta(days=settings.AUTH_REFRESH_TTL_DAYS),
    )
    return raw


def _payload(session, raw_refresh):
    return {
        "token_type": "Bearer",
        "access": signing.dumps({"sid": str(session.id)}, salt=ACCESS_SALT),
        "access_expires_in": settings.AUTH_ACCESS_TTL_SECONDS,
        "refresh": raw_refresh,
    }


def issue_tokens(user, device_name="", user_agent=""):
    session = Session.objects.create(
        user=user, device_name=(device_name or "")[:60], user_agent=(user_agent or "")[:200]
    )
    return _payload(session, _new_refresh(session))


def rotate_refresh(raw):
    """Обменивает токен обновления на новую пару. Повторное использование старого отзывает сессию."""
    now = timezone.now()
    payload = None
    with transaction.atomic():
        token = (
            RefreshToken.objects.select_for_update()
            .select_related("session__user")
            .filter(token_hash=pure.hash_token(raw or ""))
            .first()
        )
        if token is None or token.expires_at <= now:
            pass
        elif token.session.revoked_at is not None or not token.session.user.is_active:
            pass
        elif token.used_at is not None:
            token.session.revoked_at = now  # токен использовали повторно: сессия скомпрометирована
            token.session.save(update_fields=["revoked_at"])
        else:
            token.used_at = now
            token.save(update_fields=["used_at"])
            token.session.last_seen_at = now
            token.session.save(update_fields=["last_seen_at"])
            payload = _payload(token.session, _new_refresh(token.session))
    if payload is None:
        raise SessionInvalid()
    return payload


def revoke_session(session):
    if session.revoked_at is None:
        session.revoked_at = timezone.now()
        session.save(update_fields=["revoked_at"])


def revoke_all_sessions(user):
    return Session.objects.filter(user=user, revoked_at__isnull=True).update(revoked_at=timezone.now())


def consents_up_to_date(user):
    """Приняты ли актуальные версии всех обязательных документов (и не отозваны)."""
    from .models import Consent

    accepted = set(
        Consent.objects.filter(user=user, withdrawn_at__isnull=True).values_list("consent_type", "version")
    )
    return all((kind, version) in accepted for kind, version in settings.LEGAL_DOCUMENT_VERSIONS.items())


def request_account_deletion(user):
    """Немедленно закрывает аккаунт и все сессии; окончательное стирание — командой purge_expired."""
    now = timezone.now()
    user.is_active = False
    user.deletion_requested_at = now
    user.save(update_fields=["is_active", "deletion_requested_at"])
    revoke_all_sessions(user)
    return now + timedelta(days=settings.ACCOUNT_ERASURE_DAYS)


def restore_if_within_grace(user):
    """Если пользователь сам вошёл по коду в течение срока до стирания — отменяет удаление."""
    if user.is_active or user.deletion_requested_at is None:
        return False
    if timezone.now() - user.deletion_requested_at > timedelta(days=settings.ACCOUNT_ERASURE_DAYS):
        return False
    user.is_active = True
    user.deletion_requested_at = None
    user.save(update_fields=["is_active", "deletion_requested_at"])
    return True
