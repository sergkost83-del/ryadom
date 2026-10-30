import json
import re

import pytest

from apps.audit.models import AuditLog
from apps.communities.models import Building, Membership
from apps.identity.models import User
from tests.helpers import admin_login, make_staff, resident

pytestmark = pytest.mark.django_db

A = "novye-gorizonty"


@pytest.fixture
def setup(api, seeded):
    building = Building.objects.filter(street__community__slug=A).order_by("label").first()
    mod = make_staff("mod@example.com", [A])
    boss = make_staff("boss@example.com", superuser=True)
    resident(api, "secret-resident@example.com", building, status="pending")
    return {"building": building, "mod": mod, "boss": boss,
            "membership": Membership.objects.get(user__email="secret-resident@example.com")}


def test_list_view_and_decision_are_recorded(client, setup):
    admin_login(client, setup["mod"])
    client.get("/admin/communities/membership/")
    client.get(f"/admin/communities/membership/{setup['membership'].pk}/change/")
    client.post(
        "/admin/communities/membership/",
        {"action": "confirm_selected", "_selected_action": [str(setup["membership"].pk)]},
    )
    actions = list(AuditLog.objects.filter(actor=setup["mod"]).values_list("action", flat=True))
    assert {"membership.list", "membership.view", "membership.confirm"} <= set(actions)
    confirm = AuditLog.objects.get(action="membership.confirm")
    assert confirm.actor_email == "mod@example.com"
    assert confirm.object_id == str(setup["membership"].pk)
    assert confirm.community.slug == A
    assert confirm.changes == {"status": ["pending", "confirmed"]}
    assert confirm.created_at and confirm.ip_address == "127.0.0.1"


def test_denied_access_to_foreign_object_is_recorded(client, setup):
    other = make_staff("mod-b@example.com", ["storony-sveta"])
    admin_login(client, other)
    client.get(f"/admin/communities/membership/{setup['membership'].pk}/change/")
    assert AuditLog.objects.filter(action="membership.view_denied", actor=other).exists()


def test_log_contains_no_resident_personal_data(client, setup):
    admin_login(client, setup["mod"])
    client.get("/admin/communities/membership/")
    client.get(f"/admin/communities/membership/{setup['membership'].pk}/change/")
    client.post(
        "/admin/communities/membership/",
        {"action": "confirm_selected", "_selected_action": [str(setup["membership"].pk)]},
    )
    dump = json.dumps(list(AuditLog.objects.values()), default=str)
    assert "secret-resident" not in dump


def test_invite_code_and_secrets_never_reach_the_log(client, setup):
    admin_login(client, setup["mod"])
    response = client.post(
        "/admin/communities/houseinvite/add/",
        {"building": setup["building"].pk, "expires_in_days": 7, "note": "Иван Петров, кв. 5"},
        follow=True,
    )
    code = re.search(r"Код приглашения: ([A-Z2-9]{4}-[A-Z2-9]{4})", response.content.decode()).group(1)
    created = AuditLog.objects.get(action="invite.create")
    assert created.actor == setup["mod"] and created.community.slug == A
    dump = json.dumps(list(AuditLog.objects.values()), default=str)
    assert code not in dump and code.replace("-", "") not in dump
    assert "Иван" not in dump  # свободный текст заметки в журнал не копируется


def test_log_is_visible_only_to_superuser(client, setup):
    admin_login(client, setup["mod"])
    client.get("/admin/communities/membership/")
    assert client.get("/admin/audit/auditlog/").status_code == 403
    admin_login(client, setup["boss"])
    response = client.get("/admin/audit/auditlog/")
    assert response.status_code == 200
    assert any(row.action == "membership.list" for row in response.context["cl"].result_list)


def test_log_is_append_only(client, setup):
    entry = AuditLog.objects.create(action="test.action", actor_email="x@example.com")
    entry.note = "изменено"
    with pytest.raises(PermissionError):
        entry.save()
    with pytest.raises(PermissionError):
        entry.delete()
    admin_login(client, setup["boss"])
    assert client.post("/admin/audit/auditlog/add/", {"action": "forged"}).status_code == 403
    assert client.post(f"/admin/audit/auditlog/{entry.pk}/change/", {"action": "forged"}).status_code == 403
    assert client.post(f"/admin/audit/auditlog/{entry.pk}/delete/", {"post": "yes"}).status_code == 403
    assert AuditLog.objects.get(pk=entry.pk).action == "test.action"


def test_log_survives_deletion_of_the_actor(setup):
    from apps.audit.service import record

    record(actor=setup["mod"], action="test.event")
    setup["mod"].delete()
    entry = AuditLog.objects.get(action="test.event")
    assert entry.actor is None and entry.actor_email == "mod@example.com"


def test_assignment_and_role_changes_are_recorded(client, setup):
    from apps.communities.models import Community

    candidate = User.objects.get(email="secret-resident@example.com")
    admin_login(client, setup["boss"])
    client.post(
        "/admin/communities/moderatorassignment/add/",
        {"user": candidate.pk, "community": Community.objects.get(slug=A).pk},
    )
    client.post("/admin/identity/user/", {"action": "remove_moderator", "_selected_action": [str(candidate.pk)]})
    actions = set(AuditLog.objects.filter(actor=setup["boss"]).values_list("action", flat=True))
    assert {"moderator_assignment.create", "user.remove_moderator"} <= actions


def test_erasure_of_account_is_recorded_without_email(setup):
    from datetime import timedelta

    from django.core.management import call_command
    from django.utils import timezone

    user = User.objects.get(email="secret-resident@example.com")
    User.objects.filter(pk=user.pk).update(is_active=False, deletion_requested_at=timezone.now() - timedelta(days=31))
    call_command("purge_expired")
    entry = AuditLog.objects.get(action="account.erased")
    assert entry.object_id == str(user.pk) and entry.actor is None
    assert "secret-resident" not in json.dumps(list(AuditLog.objects.values()), default=str)
