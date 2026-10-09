"""Eastern Plaguelands hand-in item facts and unresolved chapel routes."""
import copy
import json
import sys
import unittest
from pathlib import Path

from test_addon import ROOT
sys.path.insert(0, str(ROOT / 'tools'))
from build_quest_dataset import own_lua
from import_warcraftdb import apply_stage_corrections


class EasternPlaguelandsCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.quests = own_lua(ROOT / 'WowTogether/QuestCatalogue.lua', 'catalogue')['quests']
        cls.corrections = json.loads((ROOT / 'tools/quest_corrections.json').read_text())

    def test_preparation_inputs_are_not_reported_as_final_handins(self):
        expected = {5206: (13155, 5, 13157, 99), 6022: (15448, 1, 15447, 7)}
        for ident, (handin_id, handin_count, input_id, input_count) in expected.items():
            with self.subTest(quest=ident):
                quest = self.quests[ident]
                self.assertEqual([(x['itemID'], x['quantity']) for x in quest['requiredItems']],
                                 [(handin_id, handin_count)])
                self.assertEqual({x['entityID']: x['quantity'] for x in quest['requirements']},
                                 {handin_id: handin_count, input_id: input_count})
                self.assertEqual([(x['itemID'], x['quantity']) for x in quest['objectives']],
                                 [(input_id, input_count)])
                self.assertEqual(quest['ends'][0]['entityID'], 11063 if ident == 5206 else 11878)
                self.assertTrue(quest['objectiveLocationsIncomplete'])

    def test_reviewed_items_are_guarded_and_idempotent(self):
        rows = copy.deepcopy(self.quests)
        self.assertEqual(apply_stage_corrections(rows), [])
        rules = {c['questID']: c for c in self.corrections if c.get('questID') in (5206, 6022)}
        self.assertEqual(set(rules), {5206, 6022})
        self.assertTrue(all('Questie/QuestieDB Forever' in c['source'] for c in rules.values()))
        for ident in rules:
            bad = copy.deepcopy(rows)
            bad[ident]['objectives'][0]['quantity'] += 1
            before = copy.deepcopy(bad)
            with self.subTest(quest=ident), self.assertRaises(ValueError):
                apply_stage_corrections(bad)
            self.assertEqual(bad, before)

    def test_unmapped_chapel_and_dungeon_points_remain_unknown(self):
        for ident in (5464, 8946):
            self.assertFalse(self.quests[ident].get('starts'))
        for ident in (5149, 5206, 5247, 5513, 5517, 5862, 6022, 6026, 8946, 9121, 9122, 9123, 9141):
            self.assertTrue(self.quests[ident].get('objectiveLocationsIncomplete'))
        self.assertEqual(self.quests[5465]['ends'][0]['entityID'], 11286)


if __name__ == '__main__':
    unittest.main()
