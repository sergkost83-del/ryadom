import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ci_summary import summarize  # noqa: E402

GOOD = """<testsuites><testsuite tests="3" failures="0" errors="0" skipped="1" time="1.5">
<testcase classname="t.A" name="test_a"/><testcase classname="t.A" name="test_b"/><testcase classname="t.A" name="test_c"><skipped/></testcase>
</testsuite></testsuites>"""
BAD = """<testsuite tests="2" failures="1" errors="0" skipped="0" time="0.2">
<testcase classname="t.B" name="test_x"><failure message="assert 1 == 2">trace</failure></testcase>
<testcase classname="t.B" name="test_y"/></testsuite>"""


def _write(text):
    f = tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False, encoding="utf-8")
    f.write(text)
    f.close()
    return f.name


class SummaryTests(unittest.TestCase):
    def test_all_passed(self):
        text, ok = summarize(_write(GOOD))
        self.assertTrue(ok)
        self.assertIn("Всего: **3**", text)

    def test_failure_listed(self):
        text, ok = summarize(_write(BAD))
        self.assertFalse(ok)
        self.assertIn("t.B::test_x", text)
        self.assertIn("assert 1 == 2", text)

    def test_missing_report_is_failure(self):
        text, ok = summarize("/nonexistent/junit.xml")
        self.assertFalse(ok)
        self.assertIn("не создан", text)

    def test_zero_tests_is_failure(self):
        _, ok = summarize(_write('<testsuite tests="0" failures="0" errors="0" skipped="0" time="0"/>'))
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
