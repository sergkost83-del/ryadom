"""Журнал защищён от изменения самой базой данных (триггер), а не только кодом приложения."""

import pytest
from django.db import DatabaseError, connection, transaction

from apps.audit.models import AuditLog
from apps.identity.models import User

pytestmark = pytest.mark.django_db


def _run(sql, params):
    with connection.cursor() as cursor, transaction.atomic():
        cursor.execute(sql, params)


def test_database_rejects_update_and_delete_of_audit_rows():
    entry = AuditLog.objects.create(action="test.row", actor_email="a@example.com", note="исходное")
    with pytest.raises(DatabaseError):
        _run("UPDATE audit_auditlog SET note = %s WHERE id = %s", ["подделано", entry.pk])
    with pytest.raises(DatabaseError):
        _run("UPDATE audit_auditlog SET action = %s WHERE id = %s", ["forged", entry.pk])
    with pytest.raises(DatabaseError):
        _run("DELETE FROM audit_auditlog WHERE id = %s", [entry.pk])
    entry.refresh_from_db()
    assert entry.note == "исходное" and entry.action == "test.row"


def test_deleting_the_actor_still_works_and_only_clears_the_link():
    user = User.objects.create_user("actor@example.com")
    AuditLog.objects.create(action="test.actor", actor=user, actor_email=user.email)
    user.delete()
    entry = AuditLog.objects.get(action="test.actor")
    assert entry.actor is None and entry.actor_email == "actor@example.com"


def test_database_rejects_linking_a_row_to_another_actor():
    user = User.objects.create_user("target@example.com")
    entry = AuditLog.objects.create(action="test.link", actor_email="x@example.com")
    with pytest.raises(DatabaseError):
        _run("UPDATE audit_auditlog SET actor_id = %s WHERE id = %s", [user.pk, entry.pk])
