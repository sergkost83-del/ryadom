"""Изоляция ЖК: модератор работает только со своим ЖК, главный администратор — со всеми. Проверка на сервере."""

import pytest

from apps.communities import services
from apps.communities.models import (
    AddressChangeRequest,
    Building,
    Community,
    HouseInvite,
    Membership,
    ModeratorAssignment,
    Notice,
)
from apps.identity.models import User
from tests.helpers import admin_login, make_staff, resident

pytestmark = pytest.mark.django_db

A, B = "novye-gorizonty", "storony-sveta"


@pytest.fixture
def world(api, seeded):
    b1 = Building.objects.filter(street__community__slug=A).order_by("label").first()
    b2 = Building.objects.filter(street__community__slug=B).order_by("label").first()
    mod1 = make_staff("mod1@example.com", [A])
    mod1b = make_staff("mod1b@example.com", [A])
    mod2 = make_staff("mod2@example.com", [B])
    mod0 = make_staff("mod0@example.com", [])
    boss = make_staff("boss@example.com", superuser=True)
    resident(api, "r1@example.com", b1, status="pending")
    resident(api, "r2@example.com", b2, status="pending")
    resident(api, "r3@example.com", b1)  # живёт в ЖК A, хочет в B
    resident(api, "r4@example.com", b2)  # живёт в ЖК B, хочет в A
    invite1, code1 = services.create_invite(created_by=mod1, building=b1)
    invite2, code2 = services.create_invite(created_by=mod2, building=b2)
    return {
        "b1": b1, "b2": b2, "mod1": mod1, "mod1b": mod1b, "mod2": mod2, "mod0": mod0, "boss": boss,
        "n1": Notice.objects.create(building=b1, title="Дом A", body="текст"),
        "n2": Notice.objects.create(building=b2, title="Дом B", body="текст"),
        "invite1": invite1, "invite2": invite2, "code1": code1, "code2": code2,
        "m": {e: Membership.objects.get(user__email=f"{e}@example.com") for e in ("r1", "r2", "r3", "r4")},
    }


def listing(client, user, model):
    admin_login(client, user)
    response = client.get(f"/admin/communities/{model}/")
    assert response.status_code == 200
    return {obj.pk for obj in response.context["cl"].result_list}


def pks(*objects):
    return {o.pk for o in objects}


def test_membership_lists_are_limited_to_own_community(client, world):
    m = world["m"]
    assert listing(client, world["mod1"], "membership") == pks(m["r1"], m["r3"])
    assert listing(client, world["mod2"], "membership") == pks(m["r2"], m["r4"])


def test_several_moderators_of_one_community_share_the_same_data(client, world):
    assert listing(client, world["mod1b"], "membership") == listing(client, world["mod1"], "membership")


def test_moderator_without_assignment_sees_nothing(client, world):
    for model in ("membership", "notice", "houseinvite", "addresschangerequest", "building", "community"):
        assert listing(client, world["mod0"], model) == set(), model


def test_superuser_sees_every_community(client, world):
    assert listing(client, world["boss"], "membership") == pks(*world["m"].values())
    assert listing(client, world["boss"], "notice") == pks(world["n1"], world["n2"])


def test_directory_is_limited_to_own_community(client, world):
    own = Community.objects.get(slug=A)
    assert listing(client, world["mod1"], "community") == {own.pk}
    assert listing(client, world["mod1"], "building") == set(
        Building.objects.filter(street__community=own).values_list("pk", flat=True)
    )


def test_direct_url_to_foreign_membership_is_denied(client, world):
    admin_login(client, world["mod1"])
    response = client.get(f"/admin/communities/membership/{world['m']['r2'].pk}/change/")
    assert response.status_code in (302, 403, 404)
    assert "r2@example.com" not in response.content.decode()
    own = client.get(f"/admin/communities/membership/{world['m']['r1'].pk}/change/")
    assert own.status_code == 200 and "r1@example.com" in own.content.decode()


def test_confirm_action_ignores_foreign_memberships(client, world):
    admin_login(client, world["mod1"])
    selected = [str(world["m"]["r1"].pk), str(world["m"]["r2"].pk)]
    client.post("/admin/communities/membership/", {"action": "confirm_selected", "_selected_action": selected})
    assert Membership.objects.get(pk=world["m"]["r1"].pk).status == "confirmed"
    assert Membership.objects.get(pk=world["m"]["r2"].pk).status == "pending"


def test_reject_action_ignores_foreign_memberships(client, world):
    admin_login(client, world["mod2"])
    selected = [str(world["m"]["r1"].pk), str(world["m"]["r2"].pk)]
    client.post("/admin/communities/membership/", {"action": "reject_selected", "_selected_action": selected})
    assert Membership.objects.get(pk=world["m"]["r2"].pk).status == "rejected"
    assert Membership.objects.get(pk=world["m"]["r1"].pk).status == "pending"


def test_notices_are_limited_and_cannot_be_changed_or_deleted_across_communities(client, world):
    assert listing(client, world["mod1"], "notice") == pks(world["n1"])
    n2 = world["n2"]
    client.post(
        f"/admin/communities/notice/{n2.pk}/change/",
        {"building": world["b2"].pk, "title": "взлом", "body": "x", "is_published": "on"},
    )
    client.post(f"/admin/communities/notice/{n2.pk}/delete/", {"post": "yes"})
    n2.refresh_from_db()
    assert n2.title == "Дом B"


def test_moderator_cannot_publish_to_foreign_community_but_can_to_own(client, world):
    admin_login(client, world["mod1"])
    foreign = client.post(
        "/admin/communities/notice/add/",
        {"building": world["b2"].pk, "title": "в чужой ЖК", "body": "x", "is_published": "on"},
    )
    assert foreign.status_code == 200  # форма вернулась с ошибкой
    assert not Notice.objects.filter(title="в чужой ЖК").exists()
    client.post(
        "/admin/communities/notice/add/",
        {"building": world["b1"].pk, "title": "в свой ЖК", "body": "x", "is_published": "on"},
    )
    created = Notice.objects.get(title="в свой ЖК")
    assert created.created_by == world["mod1"]


def test_invites_are_limited_and_foreign_ones_cannot_be_created_or_revoked(client, world):
    assert listing(client, world["mod1"], "houseinvite") == pks(world["invite1"])
    response = client.post(
        "/admin/communities/houseinvite/add/", {"building": world["b2"].pk, "expires_in_days": 14, "note": ""}
    )
    assert response.status_code == 200
    assert HouseInvite.objects.filter(building=world["b2"]).count() == 1
    selected = [str(world["invite1"].pk), str(world["invite2"].pk)]
    client.post("/admin/communities/houseinvite/", {"action": "revoke_selected", "_selected_action": selected})
    assert HouseInvite.objects.get(pk=world["invite1"].pk).revoked_at is not None
    assert HouseInvite.objects.get(pk=world["invite2"].pk).revoked_at is None


def test_address_change_requests_are_decided_by_target_community_only(client, api, world):
    from tests.helpers import client_for, login

    tokens = {}
    for email, target in (("r3", world["b2"]), ("r4", world["b1"])):
        tokens[email] = login(api, f"{email}@example.com").json()["tokens"]
        response = client_for(tokens[email]).post(
            "/api/v1/me/address-change/", {"building_id": str(target.pk)}, format="json"
        )
        assert response.status_code == 201
    req3 = AddressChangeRequest.objects.get(user__email="r3@example.com")  # цель: ЖК B
    req4 = AddressChangeRequest.objects.get(user__email="r4@example.com")  # цель: ЖК A
    assert listing(client, world["mod1"], "addresschangerequest") == pks(req4)
    assert listing(client, world["mod2"], "addresschangerequest") == pks(req3)
    selected = [str(req3.pk), str(req4.pk)]
    admin_login(client, world["mod1"])
    client.post(
        "/admin/communities/addresschangerequest/", {"action": "approve_selected", "_selected_action": selected}
    )
    req3.refresh_from_db()
    req4.refresh_from_db()
    assert req4.status == "approved" and req4.decided_by == world["mod1"]
    assert req3.status == "pending"
    new_home = Membership.objects.get(user__email="r4@example.com", status="confirmed")
    assert new_home.building_id == world["b1"].pk
    assert Membership.objects.filter(user__email="r4@example.com", status="ended").count() == 1


def test_moderator_cannot_open_assignments_users_or_audit_log(client, world):
    admin_login(client, world["mod1"])
    for url in ("/admin/communities/moderatorassignment/", "/admin/identity/user/", "/admin/audit/auditlog/"):
        assert client.get(url).status_code == 403
    other = User.objects.get(email="r1@example.com")
    forged = client.post(
        "/admin/communities/moderatorassignment/add/",
        {"user": other.pk, "community": Community.objects.get(slug=B).pk},
    )
    assert forged.status_code == 403
    assert not ModeratorAssignment.objects.filter(user=other).exists()


def test_only_superuser_assigns_moderators_and_it_takes_effect(client, world):
    candidate = User.objects.get(email="r1@example.com")
    admin_login(client, world["boss"])
    response = client.post(
        "/admin/communities/moderatorassignment/add/",
        {"user": candidate.pk, "community": Community.objects.get(slug=B).pk},
    )
    assert response.status_code == 302
    candidate.refresh_from_db()
    assert candidate.is_staff and candidate.groups.filter(name="Модераторы").exists()
    assert ModeratorAssignment.objects.filter(user=candidate, community__slug=B).exists()
    m = world["m"]
    assert listing(client, candidate, "membership") == pks(m["r2"], m["r4"])


def test_make_and_remove_moderator_actions_are_superuser_only(client, world):
    target = User.objects.get(email="r2@example.com")
    admin_login(client, world["mod1"])
    denied = client.post(
        "/admin/identity/user/", {"action": "make_moderator", "_selected_action": [str(target.pk)]}
    )
    assert denied.status_code == 403
    target.refresh_from_db()
    assert not target.is_staff
    admin_login(client, world["boss"])
    client.post("/admin/identity/user/", {"action": "make_moderator", "_selected_action": [str(target.pk)]})
    target.refresh_from_db()
    assert target.is_staff
    ModeratorAssignment.objects.create(user=target, community=Community.objects.get(slug=B))
    client.post("/admin/identity/user/", {"action": "remove_moderator", "_selected_action": [str(target.pk)]})
    target.refresh_from_db()
    assert not target.is_staff and not ModeratorAssignment.objects.filter(user=target).exists()
