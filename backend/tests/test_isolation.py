"""Главное свойство платформы: житель видит закрытые данные только своего подтверждённого дома."""

import pytest

from apps.communities.models import Membership, Notice
from tests.helpers import resident

pytestmark = pytest.mark.django_db

LIST = "/api/v1/notices/"


@pytest.fixture
def world(api, building, other_building):
    notice_a = Notice.objects.create(building=building, title="Отключение воды", body="Дом A, завтра с 10 до 16")
    notice_b = Notice.objects.create(building=other_building, title="Собрание жильцов", body="Дом B, в субботу")
    return {
        "a": resident(api, "a@example.com", building),
        "b": resident(api, "b@example.com", other_building),
        "notice_a": notice_a,
        "notice_b": notice_b,
    }


def titles(response):
    return [n["title"] for n in response.json()["notices"]]


def test_resident_sees_only_own_building_notices(world):
    assert titles(world["a"].get(LIST)) == ["Отключение воды"]
    assert titles(world["b"].get(LIST)) == ["Собрание жильцов"]


def test_foreign_notice_looks_nonexistent(world):
    assert world["a"].get(f"{LIST}{world['notice_b'].id}/").status_code == 404
    assert world["b"].get(f"{LIST}{world['notice_a'].id}/").status_code == 404
    assert world["a"].get(f"{LIST}{world['notice_a'].id}/").status_code == 200


def test_neighbour_in_same_building_sees_the_notice(api, building, world):
    neighbour = resident(api, "neighbour@example.com", building)
    assert titles(neighbour.get(LIST)) == ["Отключение воды"]


@pytest.mark.parametrize("status", ["pending", "rejected", "ended"])
def test_unconfirmed_membership_gives_no_access(api, building, world, status):
    client = resident(api, "late@example.com", building, status=status)
    response = client.get(LIST)
    assert response.status_code == 403
    assert response.json()["detail"]
    assert client.get(f"{LIST}{world['notice_a'].id}/").status_code == 403


def test_anonymous_has_no_access(api, world):
    assert api.get(LIST).status_code == 401
    assert api.get(f"{LIST}{world['notice_a'].id}/").status_code == 401


def test_unpublished_notice_is_hidden(world):
    Notice.objects.filter(pk=world["notice_a"].pk).update(is_published=False)
    assert titles(world["a"].get(LIST)) == []
    assert world["a"].get(f"{LIST}{world['notice_a'].id}/").status_code == 404


def test_access_disappears_when_membership_ends(world):
    Membership.objects.filter(user__email="a@example.com").update(status="ended")
    assert world["a"].get(LIST).status_code == 403


def test_outdated_consents_block_access_until_accepted(world, settings):
    settings.LEGAL_DOCUMENT_VERSIONS = {"privacy_policy": "2027-01", "personal_data": "2027-01"}
    blocked = world["a"].get(LIST)
    assert blocked.status_code == 403
    assert blocked.json()["detail"].startswith("Нужно принять")
    assert world["a"].get("/api/v1/me/").json()["consents_up_to_date"] is False
    accepted = world["a"].post(
        "/api/v1/me/consents/accept/", {"consents": dict(settings.LEGAL_DOCUMENT_VERSIONS)}, format="json"
    )
    assert accepted.status_code == 200 and accepted.json()["up_to_date"] is True
    assert world["a"].get(LIST).status_code == 200


def test_ids_are_uuid_so_they_cannot_be_enumerated(world):
    assert len(str(world["notice_a"].id)) == 36
