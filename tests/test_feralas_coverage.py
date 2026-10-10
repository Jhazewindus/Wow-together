"""Feralas data corrections preserve hand-ins and leave unsupported work open."""
import copy
import sys
import unittest
from pathlib import Path

from test_addon import ROOT
from test_stv_coverage import client
from test_routes import guide

sys.path.insert(0, str(ROOT / 'tools'))
from build_quest_dataset import own_lua
from import_warcraftdb import apply_stage_corrections


class FeralasFactsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.quests = own_lua(ROOT / 'WowTogether/QuestCatalogue.lua', 'catalogue')['quests']

    def test_acceptance_supplied_items_stay_as_handin_requirements(self):
        expected = {
            2941: (9329, 'A Short Note'),
            2943: (9331, 'Feralas: A History'),
            2972: (9368, "Jer'kai's Signet Ring"),
            2976: (9462, 'Crate of Grimtotem Horns'),
            3121: (9629, 'A Shrunken Head'),
            3122: (9628, "Neeru's Herb Pouch"),
            3841: (11102, 'Unhatched Sprite Darter Egg'),
            3843: (11471, 'Fragile Sprite Darter Egg'),
            4267: (11466, "Raschal's Report"),
        }
        for ident, (item_id, name) in expected.items():
            with self.subTest(quest=ident):
                quest = self.quests[ident]
                self.assertEqual([(x['itemID'], x['name'], x['quantity'])
                                  for x in quest['requiredItems']], [(item_id, name, 1)])
                self.assertFalse(quest.get('requirements'))
                self.assertFalse(quest.get('objectives'))
                self.assertIn({'entityType': 'item', 'entityID': item_id,
                               'name': name, 'quantity': 1}, quest['providedItems'])
                self.assertTrue(quest.get('ends'))

    def test_morrow_stone_requires_both_items_and_keeps_parent_gate(self):
        quest = self.quests[2942]
        self.assertEqual(quest['prerequisiteAny'], [2879])
        self.assertEqual({(r['itemID'], r['quantity']) for r in quest['requiredItems']},
                         {(9307, 1), (9306, 1)})
        self.assertIn({'entityType': 'item', 'entityID': 9306,
                       'name': 'Stave of Equinex', 'quantity': 1}, quest['providedItems'])
        self.assertEqual((quest['objectives'][0]['entityID'], quest['objectives'][0]['action']),
                         (7764, 'talk'))
        self.assertFalse(quest.get('missingRequirements'))
        self.assertFalse(quest.get('objectiveLocationsIncomplete'))
        c = client('Alliance', class_id=11, level=45)
        g = guide(c, (2942,)); g.fixedRoute = True
        c.ns.GenerateFixedGuide(g, False)
        step = next(s for s in g.fixedPlan.values() if s.id == 2942 and s.kind == 'q')
        self.assertEqual(c.ns.GuideStepAction(step), 'Speak to Troyas Moonbreeze')

    def test_unproven_elixir_source_and_two_item_count_remain_open(self):
        quest = self.quests[3842]
        self.assertEqual([(x['itemID'], x['quantity']) for x in quest['requiredItems']], [(3825, 2)])
        self.assertTrue(quest['objectiveLocationsIncomplete'])
        self.assertEqual(quest['missingRequirements'][0]['quantity'], 2)
        self.assertEqual(quest['prerequisiteAny'], [3841])

    def test_existing_two_parent_zukkash_delivery_is_unchanged(self):
        quest = self.quests[7732]
        self.assertEqual(set(quest['prerequisiteAll']), {7730, 7731})
        self.assertEqual([(x['itemID'], x['quantity']) for x in quest['requiredItems']], [(19020, 1)])
        self.assertIn({'entityType': 'item', 'entityID': 19020,
                       'name': "Camp Mojache Zukk'ash Report", 'quantity': 1}, quest['providedItems'])

    def test_stage_corrections_are_idempotent_and_nonmutating_when_current(self):
        rows = copy.deepcopy(self.quests)
        before = copy.deepcopy(rows)
        self.assertEqual(apply_stage_corrections(rows), [])
        self.assertEqual(rows, before)


if __name__ == '__main__':
    unittest.main()
