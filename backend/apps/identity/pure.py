"""Чистые функции без Django: коды, хэши, разбор IP, проверка имени и телефона. Проверяются быстрыми тестами."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import unicodedata

PHONE_RE = re.compile(r"^\+?[0-9]{10,15}$")


def generate_code() -> str:
    """Шестизначный код из криптостойкого генератора."""
    return f"{secrets.randbelow(10**6):06d}"


def hash_code(secret: str, email: str, code: str) -> str:
    """HMAC-SHA256 с секретом сервера: код нельзя подобрать по базе без секрета."""
    return hmac.new(secret.encode(), f"login-code:{email}:{code}".encode(), hashlib.sha256).hexdigest()


def hash_token(raw: str) -> str:
    """Токены обновления случайны и длинны, поэтому достаточно SHA-256."""
    return hashlib.sha256(raw.encode()).hexdigest()


def hash_key(scope: str, value: str) -> str:
    """Ключ ограничения частоты: персональные данные (e-mail, IP) в открытом виде не храним."""
    return hashlib.sha256(f"{scope}:{value}".encode()).hexdigest()


def extract_client_ip(remote_addr: str | None, forwarded_for: str | None, trusted_proxies: int = 0) -> str:
    """IP клиента. X-Forwarded-For учитывается только от доверенных прокси (их число задаётся настройкой)."""
    if trusted_proxies > 0 and forwarded_for:
        parts = [p.strip() for p in forwarded_for.split(",") if p.strip()]
        if len(parts) >= trusted_proxies:
            return parts[-trusted_proxies]
    return remote_addr or "unknown"


def clean_display_name(value: str) -> str:
    """Имя: 2–60 символов, без угловых скобок и управляющих символов."""
    name = " ".join((value or "").split())
    if len(name) < 2 or len(name) > 60:
        raise ValueError("Имя должно быть от 2 до 60 символов.")
    if "<" in name or ">" in name:
        raise ValueError("Имя не должно содержать символов < и >.")
    if any(unicodedata.category(ch).startswith("C") for ch in name):
        raise ValueError("Имя содержит недопустимые символы.")
    return name


def clean_phone(value: str) -> str:
    """Телефон необязателен. Пустая строка допустима, иначе 10–15 цифр, можно с плюсом."""
    raw = re.sub(r"[\s\-()]", "", value or "")
    if not raw:
        return ""
    if not PHONE_RE.match(raw):
        raise ValueError("Телефон: от 10 до 15 цифр, можно с плюсом в начале.")
    return raw
