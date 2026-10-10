"""Arathi data regressions; unknown offers and terrain require player checks."""
import copy
import json
import sys
import unittest
from pathlib import Path

from test_addon import Client, ROOT

sys.path.insert(0, str(ROOT / 'tools'))
from build_quest_dataset import own_lua
from import_warcraftdb import apply_stage_corrections


class ArathiCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = own_lua(ROOT / 'WowTogether/QuestCatalogue.lua', 'catalogue')['quests']
        cls.source_facts = json.loads((ROOT / 'research/arathi-highlands-2026-10-10/source-facts.json').read_text())

    def test_anyone_can_cook_retains_all_verified_ogre_sources(self):
        quest = self.records[79624]
        self.assertEqual((quest['side'], quest['level'], quest['minLevel']), ('Both', 40, 32))
        self.assertEqual((quest['classMask'], quest['raceMask']), (0, 0))
        self.assertFalse(quest.get('starts'))  # The page provides no starter relation.
        self.assertEqual(quest['ends'][0]['entityID'], 217300)
        self.assertEqual((quest['objectives'][0]['itemID'], quest['objectives'][0]['quantity']), (213422, 1))
        alternatives = quest['objectiveAlternatives'][0]['locations']
        self.assertEqual(len(alternatives), 22)
        self.assertEqual({point['entityID'] for point in alternatives},
                         {2254, 2255, 2256, 2287, 2566, 2567, 2569, 2570, 2571})
        self.assertEqual({point['mapID'] for point in alternatives}, {1416, 1417})
        self.assertTrue(all(point['action'] == 'loot' and point['itemName'] == 'Illegible Recipe'
                            and point.get('locationSource', '').startswith('Wowhead Forever NPC ')
                            for point in alternatives))

    def test_hammerfall_suture_and_restock_chain_keeps_unknown_stages_visible(self):
        suture, restock = self.records[97539], self.records[92519]
        self.assertEqual((suture['side'], suture['level'], suture['minLevel']), ('Horde', 36, 30))
        self.assertEqual((suture['classMask'], suture['raceMask']), (0, 0))
        self.assertEqual((suture['starts'][0]['entityID'], suture['ends'][0]['entityID']), (12920, 12920))
        self.assertEqual((suture['requiredItems'][0]['itemID'], suture['requiredItems'][0]['quantity']), (278225, 12))
        silk_sources = suture['objectiveAlternatives'][0]['locations']
        self.assertEqual({point['entityID'] for point in silk_sources}, {2563, 2565})
        self.assertEqual((restock['side'], restock['level'], restock['minLevel']), ('Horde', 36, 30))
        self.assertEqual((restock['classMask'], restock['raceMask']), (0, 0))
        self.assertEqual(restock['previousQuest'], 97539)  # The prior quest must be handed in.
        self.assertFalse(restock.get('starts'))  # No source identifies who offers the follow-up.
        self.assertEqual(restock['ends'][0]['entityID'], 12920)
        self.assertEqual((restock['requiredItems'][0]['itemID'], restock['requiredItems'][0]['quantity']),
                         (278462, 1))
        self.assertTrue(restock['objectiveLocationsIncomplete'])
        self.assertEqual(restock.get('objectives') or [], [])

    def test_giant_in_the_den_maps_confirmed_return_and_warns_for_elite(self):
        quest = self.records[92707]
        self.assertEqual((quest['side'], quest['level'], quest['minLevel']), ('Horde', 33, 30))
        self.assertEqual((quest['classMask'], quest['raceMask']), (0, 0))
        self.assertFalse(quest.get('starts'))
        self.assertEqual((quest['objectives'][0]['entityID'], quest['objectives'][0]['itemID'],
                          quest['objectives'][0]['quantity']), (218032, 253711, 1))
        self.assertEqual(quest['ends'][0]['entityID'], 2771)
        self.assertEqual((quest['ends'][0]['mapID'], quest['ends'][0]['x'], quest['ends'][0]['y']),
                         (1417, .742, .338))
        self.assertEqual(self.source_facts['entityFacts']['npc-218032']['classification'], 1)
        c = Client(quests=(), use_catalogue=True)
        self.assertTrue(c.ns.IsGroupQuest(92707))
        self.assertEqual(c.ns.QuestGroupWarning(92707),
                         'Elite quest: bring a party for its objectives, or use Skip quest.')
        c.ns.profile.faction = 'Alliance'
        self.assertFalse(c.ns.CatalogueAllowed(92707, c.ns.profile, c.ns.self)[0])

    def test_stage_corrections_are_guarded_and_idempotent(self):
        quests = {i: copy.deepcopy(self.records[i]) for i in (79624, 92519, 92707, 97539)}
        self.assertEqual(apply_stage_corrections(quests), [])
        bad = copy.deepcopy(quests)
        bad[92707]['ends'][0]['x'] = .7
        original = copy.deepcopy(bad)
        with self.assertRaises(ValueError):
            apply_stage_corrections(bad)
        self.assertEqual(bad, original)


if __name__ == '__main__':
    unittest.main()
