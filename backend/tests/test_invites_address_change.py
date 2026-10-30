import re
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.communities import services
from apps.communities.models import AddressChangeRequest, Building, HouseInvite, Membership, Notice
from apps.audit.models import AuditLog
from tests.helpers import (
    admin_login,
    client_for,
    login,
    make_staff,
    register,
    resident,
    verified_token,
)

pytestmark = pytest.mark.django_db

A, B = "novye-gorizonty", "storony-sveta"
INVALID = "Код приглашения недействителен или истёк."


@pytest.fixture
def world(seeded):
    return {
        "b1": Building.objects.filter(street__community__slug=A).order_by("label").first(),
        "b2": Building.objects.filter(street__community__slug=B).order_by("label").first(),
        "mod1": make_staff("mod1@example.com", [A]),
        "mod2": make_staff("mod2@example.com", [B]),
    }


def test_moderator_creates_invite_in_admin_code_shown_once_and_stored_hashed(client, world):
    admin_login(client, world["mod1"])
    response = client.post(
        "/admin/communities/houseinvite/add/", {"building": world["b1"].pk, "expires_in_days": 14, "note": ""},
        follow=True,
    )
    page = response.content.decode()
    code = re.search(r"Код приглашения: ([A-Z2-9]{4}-[A-Z2-9]{4})", page).group(1)
    invite = HouseInvite.objects.get(created_by=world["mod1"])
    assert invite.code_hash != code and code not in invite.code_hash
    assert timedelta(days=13) < invite.expires_at - timezone.now() < timedelta(days=15)
    assert code not in client.get(f"/admin/communities/houseinvite/{invite.pk}/change/").content.decode()


def test_invite_lifetime_is_capped_by_the_form(client, world, settings):
    admin_login(client, world["mod1"])
    response = client.post(
        "/admin/communities/houseinvite/add/",
        {"building": world["b1"].pk, "expires_in_days": settings.INVITE_MAX_DAYS + 1, "note": ""},
    )
    assert response.status_code == 200 and not HouseInvite.objects.exists()


def test_registration_with_invite_confirms_address_and_consumes_code(api, world):
    invite, code = services.create_invite(created_by=world["mod1"], building=world["b1"])
    response = register(api, verified_token(api, "guest@example.com"), None, invite_code=code.lower())
    assert response.status_code == 201
    assert response.json()["user"]["membership"]["status"] == "confirmed"
    membership = Membership.objects.get(user__email="guest@example.com")
    assert membership.building_id == world["b1"].pk and membership.confirmed_by == world["mod1"]
    invite.refresh_from_db()
    assert invite.used_at and invite.used_by.email == "guest@example.com"
    assert AuditLog.objects.filter(action="invite.used", object_id=str(invite.pk)).exists()
    Notice.objects.create(building=world["b1"], title="Для своих", body="x")
    tokens = response.json()["tokens"]
    assert client_for(tokens).get("/api/v1/notices/").status_code == 200


def test_invite_is_single_use(api, world):
    _, code = services.create_invite(created_by=world["mod1"], building=world["b1"])
    assert register(api, verified_token(api, "first@example.com"), None, invite_code=code).status_code == 201
    second = register(api, verified_token(api, "second@example.com"), None, invite_code=code)
    assert second.status_code == 400 and second.json()["invite_code"] == [INVALID]


@pytest.mark.parametrize("breakage", ["expired", "revoked", "wrong", "other_building"])
def test_unusable_invites_give_the_same_answer(api, world, breakage):
    invite, code = services.create_invite(created_by=world["mod1"], building=world["b1"])
    extra = {}
    if breakage == "expired":
        HouseInvite.objects.filter(pk=invite.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
    elif breakage == "revoked":
        services.revoke_invite(invite, world["mod1"])
    elif breakage == "wrong":
        code = "ZZZZ-ZZZZ"
    else:
        extra["building_id"] = str(world["b2"].pk)
    response = register(api, verified_token(api, "x@example.com"), None, invite_code=code, **extra)
    assert response.status_code == 400 and response.json()["invite_code"] == [INVALID]
    assert not Membership.objects.filter(user__email="x@example.com").exists()


def test_invite_guessing_is_rate_limited(api, world, settings):
    token = verified_token(api, "guesser@example.com")
    for _ in range(settings.INVITE_ATTEMPTS_PER_IP_HOUR):
        assert register(api, token, None, invite_code="AAAA-AAAA").status_code == 400
    assert register(api, token, None, invite_code="AAAA-AAAA").status_code == 429


def test_registration_needs_building_or_invite(api, world):
    response = register(api, verified_token(api, "none@example.com"), None)
    assert response.status_code == 400 and "building_id" in response.json()


def test_revoked_invite_cannot_be_used_but_unused_one_can_be_revoked_once(world):
    invite, _ = services.create_invite(created_by=world["mod1"], building=world["b1"])
    assert services.revoke_invite(invite, world["mod1"]) is True
    assert services.revoke_invite(invite, world["mod1"]) is False


def test_resident_changes_address_by_invite_of_the_new_house(api, world):
    client = resident(api, "mover@example.com", world["b1"])
    Notice.objects.create(building=world["b1"], title="Старый дом", body="x")
    Notice.objects.create(building=world["b2"], title="Новый дом", body="x")
    _, code = services.create_invite(created_by=world["mod2"], building=world["b2"])
    response = client.post("/api/v1/me/address-change/", {"invite_code": code}, format="json")
    assert response.status_code == 200 and response.json()["request"]["status"] == "approved"
    statuses = dict(Membership.objects.filter(user__email="mover@example.com").values_list("building_id", "status"))
    assert statuses == {world["b1"].pk: "ended", world["b2"].pk: "confirmed"}
    titles = [n["title"] for n in client.get("/api/v1/notices/").json()["notices"]]
    assert titles == ["Новый дом"]
    assert AuditLog.objects.filter(action="address_change.approved_by_invite").exists()
    assert client.post("/api/v1/me/address-change/", {"invite_code": code}, format="json").status_code == 400


def test_address_change_request_flow_until_moderator_of_new_community_decides(client, api, world):
    mover = resident(api, "flow@example.com", world["b1"])
    Notice.objects.create(building=world["b1"], title="Старый дом", body="x")
    Notice.objects.create(building=world["b2"], title="Новый дом", body="x")
    created = mover.post("/api/v1/me/address-change/", {"building_id": str(world["b2"].pk)}, format="json")
    assert created.status_code == 201 and created.json()["request"]["status"] == "pending"
    assert [n["title"] for n in mover.get("/api/v1/notices/").json()["notices"]] == ["Старый дом"]
    duplicate = mover.post("/api/v1/me/address-change/", {"building_id": str(world["b2"].pk)}, format="json")
    assert duplicate.status_code == 409
    state = mover.get("/api/v1/me/address-change/").json()
    assert state["membership"]["building"]["label"] == world["b1"].label and state["request"]["status"] == "pending"
    req = AddressChangeRequest.objects.get(user__email="flow@example.com")
    selected = {"action": "approve_selected", "_selected_action": [str(req.pk)]}
    admin_login(client, world["mod1"])  # модератор прежнего ЖК решать не вправе
    client.post("/admin/communities/addresschangerequest/", selected)
    req.refresh_from_db()
    assert req.status == "pending"
    admin_login(client, world["mod2"])
    client.post("/admin/communities/addresschangerequest/", selected)
    req.refresh_from_db()
    assert req.status == "approved" and req.decided_by == world["mod2"]
    assert [n["title"] for n in mover.get("/api/v1/notices/").json()["notices"]] == ["Новый дом"]
    logged = AuditLog.objects.get(action="address_change.approve")
    assert logged.actor == world["mod2"] and logged.community.slug == B


def test_rejected_request_keeps_the_old_address(client, api, world):
    mover = resident(api, "stay@example.com", world["b1"])
    mover.post("/api/v1/me/address-change/", {"building_id": str(world["b2"].pk)}, format="json")
    req = AddressChangeRequest.objects.get(user__email="stay@example.com")
    admin_login(client, world["mod2"])
    client.post(
        "/admin/communities/addresschangerequest/", {"action": "reject_selected", "_selected_action": [str(req.pk)]}
    )
    req.refresh_from_db()
    assert req.status == "rejected"
    assert Membership.objects.get(user__email="stay@example.com", status="confirmed").building_id == world["b1"].pk


def test_superuser_can_decide_any_request(client, api, world):
    boss = make_staff("boss@example.com", superuser=True)
    resident(api, "any@example.com", world["b1"]).post(
        "/api/v1/me/address-change/", {"building_id": str(world["b2"].pk)}, format="json"
    )
    req = AddressChangeRequest.objects.get(user__email="any@example.com")
    admin_login(client, boss)
    client.post(
        "/admin/communities/addresschangerequest/", {"action": "approve_selected", "_selected_action": [str(req.pk)]}
    )
    req.refresh_from_db()
    assert req.status == "approved" and req.decided_by == boss


def test_cancel_and_validation(api, world):
    mover = resident(api, "cancel@example.com", world["b1"])
    assert mover.post("/api/v1/me/address-change/cancel/").status_code == 404
    same = mover.post("/api/v1/me/address-change/", {"building_id": str(world["b1"].pk)}, format="json")
    assert same.status_code == 400
    assert mover.post("/api/v1/me/address-change/", {}, format="json").status_code == 400
    import uuid

    unknown = mover.post("/api/v1/me/address-change/", {"building_id": str(uuid.uuid4())}, format="json")
    assert unknown.status_code == 400
    mover.post("/api/v1/me/address-change/", {"building_id": str(world["b2"].pk)}, format="json")
    assert mover.post("/api/v1/me/address-change/cancel/").status_code == 204
    assert AddressChangeRequest.objects.get(user__email="cancel@example.com").status == "cancelled"
    again = mover.post("/api/v1/me/address-change/", {"building_id": str(world["b2"].pk)}, format="json")
    assert again.status_code == 201


def test_address_change_requires_login(api):
    assert api.get("/api/v1/me/address-change/").status_code == 401
    assert api.post("/api/v1/me/address-change/", {}, format="json").status_code == 401


def test_login_helper_still_works_for_existing_resident(api, world):
    resident(api, "again@example.com", world["b1"])
    assert login(api, "again@example.com").json()["is_new"] is False
