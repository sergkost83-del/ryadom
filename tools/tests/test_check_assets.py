import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_assets  # noqa: E402


def make_set(root, files):
    rows = []
    for name, data in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        rows.append({"file": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    (root / "manifest.json").write_text(json.dumps({"files": rows}), encoding="utf-8")


class AssetCheckTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())

    def test_consistent_set_passes(self):
        make_set(self.folder, {"icons/a.webp": b"1" * 100, "brand/b.png": b"2" * 50})
        self.assertEqual(check_assets.verify(self.folder), [])

    def test_changed_file_is_found(self):
        make_set(self.folder, {"icons/a.webp": b"1" * 100})
        (self.folder / "icons/a.webp").write_bytes(b"changed")
        self.assertTrue(any("не совпадает" in p for p in check_assets.verify(self.folder)))

    def test_missing_and_extra_files_are_found(self):
        make_set(self.folder, {"icons/a.webp": b"1", "icons/b.webp": b"2"})
        (self.folder / "icons/b.webp").unlink()
        (self.folder / "icons/stray.png").write_bytes(b"x")
        found = " ".join(check_assets.verify(self.folder))
        self.assertIn("отсутствует", found)
        self.assertIn("нет в описи", found)

    def test_budget_and_names(self):
        make_set(self.folder, {"big.webp": b"0" * (check_assets.FILE_BUDGET + 1), "плохое имя.png": b"1"})
        found = " ".join(check_assets.verify(self.folder))
        self.assertIn("допустимых", found)
        self.assertIn("латиницей", found)

    def test_missing_manifest(self):
        self.assertTrue(any("manifest" in p for p in check_assets.verify(self.folder)))


if __name__ == "__main__":
    unittest.main()
