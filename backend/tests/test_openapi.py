import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


def test_openapi_schema_is_valid_and_has_no_warnings(tmp_path):
    target = tmp_path / "schema.yml"
    try:
        call_command("spectacular", "--validate", "--fail-on-warn", "--file", str(target))
    except (CommandError, SystemExit) as exc:
        pytest.fail(f"OpenAPI-схема содержит предупреждения или ошибки: {exc}")
    text = target.read_text(encoding="utf-8")
    assert "/api/v1/auth/code/request/" in text
    assert "bearerAuth" in text
