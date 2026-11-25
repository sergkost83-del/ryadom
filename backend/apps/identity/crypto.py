"""Шифрование секретов в базе (секрет 2FA). Ключи хранятся вне базы, в окружении сервера.

Первый ключ в FIELD_ENCRYPTION_KEYS шифрует, остальные только расшифровывают: так ключ меняют без потери данных.
"""

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

PREFIX = "enc1:"


class DecryptionError(Exception):
    pass


def _cipher():
    keys = list(settings.FIELD_ENCRYPTION_KEYS)
    if not keys:
        raise ImproperlyConfigured("FIELD_ENCRYPTION_KEYS не задан.")
    return MultiFernet([Fernet(key.encode() if isinstance(key, str) else key) for key in keys])


def encrypt(plain):
    return PREFIX + _cipher().encrypt(plain.encode()).decode()


def decrypt(value):
    if not value.startswith(PREFIX):
        return value  # секрет, записанный до включения шифрования; переписывается миграцией
    try:
        return _cipher().decrypt(value[len(PREFIX):].encode()).decode()
    except InvalidToken:
        raise DecryptionError("Секрет не расшифровать: неверный ключ шифрования.") from None
