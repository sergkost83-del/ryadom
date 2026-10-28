#!/usr/bin/env python3
"""Комплексная локальная проверка проекта «РЯДОМ». Результат: reports/REPORT.md

Что проверяется здесь (без установки Django и без Docker):
  структура проекта, синтаксис Python, справочник ЖК/домов, версия, секреты в коде,
  окончания строк в .bat, проверки без базы данных.
Полные тесты с PostgreSQL: через Docker (если он установлен) или в GitHub Actions.
"""

from __future__ import annotations

import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "node_modules", "reports", "__pycache__", ".venv", "venv", "staticfiles"}
TEXT_SUFFIXES = {".py", ".md", ".yml", ".yaml", ".json", ".txt", ".bat", ".toml", ".ini", ".cfg", ".html",
                 ".js", ".ts", ".tsx", ".example", ".env"}

REQUIRED = [
    "VERSION", "README.md", "CHANGELOG.md", ".gitignore", ".gitattributes", ".env.example",
    "docker-compose.yml", "CHECK_ALL.bat", ".github/workflows/ci.yml",
    "backend/manage.py", "backend/requirements.txt", "backend/Dockerfile", "backend/pytest.ini",
    "backend/config/settings/base.py", "backend/config/settings/prod.py", "backend/config/urls.py",
    "backend/apps/identity/models.py", "backend/apps/identity/migrations/0001_initial.py",
    "backend/apps/communities/models.py", "backend/apps/communities/migrations/0001_initial.py",
    "backend/apps/communities/data/communities_seed.json",
    "docs/ARCHITECTURE.md", "docs/M1_ACCEPTANCE.md", "docs/DECISIONS.md", "docs/LEGACY_MAP.md",
    "docs/RELEASING.md", "design/tokens.json",
]

SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{30,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"(?i)\b(secret|token|passw(?:or)?d|api[_-]?key)\w*\s*[:=]\s*[\"'][^\"'\s]{12,}[\"']"),
]
ALLOW_MARK = "secret-scan: allow"


def iter_files():
    for path in ROOT.rglob("*"):
        if path.is_file() and not (set(path.relative_to(ROOT).parts) & SKIP_DIRS):
            yield path


def check_structure():
    missing = [p for p in REQUIRED if not (ROOT / p).exists()]
    return (not missing), [f"нет файла: {p}" for p in missing] or [f"все {len(REQUIRED)} обязательных файлов на месте"]


def check_syntax():
    bad, n = [], 0
    for path in iter_files():
        if path.suffix == ".py":
            n += 1
            try:
                py_compile.compile(str(path), cfile=os.path.join(tempfile.gettempdir(), "_ryadom.pyc"), doraise=True)
            except py_compile.PyCompileError as exc:
                bad.append(f"{path.relative_to(ROOT)}: {str(exc).strip().splitlines()[-1][:160]}")
    return (not bad), bad or [f"синтаксис верен в {n} файлах Python"]


def check_seed():
    sys.path.insert(0, str(ROOT / "backend"))
    try:
        from apps.communities.seed import load_seed_file

        records = load_seed_file()
    except Exception as exc:  # noqa: BLE001
        return False, [f"справочник некорректен: {exc}"]
    communities = {r.community_slug for r in records}
    return True, [f"справочник корректен: ЖК {len(communities)}, домов {len(records)}"]


def check_version():
    file_v = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    code = (ROOT / "backend/config/version.py").read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*"([^"]+)"', code)
    if not m or m.group(1) != file_v:
        return False, [f"версии расходятся: VERSION={file_v}, config/version.py={m.group(1) if m else '?'}"]
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if file_v not in changelog:
        return False, [f"версии {file_v} нет в CHANGELOG.md"]
    return True, [f"версия {file_v} совпадает в VERSION, коде и CHANGELOG"]


def check_secrets():
    found = []
    for path in iter_files():
        if path.name in {"local_check.py", "test_local_check.py"}:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {".env", ".env.example"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if ALLOW_MARK in line:
                continue
            if any(p.search(line) for p in SECRET_PATTERNS):
                found.append(f"{path.relative_to(ROOT)}:{number}: похоже на секрет")
    if (ROOT / ".env").exists():
        found.append("в папке проекта лежит .env — он не должен попасть в репозиторий (проверьте .gitignore)")
    return (not found), found or ["секретов в коде не найдено"]


def check_bat_line_endings():
    bad = [str(p.relative_to(ROOT)) for p in iter_files() if p.suffix == ".bat" and b"\r\n" not in p.read_bytes()]
    return (not bad), [f"{b}: нужны окончания строк CRLF" for b in bad] or ["все .bat-файлы в формате Windows (CRLF)"]


def run_unittests():
    """Быстрые тесты без базы. Два набора запускаются раздельно: у них одинаковое имя пакета tests."""
    runs = [
        ([sys.executable, "-m", "unittest", "discover", "-s", "tools/tests", "-t", "tools"], ROOT),
        ([sys.executable, "-m", "unittest", "tests.test_seed_parser", "tests.test_pure"], ROOT / "backend"),
    ]
    total, problems = 0, []
    for cmd, cwd in runs:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        output = (result.stdout + result.stderr).strip()
        match = re.search(r"Ran (\d+) tests?", output)
        total += int(match.group(1)) if match else 0
        if result.returncode != 0:
            problems.append("набор тестов упал: " + " ".join(cmd[2:]))
            problems += output.splitlines()[-8:]
    return (not problems), problems or [f"{total} быстрых тестов без базы данных пройдено"]


def run_full_tests():
    if os.environ.get("CI"):
        return None, ["пропущено: в CI полные тесты выполняются отдельным шагом"]
    if not shutil.which("docker"):
        return None, ["пропущено: Docker не установлен. Полные тесты с PostgreSQL выполняет GitHub Actions"]
    probe = subprocess.run(["docker", "info"], capture_output=True, text=True)
    if probe.returncode != 0:
        return None, ["пропущено: Docker установлен, но не запущен. Запустите Docker Desktop и повторите"]
    cmd = ["docker", "compose", "--profile", "test", "run", "--rm", "--build", "tests"]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = (result.stdout + result.stderr).strip().splitlines()[-25:]
    if result.returncode == 0:
        return True, ["полные тесты с PostgreSQL пройдены (Docker)"] + tail[-3:]
    return False, ["полные тесты упали:"] + tail


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    steps = [
        ("Структура проекта", check_structure),
        ("Синтаксис Python", check_syntax),
        ("Справочник ЖК и домов", check_seed),
        ("Версия", check_version),
        ("Секреты в коде", check_secrets),
        ("Файлы .bat", check_bat_line_endings),
        ("Быстрые тесты без базы", run_unittests),
        ("Полные тесты с PostgreSQL", run_full_tests),
    ]
    out = ["# РЯДОМ: локальная проверка", f"Дата: {datetime.now():%Y-%m-%d %H:%M}", ""]
    failed = skipped = 0
    for name, fn in steps:
        try:
            status, details = fn()
        except Exception as exc:  # noqa: BLE001
            status, details = False, [f"сбой проверки: {exc}"]
        icon = "✅" if status is True else ("⏭" if status is None else "❌")
        failed += status is False
        skipped += status is None
        out.append(f"## {icon} {name}")
        out += [f"- {d}" for d in details]
        out.append("")
    verdict = "❌ ЕСТЬ ОШИБКИ — покажите этот отчёт" if failed else "✅ ВСЁ, ЧТО ПРОВЕРЯЕТСЯ ЛОКАЛЬНО, В ПОРЯДКЕ"
    out.append(f"**ИТОГ: {verdict}**")
    if skipped and not failed:
        out.append("")
        out.append("Пропущенное проверит GitHub Actions при отправке изменений.")
    text = "\n".join(out) + "\n"
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "REPORT.md").write_text(text, encoding="utf-8")
    print(text)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
