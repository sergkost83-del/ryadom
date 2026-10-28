import uuid

import pytest
from django.core import mail

from apps.identity.models import User
from tests.helpers import as_user, last_code, login, register, request_code, signup, verified_token, verify

pytestmark = pytest.mark.django_db


def test_request_code_sends_mail_and_never_returns_code(api):
    response = request_code(api, "Anna@Example.com")
    assert response.status_code == 202
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["anna@example.com"]
    assert last_code() not in response.content.decode()


def test_full_registration_creates_user_consents_and_pending_membership(api, building):
    request_code(api, "new@example.com")
    response = verify(api, "new@example.com", last_code())
    body = response.json()
    assert response.status_code == 200 and body["is_new"] is True
    assert "tokens" not in body
    created = register(api, body["registration_token"], building)
    assert created.status_code == 201
    user = User.objects.get(email="new@example.com")
    assert user.display_name == "Анна Иванова"
    assert user.age_confirmed_at is not None
    assert user.account_type == "adult"
    assert not user.has_usable_password()
    assert set(user.consents.values_list("consent_type", flat=True)) == {"privacy_policy", "personal_data"}
    membership = user.memberships.get()
    assert membership.status == "pending" and membership.building_id == building.id
    as_user(api, created.json()["tokens"]["access"])
    me = api.get("/api/v1/me/")
    assert me.status_code == 200
    assert me.json()["email"] == "new@example.com"
    assert me.json()["membership"]["status"] == "pending"


@pytest.mark.parametrize(
    "override, field",
    [
        ({"is_adult": False}, "is_adult"),
        ({"consents": {}}, "consents"),
        ({"consents": {"privacy_policy": "old", "personal_data": "old"}}, "consents"),
        ({"display_name": "<b>x</b>"}, "display_name"),
        ({"display_name": "A"}, "display_name"),
        ({"building_id": str(uuid.uuid4())}, "building_id"),
    ],
)
def test_registration_is_rejected_for_invalid_input(api, building, override, field):
    token = verified_token(api, "x@example.com")
    response = register(api, token, building, **override)
    assert response.status_code == 400
    assert field in response.json()
    assert not User.objects.filter(email="x@example.com").exists()


def test_registration_requires_valid_token(api, building):
    assert register(api, "garbage", building).status_code == 400


def test_registration_token_cannot_be_used_twice(api, building):
    token = verified_token(api, "twice@example.com")
    assert register(api, token, building).status_code == 201
    assert register(api, token, building).status_code == 409
    assert User.objects.filter(email="twice@example.com").count() == 1


def test_existing_user_logs_in_on_second_device_without_registering(api, building):
    signup(api, "dev@example.com", building)
    response = login(api, "dev@example.com", device_name="Samsung")
    body = response.json()
    assert response.status_code == 200 and body["is_new"] is False
    assert body["user"]["email"] == "dev@example.com"
    assert "registration_token" not in body
    assert User.objects.get(email="dev@example.com").sessions.count() == 2


def test_inactive_user_cannot_log_in(api, building):
    signup(api, "off@example.com", building)
    User.objects.filter(email="off@example.com").update(is_active=False)
    assert login(api, "off@example.com").status_code == 400


def test_user_can_have_only_one_active_address(api, building, other_building):
    from django.db import IntegrityError, transaction

    from apps.communities.models import Membership

    signup(api, "one@example.com", building)
    user = User.objects.get(email="one@example.com")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Membership.objects.create(user=user, building=other_building)
