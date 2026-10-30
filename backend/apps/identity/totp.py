"""TOTP (RFC 6238) и одноразовые коды. Только стандартная библиотека, без Django: проверяется быстрыми тестами."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

PERIOD = 30
DIGITS = 6
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # без похожих символов: 0/O, 1/I


def generate_secret() -> str:
    """Секрет в Base32 (160 бит) — стандарт для Яндекс Ключа, Google Authenticator и других приложений."""
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _key(secret_b32: str) -> bytes:
    secret = secret_b32.strip().replace(" ", "").upper()
    return base64.b32decode(secret + "=" * (-len(secret) % 8))


def hotp(secret_b32: str, counter: int, digits: int = DIGITS) -> str:
    digest = hmac.new(_key(secret_b32), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % (10**digits)
    return str(number).zfill(digits)


def current_step(now: float | None = None, period: int = PERIOD) -> int:
    return int((time.time() if now is None else now) // period)


def totp_now(secret_b32: str, now: float | None = None) -> str:
    return hotp(secret_b32, current_step(now))


def verify_totp(secret_b32: str, code: str, now: float | None = None, window: int = 1, last_step: int | None = None):
    """Возвращает номер принятого шага или None. Шаги не позже last_step отвергаются (защита от повтора кода)."""
    code = (code or "").strip().replace(" ", "")
    if len(code) != DIGITS or not code.isdigit():
        return None
    step_now = current_step(now)
    for step in range(step_now - window, step_now + window + 1):
        if last_step is not None and step <= last_step:
            continue
        if hmac.compare_digest(hotp(secret_b32, step), code):
            return step
    return None


def provisioning_uri(secret_b32: str, account: str, issuer: str = "РЯДОМ") -> str:
    label = quote(f"{issuer}:{account}", safe="")
    return (
        f"otpauth://totp/{label}?secret={secret_b32}&issuer={quote(issuer, safe='')}"
        f"&algorithm=SHA1&digits={DIGITS}&period={PERIOD}"
    )


def generate_group_code(groups: int, size: int) -> str:
    """Случайный код вида XXXXX-XXXXX из безопасного алфавита."""
    return "-".join("".join(secrets.choice(CODE_ALPHABET) for _ in range(size)) for _ in range(groups))


def normalize_code(value: str) -> str:
    return "".join((value or "").upper().replace("-", "").split())


def hash_secret_code(server_secret: str, purpose: str, code: str) -> str:
    """HMAC-хэш одноразового кода (резервного или приглашения). В базе хранится только он."""
    return hmac.new(server_secret.encode(), f"{purpose}:{normalize_code(code)}".encode(), hashlib.sha256).hexdigest()
