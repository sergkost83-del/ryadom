"""Очистка текста сообщения. Без Django: проверяется быстрыми тестами."""

from __future__ import annotations

import unicodedata

MAX_LENGTH = 1000


def clean_body(value: str) -> str:
    """Убирает управляющие символы (кроме переноса строки) и пробелы по краям. Пустое и длинное отвергает."""
    kept = "".join(ch for ch in (value or "") if ch == "\n" or not unicodedata.category(ch).startswith("C"))
    text = kept.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        raise ValueError("Сообщение не может быть пустым.")
    if len(text) > MAX_LENGTH:
        raise ValueError(f"Сообщение длиннее {MAX_LENGTH} символов.")
    return text
