"""Regression checks for newly captured Desolace quest stages."""
import json
import unittest

from test_addon import ROOT
import sys
sys.path.insert(0, str(ROOT / 'tools'))
from build_quest_dataset import own_lua


class DesolaceCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.quests = own_lua(ROOT / 'WowTogether/QuestCatalogue.lua', 'catalogue')['quests']
        cls.coverage = json.loads((ROOT / 'WowTogether/QuestCoverage.json').read_text())
        cls.sources = json.loads((ROOT / 'research/desolace-2026-10-10/source-facts.json').read_text())

    def test_new_handoff_locations_and_faction_hubs_are_mapped(self):
        q = self.quests
        self.assertEqual(q[79229]['starts'][0]['entityID'], 417353)
        self.assertEqual(q[79229]['startRefs'][0]['entityType'], 'object')
        self.assertEqual((q[79229]['ends'][0]['entityID'], q[79229]['ends'][0]['mapID']), (11438, 1443))
        self.assertEqual((q[79235]['starts'][0]['entityID'], q[79235]['starts'][0]['mapID']), (11438, 1443))
        self.assertEqual((q[79235]['ends'][0]['entityID'], q[79235]['ends'][0]['mapID']), (215643, 1434))
        self.assertEqual((q[93224]['starts'][0]['entityID'], q[93224]['ends'][0]['entityID']), (5396, 5396))
        self.assertEqual((q[94872]['starts'][0]['entityID'], q[94872]['ends'][0]['entityID']), (5412, 253139))
        self.assertEqual((q[93227]['starts'][0]['entityID'], q[93227]['ends'][0]['entityID']), (5396, 253140))

    def test_totem_objective_is_explicit_but_kodo_count_stays_unknown(self):
        totems = self.quests[93224]
        objective = next(p for p in totems['objectives'] if p.get('itemID') == 254432)
        self.assertEqual((objective['quantity'], objective['entityID'], objective['action']), (5, 4633, 'collect'))
        self.assertEqual(objective['alternativeCount'], 28)
        self.assertFalse(totems.get('objectiveLocationsIncomplete'))
        kodo = self.quests[5561]
        self.assertTrue(kodo['objectiveLocationsIncomplete'])
        self.assertTrue(any(r.get('quantityUnknown') for r in kodo.get('missingRequirements', [])))

    def test_source_gaps_and_deferred_shared_behavior_are_retained(self):
        self.assertTrue(self.quests[6568].get('objectiveLocationsIncomplete'))
        self.assertTrue(self.quests[79236].get('objectiveLocationsIncomplete'))
        capture = self.coverage['supplemental_capture']
        self.assertEqual(capture['deferred_quest_ids'], [79242])
        self.assertIn('fixed-guide compilation', capture['deferred_reason'])
        pages = {int(i): row for i, row in capture['evidence'].items()}
        for ident in (79229, 79235, 79236, 79242, 93224, 93227, 94872):
            self.assertEqual(pages[ident]['source'], f'https://www.wowhead.com/forever/quest={ident}')
            self.assertEqual(len(pages[ident]['sha256']), 64)
        self.assertEqual([r['questID'] for r in self.sources['deferredChanges']], [79242])

    def test_fact_updates_keep_the_complete_fixed_action_scope(self):
        before = json.loads((ROOT / 'research/desolace-2026-10-10/flow-before.json').read_text())['guides']
        after = json.loads((ROOT / 'research/desolace-2026-10-10/flow-after.json').read_text())['guides']
        self.assertEqual(len(before), 5)
        self.assertEqual(len(after), 5)
        for old, new in zip(before, after):
            self.assertEqual((old['faction'], old['key']), (new['faction'], new['key']))
            self.assertEqual({(s['id'], s['kind']) for s in old['stops']},
                             {(s['id'], s['kind']) for s in new['stops']})
            self.assertTrue(new['flow']['valid'])
        for old, new in zip(before, after):
            if '31-40' in new['key']:
                for ident in (79229, 79235, 79236, 79242):
                    self.assertIn(ident, {s['id'] for s in new['stops']})


if __name__ == '__main__':
    unittest.main()
