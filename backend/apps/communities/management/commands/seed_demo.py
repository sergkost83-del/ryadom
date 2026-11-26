"""Демо-приглашения для сквозного сценария и проверки в Codespaces. Только в режиме разработки."""

import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.communities.models import Building, Community
from apps.communities.services import create_invite


class Command(BaseCommand):
    help = "Создаёт два одноразовых кода приглашения в разные дома одного ЖК (только для разработки и проверок)."

    def add_arguments(self, parser):
        parser.add_argument("--out", default=None, help="Файл для записи кодов (JSON). Без него — в консоль.")
        parser.add_argument("--community", default="novye-gorizonty", help="slug ЖК")

    def handle(self, *args, **options):
        if not settings.DEBUG and os.environ.get("RYADOM_ALLOW_DEMO") != "1":
            raise CommandError("Демо-приглашения создаются только в режиме разработки.")
        community = Community.objects.filter(slug=options["community"]).first()
        if community is None:
            raise CommandError("ЖК не найден. Сначала выполните load_communities.")
        buildings = list(Building.objects.filter(street__community=community).order_by("label")[:2])
        if len(buildings) < 2:
            raise CommandError("Нужны минимум два дома в ЖК.")
        codes = {}
        for key, building in zip(("a1", "a2"), buildings):
            _, code = create_invite(created_by=None, building=building, expires_in_days=1, note="демо")
            codes[key] = code
        payload = json.dumps(codes, ensure_ascii=False, indent=2)
        if options["out"]:
            with open(options["out"], "w", encoding="utf-8") as fh:
                fh.write(payload)
        self.stdout.write(payload)
