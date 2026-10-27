from pathlib import Path

import pytest

from config.version import __version__


def test_version_file_matches_code():
    version_file = Path(__file__).resolve().parents[2] / "VERSION"
    if not version_file.exists():
        pytest.skip("VERSION отсутствует (запуск вне репозитория)")
    assert version_file.read_text(encoding="utf-8").strip() == __version__
