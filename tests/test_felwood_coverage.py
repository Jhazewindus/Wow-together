"""Felwood quest facts, profession scope and class handoffs."""
import copy
import json
import sys
import unittest
from test_addon import ROOT
from test_stv_coverage import client
sys.path.insert(0, str(ROOT / 'tools'))
from build_quest_dataset import own_lua
from import_warcraftdb import apply_stage_corrections

class FelwoodCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.q = own_lua(ROOT / 'WowTogether/QuestCatalogue.lua', 'catalogue')['quests']
        cls.exclusions = json.loads((ROOT / 'tools/quest_exclusions.json').read_text())

    def test_trey_remains_is_a_provided_delivery(self):
        q = self.q[5385]
        self.assertEqual([(x['itemID'], x['quantity']) for x in q['requiredItems']], [(13562, 1)])
        self.assertIn(13562, [p['entityID'] for p in q['providedItems']])
        self.assertFalse(q.get('requirements'))
        self.assertFalse(q.get('missingRequirements'))
        self.assertEqual((q['starts'][0]['entityID'], q['ends'][0]['entityID']), (11020, 11019))

    def test_grazle_points_and_deadwood_quantities_are_complete_without_inferred_gates(self):
        q = self.q[6131]
        self.assertEqual(q['starts'][0]['entityID'], 11554)
        self.assertEqual(q['ends'][0]['entityID'], 11554)
        self.assertEqual((q['starts'][0]['mapID'], q['starts'][0]['x'], q['starts'][0]['y']), (1448, .5093, .8501))
        self.assertEqual({(r['entityID'], r['quantity']) for r in q['requirements']}, {(7153, 5), (7154, 5), (7155, 5)})
        self.assertFalse(q.get('previousQuest'))
        self.assertFalse(q.get('prerequisites'))
        self.assertFalse(q.get('prerequisiteAny'))
        self.assertFalse(q.get('requiredMinRep'))

    def test_profession_salves_are_classified_without_removing_catalogue_facts(self):
        ids = {ident for row in self.exclusions for ident in row.get('questIDs', [])}
        self.assertTrue({5883, 5884, 5885, 5886, 5888, 5889, 5890, 5891}.issubset(ids))
        for ident in (5882, 5887):
            self.assertNotIn(ident, ids)
            self.assertIsNotNone(self.q[ident])
        for ident in (5883, 5884, 5885, 5886, 5888, 5889, 5890, 5891):
            self.assertIsNotNone(self.q[ident])
            self.assertTrue(client().ns.IsLevelingExcludedQuest(ident))

    def test_warlock_objectives_and_class_masks_retain_exact_items(self):
        q = self.q[7602]
        self.assertEqual(q['classMask'], 256)
        self.assertEqual({(r['itemID'], r['quantity']) for r in q['requiredItems']}, {(18622, 1), (18623, 1), (18624, 1)})
        points = {p['itemID']: p for p in q['objectives']}
        self.assertEqual({(item, points[item]['entityID'], points[item]['mapID']) for item in points},
                         {(18622, 9862, 1448), (18623, 6011, 1419), (18624, 6200, 1447)})
        self.assertFalse(q.get('missingRequirements'))
        self.assertFalse(q.get('objectiveLocationsIncomplete'))
        wrong = self.q[8421]
        self.assertEqual(wrong['classMask'], 256)
        self.assertEqual({(r['itemID'], r['quantity']) for r in wrong['requiredItems']}, {(20613, 10), (20614, 4)})
        self.assertEqual({p['itemID'] for p in wrong['objectives']}, {20613, 20614})

    def test_class_quests_follow_the_existing_player_setting(self):
        def identity_allowed(c, ident):
            result = c.ns.CatalogueIdentityAllowed(ident, c.ns.profile)
            return result[0] if isinstance(result, tuple) else result
        warlock = client('Horde', class_id=9, level=55)
        self.assertTrue(warlock.ns.ClassQuestEnabled(7602))
        self.assertTrue(identity_allowed(warlock, 7602))
        self.assertFalse(identity_allowed(warlock, 7632))
        warlock.ns.SetOption('classQuests', False)
        self.assertFalse(warlock.ns.ClassQuestEnabled(7602))
        hunter = client('Alliance', class_id=3, level=55)
        self.assertTrue(hunter.ns.ClassQuestEnabled(7632))
        self.assertTrue(identity_allowed(hunter, 7632))
        self.assertFalse(identity_allowed(hunter, 7602))

    def test_hunter_raid_handoffs_remain_unknown_instead_of_getting_fake_world_points(self):
        for ident in (7632, 7635):
            q = self.q[ident]
            self.assertEqual(q['classMask'], 4)
            self.assertTrue(q.get('objectiveLocationsIncomplete') or q.get('missingRequirements'))
        self.assertFalse(self.q[7632].get('starts'))
        self.assertEqual(self.q[7635]['prerequisiteAny'], [7632])

    def test_stage_corrections_are_idempotent_and_guard_existing_facts(self):
        rows = copy.deepcopy(self.q)
        self.assertEqual(apply_stage_corrections(rows), [])
        self.assertEqual(rows, self.q)
        rows = copy.deepcopy(self.q)
        rows[6131]['starts'][0]['x'] = .1
        before = copy.deepcopy(rows)
        with self.assertRaises(ValueError):
            apply_stage_corrections(rows)
        self.assertEqual(rows, before)

if __name__ == '__main__':
    unittest.main()
