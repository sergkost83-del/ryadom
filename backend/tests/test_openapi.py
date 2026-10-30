import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


def test_openapi_schema_is_valid_and_has_no_warnings(tmp_path, capfd):
    target = tmp_path / "schema.yml"
    try:
        call_command("spectacular", "--validate", "--fail-on-warn", "--file", str(target))
    except (CommandError, SystemExit):
        captured = capfd.readouterr()
        lines = [x.strip() for x in (captured.err + captured.out).splitlines() if "Warning" in x or "Error" in x]
        pytest.fail("OpenAPI-схема: предупреждения. " + " || ".join(lines)[:1500])
    text = target.read_text(encoding="utf-8")
    assert "/api/v1/auth/code/request/" in text
    assert "bearerAuth" in text
