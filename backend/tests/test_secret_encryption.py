import pytest
from django.db import connection

from apps.identity import crypto, totp, twofactor
from apps.identity.models import User

pytestmark = pytest.mark.django_db

OLD = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="  # secret-scan: allow
NEW = "MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE="  # secret-scan: allow


def test_secret_is_stored_encrypted_and_never_in_plain_text():
    user = User.objects.create_user("enc@example.com", is_staff=True)
    device = twofactor.pending_device(user)
    plain = device.plain_secret
    assert len(plain) == 32
    with connection.cursor() as cursor:
        cursor.execute("SELECT secret FROM identity_totpdevice WHERE id = %s", [device.pk])
        stored = cursor.fetchone()[0]
    assert stored.startswith("enc1:") and plain not in stored


def test_totp_still_works_with_encrypted_secret():
    user = User.objects.create_user("work@example.com", is_staff=True)
    device = twofactor.pending_device(user)
    assert twofactor.confirm_device(user, totp.totp_now(device.plain_secret))
    assert twofactor.verify_code(user, totp.hotp(device.plain_secret, totp.current_step() + 1)) == "totp"


def test_legacy_plain_secret_is_still_readable():
    assert crypto.decrypt("JBSWY3DPEHPK3PXP") == "JBSWY3DPEHPK3PXP"


def test_key_rotation_keeps_old_data_readable(settings):
    settings.FIELD_ENCRYPTION_KEYS = [OLD]
    stored = crypto.encrypt("SECRETVALUE")
    settings.FIELD_ENCRYPTION_KEYS = [NEW, OLD]
    assert crypto.decrypt(stored) == "SECRETVALUE"
    assert crypto.decrypt(crypto.encrypt("OTHER")) == "OTHER"
    settings.FIELD_ENCRYPTION_KEYS = [NEW]
    with pytest.raises(crypto.DecryptionError):
        crypto.decrypt(stored)


def test_missing_key_is_a_configuration_error(settings):
    from django.core.exceptions import ImproperlyConfigured

    settings.FIELD_ENCRYPTION_KEYS = []
    with pytest.raises(ImproperlyConfigured):
        crypto.encrypt("x")
