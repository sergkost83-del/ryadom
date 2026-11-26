"""Чаты: доступ только своему дому и ЖК, отправка, жалобы, блокировки, модерация, лимит частоты."""

import pytest
from django.db import IntegrityError, transaction

from apps.audit.models import AuditLog
from apps.chat.models import Message, Report, Room
from apps.communities.models import Building, Community
from tests.helpers import admin_login, make_staff, resident

pytestmark = pytest.mark.django_db

A = "novye-gorizonty"
B = "storony-sveta"


@pytest.fixture
def world(api, seeded):
    a1, a2 = list(Building.objects.filter(street__community__slug=A).order_by("label")[:2])
    b1 = Building.objects.filter(street__community__slug=B).order_by("label").first()
    return {
        "a1": a1,
        "a2": a2,
        "b1": b1,
        "ann": resident(api, "ann@example.com", a1),  # дом a1, ЖК A
        "bob": resident(api, "bob@example.com", a2),  # дом a2, тот же ЖК A
        "carl": resident(api, "carl@example.com", b1),  # другой ЖК
        "late": resident(api, "late@example.com", a1, status="pending"),
        "mod": make_staff("mod@example.com", [A]),
        "boss": make_staff("boss@example.com", superuser=True),
    }


def rooms(client):
    return {r["kind"]: r for r in client.get("/api/v1/chat/rooms/").json()["rooms"]}


def post(client, room_id, body):
    return client.post(f"/api/v1/chat/rooms/{room_id}/messages/", {"body": body}, format="json")


def test_house_and_common_rooms_are_created_for_confirmed_resident(world):
    found = rooms(world["ann"])
    assert set(found) == {"house", "common"}
    assert found["house"]["title"].endswith(world["a1"].label)
    assert Room.objects.filter(kind="house", building=world["a1"]).count() == 1


def test_neighbour_in_other_house_of_same_community_cannot_read_or_write_house_chat(world):
    house = rooms(world["ann"])["house"]
    read = world["bob"].get(f"/api/v1/chat/rooms/{house['id']}/messages/")
    assert read.status_code == 404
    assert post(world["bob"], house["id"], "привет").status_code == 404
    assert house["id"] not in [r["id"] for r in world["bob"].get("/api/v1/chat/rooms/").json()["rooms"]]


def test_common_chat_is_shared_inside_community_only(world):
    common = rooms(world["ann"])["common"]
    assert post(world["ann"], common["id"], "всем привет").status_code == 201
    assert world["bob"].get(f"/api/v1/chat/rooms/{common['id']}/messages/").status_code == 200
    assert world["carl"].get(f"/api/v1/chat/rooms/{common['id']}/messages/").status_code == 404
    assert common["id"] not in [r["id"] for r in world["carl"].get("/api/v1/chat/rooms/").json()["rooms"]]


def test_pending_resident_has_no_chat_access(world):
    assert world["late"].get("/api/v1/chat/rooms/").json()["rooms"] == []


def test_anonymous_has_no_access(api, world):
    assert api.get("/api/v1/chat/rooms/").status_code == 401


def test_post_and_read_in_order(world):
    common = rooms(world["ann"])["common"]
    post(world["ann"], common["id"], "первое")
    post(world["bob"], common["id"], "второе")
    messages = world["ann"].get(f"/api/v1/chat/rooms/{common['id']}/messages/").json()["messages"]
    assert [m["body"] for m in messages] == ["первое", "второе"]
    assert messages[0]["mine"] is True and messages[1]["mine"] is False
    assert messages[1]["author"]["id"] == world["bob"].get("/api/v1/me/").json()["id"]


@pytest.mark.parametrize("body", ["", "   ", "\x00\x07", "x" * 1001])
def test_invalid_bodies_are_rejected(world, body):
    common = rooms(world["ann"])["common"]
    assert post(world["ann"], common["id"], body).status_code == 400
    assert Message.objects.count() == 0


def test_control_characters_are_removed_and_text_kept_as_text(world):
    common = rooms(world["ann"])["common"]
    # \x00 DRF отвергает сам (нулевой символ запрещён), поэтому проверяем другой управляющий символ
    response = post(world["ann"], common["id"], "  <b>привет</b>\x07\n\nмир  ")
    assert response.status_code == 201
    assert response.json()["body"] == "<b>привет</b>\n\nмир"


def test_author_can_delete_own_message_and_it_disappears(world):
    common = rooms(world["ann"])["common"]
    mine = post(world["ann"], common["id"], "ошибка").json()
    assert world["bob"].delete(f"/api/v1/chat/messages/{mine['id']}/").status_code == 403
    assert world["ann"].delete(f"/api/v1/chat/messages/{mine['id']}/").status_code == 204
    assert world["ann"].get(f"/api/v1/chat/rooms/{common['id']}/messages/").json()["messages"] == []


def test_report_is_recorded_once_and_own_message_cannot_be_reported(world):
    common = rooms(world["ann"])["common"]
    msg = post(world["ann"], common["id"], "спорно").json()
    own = world["ann"].post(f"/api/v1/chat/messages/{msg['id']}/report/", {"reason": "x"}, format="json")
    assert own.status_code == 400
    first = world["bob"].post(f"/api/v1/chat/messages/{msg['id']}/report/", {"reason": "оскорбления"}, format="json")
    again = world["bob"].post(f"/api/v1/chat/messages/{msg['id']}/report/", {"reason": "ещё раз"}, format="json")
    assert first.status_code == 201 and again.status_code == 200
    assert Report.objects.count() == 1
    empty = world["bob"].post(f"/api/v1/chat/messages/{msg['id']}/report/", {"reason": "  "}, format="json")
    assert empty.status_code == 400


def test_block_hides_author_only_for_the_blocker(world):
    common = rooms(world["ann"])["common"]
    post(world["ann"], common["id"], "от Анны")
    msg = post(world["bob"], common["id"], "от Боба").json()
    author_id = world["bob"].get("/api/v1/me/").json()["id"]  # noqa: F841
    assert world["ann"].post(f"/api/v1/chat/messages/{msg['id']}/block-author/").status_code == 201
    ann_view = [m["body"] for m in world["ann"].get(f"/api/v1/chat/rooms/{common['id']}/messages/").json()["messages"]]
    bob_view = [m["body"] for m in world["bob"].get(f"/api/v1/chat/rooms/{common['id']}/messages/").json()["messages"]]
    assert "от Боба" not in ann_view and "от Анны" in ann_view
    assert "от Анны" in bob_view and "от Боба" in bob_view
    assert world["ann"].delete(f"/api/v1/chat/blocks/{author_id}/").status_code == 204
    url = f"/api/v1/chat/rooms/{common['id']}/messages/"
    after = [m["body"] for m in world["ann"].get(url).json()["messages"]]
    assert "от Боба" in after


def test_cannot_block_yourself(world):
    common = rooms(world["ann"])["common"]
    mine = post(world["ann"], common["id"], "моё").json()
    assert world["ann"].post(f"/api/v1/chat/messages/{mine['id']}/block-author/").status_code == 400


def test_posting_is_rate_limited(world, settings):
    settings.CHAT_POSTS_PER_10_MIN = 3
    common = rooms(world["ann"])["common"]
    for i in range(3):
        assert post(world["ann"], common["id"], f"м{i}").status_code == 201
    assert post(world["ann"], common["id"], "лишнее").status_code == 429


def test_moderator_hides_message_in_own_community_and_it_is_audited(client, world):
    common = rooms(world["ann"])["common"]
    msg = post(world["bob"], common["id"], "нарушение").json()
    admin_login(client, world["mod"])
    response = client.post(
        "/admin/chat/message/",
        {"action": "hide_selected", "_selected_action": [msg["id"]]},
        follow=True,
    )
    assert response.status_code == 200
    assert Message.objects.get(pk=msg["id"]).deleted_at is not None
    entry = AuditLog.objects.get(action="chat_message.hide")
    assert entry.actor == world["mod"] and entry.community.slug == A
    assert "нарушение" not in str(list(AuditLog.objects.values_list("changes", flat=True)))  # текст не в журнале


def test_moderator_of_other_community_cannot_hide_message(client, world):
    common = rooms(world["ann"])["common"]
    msg = post(world["bob"], common["id"], "в ЖК A").json()
    other = make_staff("mod-b@example.com", [B])
    admin_login(client, other)
    client.post("/admin/chat/message/", {"action": "hide_selected", "_selected_action": [msg["id"]]})
    assert Message.objects.get(pk=msg["id"]).deleted_at is None


def test_superuser_sees_messages_of_all_communities(client, world):
    common = rooms(world["ann"])["common"]
    post(world["ann"], common["id"], "видно всем")
    admin_login(client, world["boss"])
    assert client.get("/admin/chat/message/").status_code == 200


def test_reports_are_resolved_by_moderator_of_community(client, world):
    common = rooms(world["ann"])["common"]
    msg = post(world["ann"], common["id"], "спорное").json()
    world["bob"].post(f"/api/v1/chat/messages/{msg['id']}/report/", {"reason": "жалоба"}, format="json")
    report = Report.objects.get()
    admin_login(client, world["mod"])
    client.post("/admin/chat/report/", {"action": "resolve_selected", "_selected_action": [str(report.pk)]})
    report.refresh_from_db()
    assert report.status == "resolved" and report.decided_by == world["mod"]


def test_only_one_house_chat_per_building_and_one_common_per_community(world):
    rooms(world["ann"])  # чаты создаются при первом обращении
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Room.objects.create(
                community=Community.objects.get(slug=A), building=world["a1"], kind="house", title="дубль"
            )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Room.objects.create(community=Community.objects.get(slug=A), kind="common", title="дубль")


def test_message_history_pages_with_before_cursor(world):
    common = rooms(world["ann"])["common"]
    for i in range(5):
        post(world["ann"], common["id"], f"n{i}")
    url = f"/api/v1/chat/rooms/{common['id']}/messages/?limit=2"
    first = world["ann"].get(url).json()["messages"]
    assert [m["body"] for m in first] == ["n3", "n4"]
    before = first[0]["created_at"]
    older_url = f"/api/v1/chat/rooms/{common['id']}/messages/"
    older = world["ann"].get(older_url, {"limit": 2, "before": before}).json()["messages"]
    assert [m["body"] for m in older] == ["n1", "n2"]
    bad = world["ann"].get(f"/api/v1/chat/rooms/{common['id']}/messages/?before=не-дата")
    assert bad.status_code == 400
