from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.identity.models import AuthThrottle, EmailLoginCode, RefreshToken, Session
from tests.helpers import request_code, signup

pytestmark = pytest.mark.django_db


def test_directory_is_public_and_complete(api, seeded):
    response = api.get("/api/v1/communities/")
    assert response.status_code == 200
    communities = response.json()["communities"]
    assert len(communities) == 3
    buildings = [b for c in communities for s in c["streets"] for b in s["buildings"]]
    assert len(buildings) == 23
    assert all(set(b) == {"id", "label"} for b in buildings)


def test_legal_versions_are_public(api):
    body = api.get("/api/v1/legal/current/").json()
    assert body["minimum_age"] == 18
    assert set(body["documents"]) == {"privacy_policy", "personal_data"}


def test_purge_removes_only_stale_records(api, building):
    request_code(api, "old@example.com")
    request_code(api, "fresh@example.com")
    EmailLoginCode.objects.filter(email="old@example.com").update(created_at=timezone.now() - timedelta(days=2))
    AuthThrottle.objects.update(window_start=timezone.now() - timedelta(days=2))
    tokens = signup(api, "purge@example.com", building)["tokens"]
    assert tokens
    RefreshToken.objects.update(expires_at=timezone.now() - timedelta(days=1))
    Session.objects.update(revoked_at=timezone.now() - timedelta(days=40))
    call_command("purge_expired")
    assert not EmailLoginCode.objects.filter(email="old@example.com").exists()
    assert EmailLoginCode.objects.filter(email="fresh@example.com").exists()
    assert AuthThrottle.objects.count() == 0 or all(
        t.window_start > timezone.now() - timedelta(days=1) for t in AuthThrottle.objects.all()
    )
    assert RefreshToken.objects.count() == 0
    assert Session.objects.count() == 0
