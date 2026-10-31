#!/usr/bin/env python3
"""Превращает отчёт JUnit в короткую сводку на русском (REPORT.md и сводка запуска GitHub Actions)."""

from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def summarize(junit_path: str) -> tuple[str, bool]:
    path = Path(junit_path)
    if not path.exists():
        text = "## Тесты\n❌ Тесты не запустились: упал один из предыдущих шагов.\n"
        for filename, title in (("ruff.txt", "Линтер"), ("migrations.txt", "Проверка миграций")):
            extra = path.parent / filename
            if extra.exists():
                tail = [line for line in extra.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
                if tail and "All checks passed" not in tail[-1] and "No changes detected" not in tail[-1]:
                    text += f"\n### {title}\n```\n" + "\n".join(tail[-30:]) + "\n```\n"
        return text, False
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    total = sum(int(s.get("tests", 0)) for s in suites)
    failures = sum(int(s.get("failures", 0)) for s in suites)
    errors = sum(int(s.get("errors", 0)) for s in suites)
    skipped = sum(int(s.get("skipped", 0)) for s in suites)
    seconds = sum(float(s.get("time", 0)) for s in suites)
    ok = total > 0 and failures == 0 and errors == 0
    lines = ["## Тесты", f"{'✅ Все тесты пройдены' if ok else '❌ Есть ошибки'}", ""]
    lines.append(f"- Всего: **{total}**, упало: **{failures}**, ошибок: **{errors}**, пропущено: {skipped}")
    lines.append(f"- Время: {seconds:.1f} с")
    bad = []
    for case in root.iter("testcase"):
        for kind in ("failure", "error"):
            node = case.find(kind)
            if node is not None:
                message = " ".join((node.get("message") or (node.text or "")).split())
                bad.append((f"{case.get('classname', '')}::{case.get('name', '')}", message[:1200]))
    if total == 0:
        lines.append("- ⚠ Не выполнено ни одного теста.")
    if bad:
        lines += ["", "### Упавшие тесты"]
        for name, message in bad[:30]:
            lines.append(f"- `{name}` — {message}")
        if len(bad) > 30:
            lines.append(f"- … и ещё {len(bad) - 30}")
    return "\n".join(lines) + "\n", ok


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Использование: ci_summary.py junit.xml REPORT.md", file=sys.stderr)
        return 2
    text, ok = summarize(argv[1])
    Path(argv[2]).parent.mkdir(parents=True, exist_ok=True)
    Path(argv[2]).write_text(text, encoding="utf-8")
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as fh:
            fh.write(text)
    print(text)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
