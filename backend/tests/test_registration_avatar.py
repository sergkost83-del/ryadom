import pytest

from apps.identity.models import User
from tests.helpers import register, verified_token

pytestmark = pytest.mark.django_db


def test_registration_saves_chosen_avatar(api, seeded):
    from apps.communities.models import Building

    building = Building.objects.order_by("label").first()
    response = register(api, verified_token(api, "avatar@example.com"), building, avatar_id=5)
    assert response.status_code == 201
    assert User.objects.get(email="avatar@example.com").avatar_id == 5


def test_registration_avatar_defaults_to_first_and_rejects_out_of_range(api, seeded):
    from apps.communities.models import Building

    building = Building.objects.order_by("label").first()
    assert register(api, verified_token(api, "a1@example.com"), building, avatar_id=9).status_code == 400
    assert register(api, verified_token(api, "a2@example.com"), building).status_code == 201
    assert User.objects.get(email="a2@example.com").avatar_id == 1
