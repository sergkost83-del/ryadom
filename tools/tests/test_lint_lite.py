import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lint_lite import check_file  # noqa: E402


def _check(code, name="mod.py"):
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / name
        path.write_text(code, encoding="utf-8")
        return [message for _, message in check_file(path)]


class LintLiteTests(unittest.TestCase):
    def test_clean_code_passes(self):
        self.assertEqual(_check("import os\n\n\ndef f(x):\n    y = x + 1\n    return os.sep + str(y)\n"), [])

    def test_undefined_name_is_found(self):
        found = _check("def f(a):\n    if invite:\n        return a\n")
        self.assertTrue(any("invite" in m for m in found))

    def test_names_from_other_scopes_are_fine(self):
        code = "import os\n\nclass A:\n    x = 1\n\n    def m(self, p):\n        return [i for i in p] + [os.sep]\n"
        self.assertEqual(_check(code), [])

    def test_unused_import_is_found_but_noqa_and_init_are_ignored(self):
        self.assertTrue(any("json" in m for m in _check("import json\n")))
        self.assertEqual(_check("import json  # noqa: F401\n"), [])
        self.assertEqual(_check("import json\n", name="__init__.py"), [])

    def test_future_import_is_ignored(self):
        self.assertEqual(_check("from __future__ import annotations\n"), [])

    def test_long_line_is_found(self):
        self.assertTrue(any("длиннее" in m for m in _check("x = '" + "a" * 130 + "'\n")))


if __name__ == "__main__":
    unittest.main()
