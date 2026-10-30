import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command

from apps.communities.models import Membership, Notice
from apps.identity.models import User
from tests.helpers import admin_login, make_staff, resident

pytestmark = pytest.mark.django_db


@pytest.fixture
def moderator(seeded):
    return make_staff("mod@example.com", ["novye-gorizonty"])


def test_setup_roles_is_idempotent_and_minimal():
    call_command("setup_roles")
    call_command("setup_roles")
    group = Group.objects.get(name="Модераторы")
    codenames = set(group.permissions.values_list("codename", flat=True))
    assert codenames == {
        "view_membership", "change_membership",
        "view_addresschangerequest", "change_addresschangerequest",
        "view_houseinvite", "add_houseinvite", "change_houseinvite",
        "view_notice", "add_notice", "change_notice", "delete_notice",
        "view_building", "view_street", "view_community",
    }
    forbidden = ("user", "consent", "session", "auditlog", "moderatorassignment", "totp", "backup")
    assert not any(word in c for c in codenames for word in forbidden)


def test_moderator_can_work_with_addresses_invites_and_notices_only(client, moderator):
    admin_login(client, moderator)
    for allowed in ("membership", "notice", "houseinvite", "addresschangerequest", "community", "building"):
        assert client.get(f"/admin/communities/{allowed}/").status_code == 200, allowed
    for forbidden in (
        "/admin/identity/user/",
        "/admin/communities/region/",
        "/admin/communities/moderatorassignment/",
        "/admin/audit/auditlog/",
        "/admin/auth/group/",
    ):
        assert client.get(forbidden).status_code == 403, forbidden


def test_staff_without_role_has_no_access_to_data(client, db):
    user = User.objects.create_user("staff@example.com", is_staff=True)
    admin_login(client, user)
    assert client.get("/admin/communities/membership/").status_code == 403


def test_resident_cannot_open_admin(client, api, building):
    resident(api, "res@example.com", building)
    client.force_login(User.objects.get(email="res@example.com"))
    response = client.get("/admin/communities/membership/")
    assert response.status_code == 302 and "login" in response["Location"]


def test_moderator_confirms_address_and_resident_gets_access(client, api, building, moderator):
    pending = resident(api, "new@example.com", building, status="pending")
    Notice.objects.create(building=building, title="Добро пожаловать", body="Текст")
    assert pending.get("/api/v1/notices/").status_code == 403
    admin_login(client, moderator)
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
