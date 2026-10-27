import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction

from apps.communities.models import Building, Community, Locality, Region, Street

pytestmark = pytest.mark.django_db


def test_seed_loads_expected_directory():
    call_command("load_communities")
    assert Region.objects.count() == 1
    assert Locality.objects.count() == 1
    assert Community.objects.count() == 3
    assert Building.objects.count() == 23
    assert Building.objects.filter(street__community__slug="novye-gorizonty").count() == 17


def test_seed_is_idempotent():
    call_command("load_communities")
    call_command("load_communities")
    assert Community.objects.count() == 3
    assert Building.objects.count() == 23
    assert Street.objects.count() == 4


def test_seed_with_bad_file_changes_nothing(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    with pytest.raises(CommandError):
        call_command("load_communities", file=str(bad))
    assert Community.objects.count() == 0


def test_building_label_unique_within_street():
    call_command("load_communities")
    building = Building.objects.first()
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Building.objects.create(street=building.street, label=building.label, slug="other-slug")


def test_ids_are_uuid_not_sequential():
    call_command("load_communities")
    ids = list(Building.objects.values_list("id", flat=True))
    assert len(set(ids)) == len(ids)
    assert all(len(str(i)) == 36 for i in ids)


def test_parent_cannot_be_deleted_while_children_exist():
    call_command("load_communities")
    from django.db.models import ProtectedError

    with pytest.raises(ProtectedError):
        Region.objects.first().delete()
