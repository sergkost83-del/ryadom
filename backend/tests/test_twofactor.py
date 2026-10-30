import json
import re

import pytest
from django.core.management import call_command
from django.test import Client

from apps.audit.models import AuditLog
from apps.identity import totp
from apps.identity.models import BackupCode, TOTPDevice, User
from tests.helpers import make_staff

pytestmark = pytest.mark.django_db

BACKUP_RE = re.compile(r"\b[A-Z2-9]{5}-[A-Z2-9]{5}\b")


@pytest.fixture
def boss(db):
    return make_staff("boss@example.com", superuser=True)


def enroll(client, user):
    """Проходит настройку защиты. Возвращает (секрет, резервные коды)."""
    client.force_login(user)
    assert client.get("/admin/2fa/setup/").status_code == 200
    secret = TOTPDevice.objects.get(user=user).secret
    response = client.post("/admin/2fa/setup/", {"code": totp.totp_now(secret)})
    assert response.status_code == 200
    return secret, BACKUP_RE.findall(response.content.decode())


def fresh_client(user):
    client = Client()
    client.force_login(user)
    return client


def next_code(secret):
    """Код следующего шага: не совпадает с уже использованным, но входит в допустимое окно."""
    return totp.hotp(secret, totp.current_step() + 1)


def test_unenrolled_staff_is_sent_to_setup(client, boss):
    client.force_login(boss)
    response = client.get("/admin/")
    assert response.status_code == 302 and "/admin/2fa/setup/" in response["Location"]


def test_enrollment_shows_secret_then_backup_codes_once(client, boss):
    client.force_login(boss)
    page = client.get("/admin/2fa/setup/").content.decode()
    device = TOTPDevice.objects.get(user=boss)
    assert device.secret in page and device.confirmed_at is None
    wrong = client.post("/admin/2fa/setup/", {"code": "000000"})
    assert wrong.status_code == 200 and "Код не подошёл" in wrong.content.decode()
    assert TOTPDevice.objects.get(user=boss).confirmed_at is None
    right = client.post("/admin/2fa/setup/", {"code": totp.totp_now(device.secret)})
    codes = BACKUP_RE.findall(right.content.decode())
    assert len(set(codes)) == 10
    assert TOTPDevice.objects.get(user=boss).confirmed_at is not None
    assert BackupCode.objects.filter(user=boss).count() == 10
    assert client.get("/admin/").status_code == 200


def test_setup_page_keeps_the_same_secret_on_reload(client, boss):
    client.force_login(boss)
    client.get("/admin/2fa/setup/")
    first = TOTPDevice.objects.get(user=boss).secret
    client.get("/admin/2fa/setup/")
    assert TOTPDevice.objects.get(user=boss).secret == first


def test_new_session_requires_code_and_rejects_replay(client, boss):
    secret, _ = enroll(client, boss)
    other = fresh_client(boss)
    response = other.get("/admin/")
    assert response.status_code == 302 and "/admin/2fa/verify/" in response["Location"]
    code = next_code(secret)
    assert other.post("/admin/2fa/verify/", {"code": code}).status_code == 302
    assert other.get("/admin/").status_code == 200
    thief = fresh_client(boss)
    assert thief.post("/admin/2fa/verify/", {"code": code}).status_code == 200
    assert thief.get("/admin/").status_code == 302


def test_backup_code_works_once_and_is_stored_hashed(client, boss):
    _, codes = enroll(client, boss)
    one = fresh_client(boss)
    assert one.post("/admin/2fa/verify/", {"code": codes[0].lower()}).status_code == 302
    assert one.get("/admin/").status_code == 200
    again = fresh_client(boss)
    assert again.post("/admin/2fa/verify/", {"code": codes[0]}).status_code == 200
    assert again.get("/admin/").status_code == 302
    assert BackupCode.objects.filter(user=boss, used_at__isnull=False).count() == 1
    stored = set(BackupCode.objects.values_list("code_hash", flat=True))
    assert not stored & {c.replace("-", "") for c in codes} and not stored & set(codes)


def test_wrong_codes_are_rate_limited(client, boss, settings):
    secret, _ = enroll(client, boss)
    attacker = fresh_client(boss)
    # одна попытка уже потрачена на настройку защиты
    for _ in range(settings.ADMIN_2FA_ATTEMPTS_PER_15_MIN - 1):
        assert "Код не подошёл" in attacker.post("/admin/2fa/verify/", {"code": "111111"}).content.decode()
    blocked = attacker.post("/admin/2fa/verify/", {"code": next_code(secret)})
    assert "Слишком много попыток" in blocked.content.decode()
    assert attacker.get("/admin/").status_code == 302


def test_regenerating_backup_codes_invalidates_old_ones(client, boss):
    _, old_codes = enroll(client, boss)
    response = client.post("/admin/2fa/backup-codes/regenerate/")
    new_codes = BACKUP_RE.findall(response.content.decode())
    assert len(new_codes) == 10 and not set(new_codes) & set(old_codes)
    victim = fresh_client(boss)
    assert victim.post("/admin/2fa/verify/", {"code": old_codes[0]}).status_code == 200
    assert victim.get("/admin/").status_code == 302


def test_unverified_session_cannot_regenerate_codes(client, boss):
    enroll(client, boss)
    other = fresh_client(boss)
    response = other.post("/admin/2fa/backup-codes/regenerate/")
    assert response.status_code == 302 and "verify" in response["Location"]


def test_open_redirect_is_blocked(client, boss):
    secret, _ = enroll(client, boss)
    other = fresh_client(boss)
    response = other.post("/admin/2fa/verify/", {"code": next_code(secret), "next": "https://evil.example/"})
    assert response.status_code == 302 and "evil.example" not in response["Location"]


def test_residents_and_anonymous_are_not_affected(client, db):
    assert client.get("/admin/").status_code == 302 and "login" in client.get("/admin/")["Location"]
    resident = User.objects.create_user("res@example.com")
    client.force_login(resident)
    response = client.get("/admin/")
    assert response.status_code == 302 and "2fa" not in response["Location"]


def test_command_resets_protection_and_is_logged(client, boss):
    enroll(client, boss)
    call_command("reset_2fa", "BOSS@example.com")
    assert not TOTPDevice.objects.filter(user=boss).exists()
    assert not BackupCode.objects.filter(user=boss).exists()
    assert AuditLog.objects.filter(action="staff.2fa_reset_cli").exists()
    assert fresh_client(boss).get("/admin/")["Location"].startswith("/admin/2fa/setup/")


def test_events_are_audited_without_any_codes(client, boss):
    secret, codes = enroll(client, boss)
    attacker = fresh_client(boss)
    attacker.post("/admin/2fa/verify/", {"code": "222222"})
    attacker.post("/admin/2fa/verify/", {"code": next_code(secret)})
    actions = set(AuditLog.objects.values_list("action", flat=True))
    assert {"staff.2fa_enrolled", "staff.2fa_failed", "staff.2fa_verified"} <= actions
    dump = json.dumps(list(AuditLog.objects.values("action", "changes", "note", "object_id")), default=str)
    for secret_value in [secret, "222222", next_code(secret), *codes]:
        assert secret_value not in dump
