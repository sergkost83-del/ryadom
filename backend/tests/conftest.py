import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.communities.models import Building


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def seeded(db):
    call_command("load_communities")


@pytest.fixture
def building(seeded):
    return Building.objects.filter(street__community__slug="novye-gorizonty").order_by("label").first()


@pytest.fixture
def other_building(seeded):
    return Building.objects.filter(street__community__slug="storony-sveta").order_by("label").first()
