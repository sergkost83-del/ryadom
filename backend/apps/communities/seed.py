"""Разбор и проверка файла стартовых данных. Без зависимостей от Django: проверяется отдельно."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SEED = Path(__file__).resolve().parent / "data" / "communities_seed.json"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class SeedError(ValueError):
    pass


@dataclass(frozen=True)
class BuildingSeed:
    region: str
    locality: str
    community_name: str
    community_slug: str
    street: str
    label: str
    slug: str


def _text(value, where, max_len):
    if not isinstance(value, str) or not value.strip():
        raise SeedError(f"{where}: нужна непустая строка")
    value = value.strip()
    if len(value) > max_len:
        raise SeedError(f"{where}: длиннее {max_len} символов")
    return value


def _slug(value, where, max_len):
    value = _text(value, where, max_len)
    if not SLUG_RE.match(value):
        raise SeedError(f"{where}: slug '{value}' должен состоять из латиницы, цифр и дефисов")
    return value


def _items(data, key, where):
    if not isinstance(data, dict) or not isinstance(data.get(key), list) or not data[key]:
        raise SeedError(f"{where}: ожидался непустой список '{key}'")
    return data[key]


def parse_seed(data) -> list[BuildingSeed]:
    records: list[BuildingSeed] = []
    seen_community = set()
    seen_building = set()
    for region in _items(data, "regions", "корень"):
        region_name = _text(region.get("name") if isinstance(region, dict) else None, "region.name", 120)
        for locality in _items(region, "localities", region_name):
            locality_name = _text(locality.get("name"), f"{region_name}.locality.name", 120)
            for community in _items(locality, "communities", locality_name):
                c_name = _text(community.get("name"), f"{locality_name}.community.name", 120)
                c_slug = _slug(community.get("slug"), f"{c_name}.slug", 80)
                if (region_name, locality_name, c_slug) in seen_community:
                    raise SeedError(f"{c_name}: повторяющийся slug '{c_slug}'")
                seen_community.add((region_name, locality_name, c_slug))
                for street in _items(community, "streets", c_name):
                    s_name = _text(street.get("name"), f"{c_name}.street.name", 120)
                    for house in _items(street, "houses", s_name):
                        label = _text(house.get("label"), f"{s_name}.house.label", 40)
                        slug = _slug(house.get("slug"), f"{s_name}.{label}.slug", 40)
                        key = (c_slug, s_name, slug)
                        label_key = (c_slug, s_name, label)
                        if key in seen_building or label_key in seen_building:
                            raise SeedError(f"{s_name}, {label}: дом повторяется")
                        seen_building.add(key)
                        seen_building.add(label_key)
                        records.append(
                            BuildingSeed(region_name, locality_name, c_name, c_slug, s_name, label, slug)
                        )
    return records


def load_seed_file(path=DEFAULT_SEED) -> list[BuildingSeed]:
    with open(path, encoding="utf-8") as fh:
        return parse_seed(json.load(fh))
