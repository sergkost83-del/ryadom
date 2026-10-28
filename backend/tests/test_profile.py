import pytest

from apps.identity.models import User
from tests.helpers import as_user, signup

pytestmark = pytest.mark.django_db


def _client(api, building, email="p@example.com"):
    return as_user(api, signup(api, email, building)["tokens"]["access"])


def test_profile_update_name_avatar_phone(api, building):
    client = _client(api, building)
    response = client.patch(
        "/api/v1/me/",
        {"display_name": "  Пётр   Сидоров ", "avatar_id": 5, "phone": "+7 (900) 123-45-67"},
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "Пётр Сидоров" and body["avatar_id"] == 5 and body["phone"] == "+79001234567"
    assert User.objects.get(email="p@example.com").avatar_id == 5


def test_phone_is_optional_and_can_be_cleared(api, building):
    client = _client(api, building)
    client.patch("/api/v1/me/", {"phone": "89001234567"}, format="json")
    assert client.patch("/api/v1/me/", {"phone": ""}, format="json").json()["phone"] == ""


@pytest.mark.parametrize(
    "payload",
    [
        {"avatar_id": 9},
        {"avatar_id": 0},
        {"phone": "abc"},
        {"phone": "123"},
        {"display_name": "<img src=x onerror=alert(1)>"},
        {"display_name": " "},
    ],
)
def test_invalid_profile_values_are_rejected(api, building, payload):
    client = _client(api, building)
    assert client.patch("/api/v1/me/", payload, format="json").status_code == 400


@pytest.mark.parametrize("field", ["email", "is_staff", "is_superuser", "id", "account_type", "membership"])
def test_protected_fields_cannot_be_changed(api, building, field):
    client = _client(api, building)
    response = client.patch("/api/v1/me/", {field: "x"}, format="json")
    assert response.status_code == 400
    user = User.objects.get(email="p@example.com")
    assert user.email == "p@example.com" and not user.is_staff and not user.is_superuser


def test_me_returns_only_own_data(api, building):
    _client(api, building, "mine@example.com")
    other = signup(api, "theirs@example.com", building)["tokens"]["access"]
    as_user(api, other)
    assert api.get("/api/v1/me/").json()["email"] == "theirs@example.com"
