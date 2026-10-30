"""Приглашения и смена адреса. Все изменения членства проходят через эти функции."""

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.identity import totp

from .models import AddressChangeRequest, HouseInvite, Membership


class InvalidInvite(APIException):
    status_code = 400
    default_detail = "Код приглашения недействителен или истёк."
    default_code = "invalid_invite"


def _hash(code):
    return totp.hash_secret_code(settings.SECRET_KEY, "invite", code)


def new_invite_secret():
    """Новый код приглашения и его хэш для хранения."""
    code = totp.generate_group_code(2, 4)
    return code, _hash(code)


def create_invite(*, created_by, building, expires_in_days=None, note=""):
    """Создаёт приглашение. Открытый код возвращается один раз и нигде не хранится."""
    days = expires_in_days or settings.INVITE_DEFAULT_DAYS
    days = min(max(int(days), 1), settings.INVITE_MAX_DAYS)
    code, code_hash = new_invite_secret()
    invite = HouseInvite.objects.create(
        building=building,
        code_hash=code_hash,
        expires_at=timezone.now() + timedelta(days=days),
        note=note,
        created_by=created_by,
    )
    return invite, code


def find_valid_invite(code):
    if not totp.normalize_code(code):
        return None
    invite = HouseInvite.objects.select_related("building__street__community").filter(code_hash=_hash(code)).first()
    return invite if invite is not None and invite.is_valid else None


def consume_invite(invite, user):
    """Погашает приглашение. При гонке двух запросов второй получает отказ."""
    with transaction.atomic():
        locked = HouseInvite.objects.select_for_update().get(pk=invite.pk)
        if not locked.is_valid:
            raise InvalidInvite()
        locked.used_at = timezone.now()
        locked.used_by = user
        locked.save(update_fields=["used_at", "used_by", "updated_at"])
    return locked


def revoke_invite(invite, by):
    with transaction.atomic():
        locked = HouseInvite.objects.select_for_update().get(pk=invite.pk)
        if locked.used_at is not None or locked.revoked_at is not None:
            return False
        locked.revoked_at = timezone.now()
        locked.revoked_by = by
        locked.save(update_fields=["revoked_at", "revoked_by", "updated_at"])
    return True


def apply_membership(user, building, confirmed_by):
    """Завершает прежний активный адрес и закрепляет новый подтверждённым."""
    now = timezone.now()
    with transaction.atomic():
        Membership.objects.filter(user=user, status__in=Membership.ACTIVE_STATUSES).update(
            status=Membership.STATUS_ENDED, valid_to=now
        )
        return Membership.objects.create(
            user=user,
            building=building,
            status=Membership.STATUS_CONFIRMED,
            confirmed_by=confirmed_by,
            confirmed_at=now,
        )


def current_building(user):
    membership = user.memberships.filter(status__in=Membership.ACTIVE_STATUSES).select_related("building").first()
    return membership.building if membership else None


def approve_address_change(req, decided_by, comment=""):
    with transaction.atomic():
        locked = AddressChangeRequest.objects.select_for_update().get(pk=req.pk)
        if locked.status != AddressChangeRequest.STATUS_PENDING:
            return None
        membership = apply_membership(locked.user, locked.to_building, decided_by)
        locked.status = AddressChangeRequest.STATUS_APPROVED
        locked.decided_by = decided_by
        locked.decided_at = timezone.now()
        locked.comment = comment[:200]
        locked.save(update_fields=["status", "decided_by", "decided_at", "comment", "updated_at"])
    return membership


def reject_address_change(req, decided_by, comment=""):
    with transaction.atomic():
        locked = AddressChangeRequest.objects.select_for_update().get(pk=req.pk)
        if locked.status != AddressChangeRequest.STATUS_PENDING:
            return False
        locked.status = AddressChangeRequest.STATUS_REJECTED
        locked.decided_by = decided_by
        locked.decided_at = timezone.now()
        locked.comment = comment[:200]
        locked.save(update_fields=["status", "decided_by", "decided_at", "comment", "updated_at"])
    return True
