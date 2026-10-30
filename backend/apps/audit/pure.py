"""Очистка данных перед записью в журнал аудита: секреты в журнал не попадают. Без Django."""

from __future__ import annotations

FORBIDDEN_PARTS = ("password", "passwd", "code", "token", "secret", "hash", "otp", "backup", "key")
MAX_VALUE = 200


def _value(value):
    if isinstance(value, (list, tuple)):
        return [_value(v) for v in value]
    text = "" if value is None else str(value)
    return text if len(text) <= MAX_VALUE else text[:MAX_VALUE] + "…"


def sanitize_changes(changes, exclude=()):
    """Оставляет только безопасные поля: имена с password/code/token/secret/hash/otp/backup/key отбрасываются."""
    cleaned = {}
    for name, value in (changes or {}).items():
        lowered = str(name).lower()
        if name in exclude or any(part in lowered for part in FORBIDDEN_PARTS):
            continue
        cleaned[str(name)] = _value(value)
    return cleaned
