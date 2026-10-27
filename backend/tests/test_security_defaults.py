import pytest
from django.conf import settings
from rest_framework.test import APIClient


def test_api_denies_by_default():
    assert settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] == ["rest_framework.permissions.IsAuthenticated"]


def test_debug_is_off_in_tests_and_cookies_are_httponly():
    assert settings.DEBUG is False
    assert settings.SESSION_COOKIE_HTTPONLY is True


def test_request_body_is_limited():
    assert settings.DATA_UPLOAD_MAX_MEMORY_SIZE <= 1_048_576


@pytest.mark.django_db
def test_admin_requires_login(client):
    response = client.get("/" + settings.ADMIN_URL)
    assert response.status_code == 302
    assert "login" in response["Location"]


def test_schema_is_not_public_in_non_debug():
    response = APIClient().get("/api/v1/schema/")
    assert response.status_code == 404
