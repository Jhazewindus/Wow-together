import sys
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import build_farm_prior_package as package


class FishingReferenceTests(unittest.TestCase):
    def test_nested_area_references_multiply_chances_and_keep_short_sources(self):
        rows = {
            'gameobjects': [],
            'gameobject_loot': [],
            'fishing_loot': [
                {'ownerLootId': 501, 'itemId': 0, 'chanceOrQuestChance': 50, 'minCountOrReference': -10},
                {'ownerLootId': 502, 'itemId': 0, 'chanceOrQuestChance': 100, 'minCountOrReference': -30},
            ],
            'reference_loot': [
                {'ownerLootId': 10, 'itemId': 0, 'chanceOrQuestChance': 80, 'minCountOrReference': -20},
                {'ownerLootId': 20, 'itemId': 6308, 'chanceOrQuestChance': 50, 'minCountOrReference': 2},
                {'ownerLootId': 30, 'itemId': 6359, 'chanceOrQuestChance': 100, 'minCountOrReference': 1},
            ],
            'items': [{'id': 6308, 'name': 'Raw Fish'}, {'id': 6359, 'name': 'Firefin Snapper'}],
        }
        transforms = {
            1417: {'continent': 0, 'mapID': 1417, 'targetName': 'Arathi Highlands'},
            1434: {'continent': 0, 'mapID': 1434, 'targetName': 'Stranglethorn Vale'},
        }
        with patch.object(package, 'read_rows', side_effect=lambda name: rows[name]), \
             patch.object(package, 'read_geometry', return_value=(transforms, {501: 1417, 502: 1434}, {})):
            results = package.build_gathering_records(Path('unused'))
        arathi = results['Fishing|Arathi Highlands|1417']['loot']
        stranglethorn = results['Fishing|Stranglethorn Vale|1434']['loot']
        self.assertEqual([(item['itemID'], item['chance'], item['quantity']) for item in arathi], [(6308, 20, 2)])
        self.assertEqual([(item['itemID'], item['chance']) for item in stranglethorn], [(6359, 100)])
        self.assertTrue(all(len(item['source']) <= 480 for item in arathi + stranglethorn))


if __name__ == '__main__':
    unittest.main()
