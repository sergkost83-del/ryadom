"""Проверка папки изображений приложения (только стандартная библиотека).

Сверяет файлы с описью manifest.json: все на месте, контрольные суммы совпадают, лишних файлов нет, размер в бюджете.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

TOTAL_BUDGET = 6_000_000      # байт на весь набор: приложение не должно раздуваться
FILE_BUDGET = 900_000         # байт на один файл
ALLOWED_EXTRA = {"manifest.json", "README.md"}


def verify(root: Path) -> list[str]:
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        return ["нет файла manifest.json (опись изображений)"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    problems: list[str] = []
    listed = set()
    total = 0
    for row in manifest.get("files", []):
        name = row["file"]
        listed.add(name)
        path = root / name
        if not path.exists():
            problems.append(f"{name}: файл из описи отсутствует")
            continue
        data = path.read_bytes()
        total += len(data)
        if hashlib.sha256(data).hexdigest() != row["sha256"]:
            problems.append(f"{name}: содержимое не совпадает с описью (файл изменён без пересборки)")
        if len(data) > FILE_BUDGET:
            problems.append(f"{name}: {len(data) // 1024} КБ — больше допустимых {FILE_BUDGET // 1024} КБ")
        if not name.isascii() or " " in name:
            problems.append(f"{name}: имя файла только латиницей и без пробелов")
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_file() and relative not in listed and relative not in ALLOWED_EXTRA:
            problems.append(f"{relative}: файла нет в описи (добавьте через tools/build_app_assets.py)")
    if total > TOTAL_BUDGET:
        problems.append(f"общий размер {total / 1e6:.1f} МБ больше бюджета {TOTAL_BUDGET / 1e6:.0f} МБ")
    return problems
