import pytest

from apps.identity.models import Session
from tests.helpers import as_user, login, signup

pytestmark = pytest.mark.django_db


def _tokens(response):
    return response.json()["tokens"]


def test_logout_closes_only_this_device(api, building):
    first = signup(api, "s@example.com", building)["tokens"]
    second = _tokens(login(api, "s@example.com", device_name="Phone"))
    as_user(api, first["access"])
    assert api.post("/api/v1/auth/logout/").status_code == 204
    assert api.get("/api/v1/me/").status_code == 401
    as_user(api, second["access"])
    assert api.get("/api/v1/me/").status_code == 200


def test_logout_all_closes_every_device(api, building):
    first = signup(api, "all@example.com", building)["tokens"]
    second = _tokens(login(api, "all@example.com"))
    as_user(api, first["access"])
    assert api.post("/api/v1/auth/logout-all/").status_code == 204
    for tokens in (first, second):
        as_user(api, tokens["access"])
        assert api.get("/api/v1/me/").status_code == 401


def test_sessions_list_marks_current_device(api, building):
    first = signup(api, "list@example.com", building, device_name="Laptop")["tokens"]
    _tokens(login(api, "list@example.com", device_name="Phone"))
    as_user(api, first["access"])
    sessions = api.get("/api/v1/auth/sessions/").json()["sessions"]
    assert len(sessions) == 2
    assert sum(1 for s in sessions if s["current"]) == 1
    assert {s["device_name"] for s in sessions} == {"Laptop", "Phone"}


def test_user_can_close_another_device_remotely(api, building):
    first = signup(api, "remote@example.com", building)["tokens"]
    second = _tokens(login(api, "remote@example.com"))
    as_user(api, first["access"])
    other = [s for s in api.get("/api/v1/auth/sessions/").json()["sessions"] if not s["current"]][0]
    assert api.delete(f"/api/v1/auth/sessions/{other['id']}/").status_code == 204
    as_user(api, second["access"])
    assert api.get("/api/v1/me/").status_code == 401


def test_cannot_close_someone_elses_session(api, building):
    victim = signup(api, "victim@example.com", building)["tokens"]
    attacker = signup(api, "attacker@example.com", building)["tokens"]
    victim_session = Session.objects.get(user__email="victim@example.com")
    as_user(api, attacker["access"])
    assert api.delete(f"/api/v1/auth/sessions/{victim_session.id}/").status_code == 404
    as_user(api, victim["access"])
    assert api.get("/api/v1/me/").status_code == 200


def test_refresh_rotates_tokens(api, building):
    tokens = signup(api, "rot@example.com", building)["tokens"]
    response = api.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]}, format="json")
    assert response.status_code == 200
    new = response.json()["tokens"]
    assert new["refresh"] != tokens["refresh"]
    as_user(api, new["access"])
    assert api.get("/api/v1/me/").status_code == 200


def test_reused_refresh_token_revokes_the_session(api, building):
    tokens = signup(api, "reuse@example.com", building)["tokens"]
    fresh = api.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]}, format="json").json()["tokens"]
    stolen = api.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]}, format="json")
    assert stolen.status_code == 401
    assert api.post("/api/v1/auth/refresh/", {"refresh": fresh["refresh"]}, format="json").status_code == 401
    as_user(api, fresh["access"])
    assert api.get("/api/v1/me/").status_code == 401


def test_unknown_refresh_token_is_rejected(api):
    assert api.post("/api/v1/auth/refresh/", {"refresh": "nope"}, format="json").status_code == 401


def test_expired_access_token_is_rejected(api, building, settings):
    tokens = signup(api, "exp@example.com", building)["tokens"]
    settings.AUTH_ACCESS_TTL_SECONDS = -1
    as_user(api, tokens["access"])
    assert api.get("/api/v1/me/").status_code == 401


def test_forged_and_missing_tokens_are_rejected(api):
    assert api.get("/api/v1/me/").status_code == 401
    as_user(api, "forged.token.value")
    assert api.get("/api/v1/me/").status_code == 401
    api.credentials(HTTP_AUTHORIZATION="Basic abc")
    assert api.get("/api/v1/me/").status_code == 401


def test_deactivated_user_loses_access_immediately(api, building):
    from apps.identity.models import User

    tokens = signup(api, "ban@example.com", building)["tokens"]
    User.objects.filter(email="ban@example.com").update(is_active=False)
    as_user(api, tokens["access"])
    assert api.get("/api/v1/me/").status_code == 401
    assert api.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]}, format="json").status_code == 401
