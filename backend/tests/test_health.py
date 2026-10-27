import pytest

from config.version import __version__

pytestmark = pytest.mark.django_db


def test_health_ok(client):
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__, "database": "ok"}


def test_health_does_not_leak_internal_details(client):
    body = client.get("/api/v1/health/").content.decode()
    for word in ("postgres", "password", "SECRET", "/app", "settings"):
        assert word.lower() not in body.lower()
