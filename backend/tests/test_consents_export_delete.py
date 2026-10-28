from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.communities.models import Building, Membership
from apps.identity.models import Consent, EmailLoginCode, Session, User
from tests.helpers import client_for, login, resident, signup

pytestmark = pytest.mark.django_db


def test_consent_list_shows_accepted_documents(api, building):
    client = resident(api, "c@example.com", building)
    body = client.get("/api/v1/me/consents/").json()
    assert body["up_to_date"] is True
    assert {c["consent_type"] for c in body["accepted"]} == {"privacy_policy", "personal_data"}
    assert all(c["withdrawn_at"] is None and c["accepted_at"] for c in body["accepted"])


def test_accepting_wrong_versions_is_rejected(api, building):
    client = resident(api, "w@example.com", building)
    response = client.post(
        "/api/v1/me/consents/accept/", {"consents": {"privacy_policy": "x", "personal_data": "y"}}, format="json"
    )
    assert response.status_code == 400


def test_withdrawing_privacy_policy_is_not_possible(api, building):
    client = resident(api, "pp@example.com", building)
    response = client.post("/api/v1/me/consents/withdraw/", {"consent_type": "privacy_policy"}, format="json")
    assert response.status_code == 400
    assert client.get("/api/v1/me/").status_code == 200


def test_withdrawing_personal_data_consent_starts_deletion(api, building):
    client = resident(api, "wd@example.com", building)
    response = client.post("/api/v1/me/consents/withdraw/", {"consent_type": "personal_data"}, format="json")
    assert response.status_code == 202
    user = User.objects.get(email="wd@example.com")
    assert user.is_active is False and user.deletion_requested_at is not None
    assert Consent.objects.get(user=user, consent_type="personal_data").withdrawn_at is not None
    assert client.get("/api/v1/me/").status_code == 401


def test_export_contains_only_own_data_and_no_secrets(api, building):
    mine = resident(api, "mine@example.com", building)
    resident(api, "other@example.com", building)
    response = mine.get("/api/v1/me/export/")
    assert response.status_code == 200
    assert "attachment" in response["Content-Disposition"]
    body = response.json()
    assert body["user"]["email"] == "mine@example.com"
    assert len(body["memberships"]) == 1 and body["memberships"][0]["status"] == "confirmed"
    assert {c["consent_type"] for c in body["consents"]} == {"privacy_policy", "personal_data"}
    text = response.content.decode()
    assert "other@example.com" not in text
    for secret in ("token_hash", "refresh", "password", "code_hash"):
        assert secret not in text


def test_export_requires_login(api):
    assert api.get("/api/v1/me/export/").status_code == 401


def test_deletion_requires_matching_email(api, building):
    client = resident(api, "del@example.com", building)
    assert client.post("/api/v1/me/delete/", {"confirm_email": "wrong@example.com"}, format="json").status_code == 400
    assert User.objects.get(email="del@example.com").is_active is True


def test_deletion_closes_account_and_all_devices_immediately(api, building):
    first = signup(api, "gone@example.com", building)["tokens"]
    second = login(api, "gone@example.com").json()["tokens"]
    response = client_for(first).post("/api/v1/me/delete/", {"confirm_email": "Gone@Example.com"}, format="json")
    assert response.status_code == 202 and response.json()["deletion_scheduled_for"]
    for tokens in (first, second):
        assert client_for(tokens).get("/api/v1/me/").status_code == 401
    assert Session.objects.filter(user__email="gone@example.com", revoked_at__isnull=True).count() == 0


def test_user_can_cancel_deletion_by_logging_in_within_grace_period(api, building):
    tokens = signup(api, "back@example.com", building)["tokens"]
    client_for(tokens).post("/api/v1/me/delete/", {"confirm_email": "back@example.com"}, format="json")
    response = login(api, "back@example.com")
    assert response.status_code == 200 and response.json()["restored"] is True
    user = User.objects.get(email="back@example.com")
    assert user.is_active and user.deletion_requested_at is None


def test_no_restore_after_grace_period(api, building):
    tokens = signup(api, "late@example.com", building)["tokens"]
    client_for(tokens).post("/api/v1/me/delete/", {"confirm_email": "late@example.com"}, format="json")
    User.objects.filter(email="late@example.com").update(deletion_requested_at=timezone.now() - timedelta(days=31))
    assert login(api, "late@example.com").status_code == 400


def test_purge_erases_expired_accounts_completely(api, building):
    tokens = signup(api, "erase@example.com", building)["tokens"]
    signup(api, "stay@example.com", building)
    client_for(tokens).post("/api/v1/me/delete/", {"confirm_email": "erase@example.com"}, format="json")
    call_command("purge_expired")
    assert User.objects.filter(email="erase@example.com").exists()  # срок ещё не истёк
    User.objects.filter(email="erase@example.com").update(deletion_requested_at=timezone.now() - timedelta(days=31))
    call_command("purge_expired")
    assert not User.objects.filter(email="erase@example.com").exists()
    assert not Consent.objects.filter(user__email="erase@example.com").exists()
    assert not Membership.objects.filter(user__email="erase@example.com").exists()
    assert not EmailLoginCode.objects.filter(email="erase@example.com").exists()
    assert User.objects.filter(email="stay@example.com").exists()
    assert Building.objects.filter(pk=building.pk).exists()
    assert signup(api, "erase@example.com", building)["user"]["email"] == "erase@example.com"
