"""Телефон хранится только по отдельному согласию; закрытые заявки удаляются по сроку."""

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.communities.models import AddressChangeRequest, Building, Membership
from apps.identity.models import Consent, User
from tests.helpers import resident

pytestmark = pytest.mark.django_db


@pytest.fixture
def house(seeded):
    return Building.objects.order_by("label").first()


def test_phone_without_consent_is_refused(api, house):
    client = resident(api, "nophone@example.com", house)
    response = client.patch("/api/v1/me/", {"phone": "+79001234567"}, format="json")
    assert response.status_code == 400 and "phone" in response.json()
    assert User.objects.get(email="nophone@example.com").phone == ""


def test_phone_with_consent_is_saved_and_recorded(api, house):
    client = resident(api, "withphone@example.com", house)
    response = client.patch("/api/v1/me/", {"phone": "+79001234567", "phone_consent": True}, format="json")
    assert response.status_code == 200
    assert response.json()["phone"] == "+79001234567" and response.json()["phone_consent"] is True
    active = Consent.objects.filter(
        user__email="withphone@example.com", consent_type="phone", withdrawn_at__isnull=True
    )
    assert active.exists()


def test_clearing_phone_withdraws_consent(api, house):
    client = resident(api, "clear@example.com", house)
    client.patch("/api/v1/me/", {"phone": "+79001234567", "phone_consent": True}, format="json")
    response = client.patch("/api/v1/me/", {"phone": ""}, format="json")
    assert response.status_code == 200 and response.json()["phone_consent"] is False
    active = Consent.objects.filter(
        user__email="clear@example.com", consent_type="phone", withdrawn_at__isnull=True
    )
    assert not active.exists()


def test_phone_consent_does_not_block_app_access(api, house):
    client = resident(api, "access@example.com", house)
    client.patch("/api/v1/me/", {"phone": "+79001234567", "phone_consent": True}, format="json")
    client.patch("/api/v1/me/", {"phone": ""}, format="json")
    assert client.get("/api/v1/me/").json()["consents_up_to_date"] is True


def test_purge_clears_phones_without_consent_and_keeps_those_with_it(api, house):
    without = resident(api, "p-without@example.com", house)
    with_consent = resident(api, "p-with@example.com", house)
    User.objects.filter(email="p-without@example.com").update(phone="+79001111111")
    with_consent.patch("/api/v1/me/", {"phone": "+79002222222", "phone_consent": True}, format="json")
    call_command("purge_expired")
    assert User.objects.get(email="p-without@example.com").phone == ""
    assert User.objects.get(email="p-with@example.com").phone == "+79002222222"


def test_purge_removes_old_closed_requests_only(api, house):
    old = timezone.now() - timedelta(days=120)
    resident(api, "keep@example.com", house)  # подтверждённый адрес — не трогаем
    resident(api, "old-rejected@example.com", house, status="pending")
    Membership.objects.filter(user__email="old-rejected@example.com").update(status="rejected", updated_at=old)
    resident(api, "old-moved@example.com", house)
    address = AddressChangeRequest.objects.create(
        user=User.objects.get(email="old-moved@example.com"),
        to_building=Building.objects.exclude(pk=house.pk).order_by("label").first(),
        status=AddressChangeRequest.STATUS_CANCELLED,
    )
    AddressChangeRequest.objects.filter(pk=address.pk).update(updated_at=old)
    call_command("purge_expired")
    assert not Membership.objects.filter(user__email="old-rejected@example.com").exists()
    assert not AddressChangeRequest.objects.filter(pk=address.pk).exists()
    assert Membership.objects.filter(user__email="keep@example.com", status="confirmed").exists()
