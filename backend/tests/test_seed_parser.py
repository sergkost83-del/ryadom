"""Проверка разбора справочника. Без Django: запускается и через pytest, и через unittest."""

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.communities.seed import DEFAULT_SEED, SeedError, load_seed_file, parse_seed  # noqa: E402


def _data():
    return json.loads(Path(DEFAULT_SEED).read_text(encoding="utf-8"))


class SeedParserTests(unittest.TestCase):
    def test_real_seed_has_expected_directory(self):
        records = load_seed_file()
        self.assertEqual(len(records), 23)
        self.assertEqual({r.community_name for r in records}, {"Новые горизонты", "Стороны света", "Стороны света-2"})
        self.assertEqual(sum(1 for r in records if r.community_name == "Новые горизонты"), 17)
        self.assertEqual({r.locality for r in records}, {"Бугры"})

    def test_duplicate_house_rejected(self):
        data = _data()
        houses = data["regions"][0]["localities"][0]["communities"][0]["streets"][0]["houses"]
        houses.append(copy.deepcopy(houses[0]))
        with self.assertRaises(SeedError):
            parse_seed(data)

    def test_duplicate_community_slug_rejected(self):
        data = _data()
        comms = data["regions"][0]["localities"][0]["communities"]
        comms[1]["slug"] = comms[0]["slug"]
        with self.assertRaises(SeedError):
            parse_seed(data)

    def test_bad_slug_rejected(self):
        data = _data()
        data["regions"][0]["localities"][0]["communities"][0]["slug"] = "Новые горизонты"
        with self.assertRaises(SeedError):
            parse_seed(data)

    def test_missing_keys_rejected(self):
        with self.assertRaises(SeedError):
            parse_seed({})
        with self.assertRaises(SeedError):
            parse_seed({"regions": [{"name": "X"}]})

    def test_empty_label_rejected(self):
        data = _data()
        data["regions"][0]["localities"][0]["communities"][0]["streets"][0]["houses"][0]["label"] = "  "
        with self.assertRaises(SeedError):
            parse_seed(data)


if __name__ == "__main__":
    unittest.main()
