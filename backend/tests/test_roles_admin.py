import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command

from apps.communities.models import Membership
from apps.identity.models import User
from tests.helpers import resident

pytestmark = pytest.mark.django_db


@pytest.fixture
def moderator(db):
    call_command("setup_roles")
    user = User.objects.create_user("mod@example.com", is_staff=True)
    user.groups.add(Group.objects.get(name="Модераторы"))
    return user


def test_setup_roles_is_idempotent_and_minimal():
    call_command("setup_roles")
    call_command("setup_roles")
    group = Group.objects.get(name="Модераторы")
    codenames = set(group.permissions.values_list("codename", flat=True))
    assert codenames == {
        "view_membership", "change_membership", "view_notice", "add_notice", "change_notice", "delete_notice",
        "view_building", "view_street", "view_community",
    }
    assert not any("user" in c or "consent" in c or "session" in c for c in codenames)


def test_moderator_can_work_with_addresses_and_notices_only(client, moderator):
    client.force_login(moderator)
    assert client.get("/admin/communities/membership/").status_code == 200
    assert client.get("/admin/communities/notice/").status_code == 200
    for forbidden in ("/admin/identity/user/", "/admin/communities/region/", "/admin/auth/group/"):
        assert client.get(forbidden).status_code == 403


def test_staff_without_role_has_no_access_to_data(client, db):
    user = User.objects.create_user("staff@example.com", is_staff=True)
    client.force_login(user)
    assert client.get("/admin/communities/membership/").status_code == 403


def test_resident_cannot_open_admin(client, api, building):
    resident(api, "res@example.com", building)
    client.force_login(User.objects.get(email="res@example.com"))
    response = client.get("/admin/communities/membership/")
    assert response.status_code == 302 and "login" in response["Location"]


def test_moderator_confirms_address_and_resident_gets_access(client, api, building, moderator):
    from apps.communities.models import Notice

    pending = resident(api, "new@example.com", building, status="pending")
    Notice.objects.create(building=building, title="Добро пожаловать", body="Текст")
    assert pending.get("/api/v1/notices/").status_code == 403
    client.force_login(moderator)
    membership = Membership.objects.get(user__email="new@example.com")
    response = client.post(
        "/admin/communities/membership/",
        {"action": "confirm_selected", "_selected_action": [str(membership.pk)]},
        follow=True,
    )
    assert response.status_code == 200
    membership.refresh_from_db()
    assert membership.status == "confirmed" and membership.confirmed_by == moderator and membership.confirmed_at
    assert pending.get("/api/v1/notices/").status_code == 200
