import json

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.communities.models import Building, Community
from apps.identity.models import User

pytestmark = pytest.mark.django_db


def test_demo_seed_refuses_outside_development(settings, seeded):
    settings.DEBUG = False
    with pytest.raises(CommandError):
        call_command("seed_demo")


def test_demo_seed_creates_two_invites_in_different_houses(settings, seeded, tmp_path):
    settings.DEBUG = True
    out = tmp_path / "codes.json"
    call_command("seed_demo", out=str(out))
    codes = json.loads(out.read_text(encoding="utf-8"))
    assert set(codes) == {"a1", "a2"} and codes["a1"] != codes["a2"]
    community = Community.objects.get(slug="novye-gorizonty")
    assert Building.objects.filter(street__community=community).count() >= 2
    assert not User.objects.filter(is_staff=True).exists()
