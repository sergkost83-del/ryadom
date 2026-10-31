"""Упрощённая замена части проверок ruff (F821 необъявленные имена, F401 лишние импорты, E501 длинные строки).

Нужна, чтобы такие ошибки находились локально и в быстрой проверке, до запуска полного CI.
"""

from __future__ import annotations

import ast
import builtins
from pathlib import Path

MAX_LINE = 120
BUILTINS = set(dir(builtins)) | {"__file__", "__name__"}


def _stores(node):
    names = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            names.add(n.id)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(n.name)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                names.add((a.asname or a.name).split(".")[0])
        elif isinstance(n, ast.ExceptHandler) and n.name:
            names.add(n.name)
        elif isinstance(n, ast.arg):
            names.add(n.arg)
    return names


def undefined_names(tree):
    problems = []
    module_scope = _stores(tree) | BUILTINS

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.scopes = [module_scope]

        def visit_FunctionDef(self, node):
            self.scopes.append(_stores(node))
            for child in node.body:
                self.visit(child)
            for decorator in node.decorator_list:
                self.visit(decorator)
            self.scopes.pop()

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Lambda(self, node):
            self.scopes.append({a.arg for a in node.args.args})
            self.visit(node.body)
            self.scopes.pop()

        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Load) and not any(node.id in s for s in self.scopes):
                problems.append((node.lineno, f"необъявленное имя «{node.id}»"))

    Visitor().visit(tree)
    return problems


def unused_imports(tree, lines, is_init):
    if is_init:
        return []
    imported = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                imported[(a.asname or a.name).split(".")[0]] = n.lineno
        elif isinstance(n, ast.ImportFrom):
            for a in n.names:
                if a.name != "*" and n.module != "__future__":
                    imported[a.asname or a.name] = n.lineno
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    return [
        (line, f"неиспользуемый импорт «{name}»")
        for name, line in imported.items()
        if name not in used and "noqa" not in lines[line - 1]
    ]


def check_file(path: Path):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    tree = ast.parse(text)
    problems = undefined_names(tree) + unused_imports(tree, lines, path.name == "__init__.py")
    for number, line in enumerate(lines, 1):
        if len(line) > MAX_LINE and "noqa" not in line:
            problems.append((number, f"строка длиннее {MAX_LINE} символов ({len(line)})"))
    return sorted(problems)


def check_tree(root: Path):
    found = []
    for path in sorted(root.rglob("*.py")):
        if "migrations" in path.parts or "staticfiles" in path.parts:
            continue
        for line, message in check_file(path):
            found.append(f"{path.relative_to(root.parent)}:{line}: {message}")
    return found
