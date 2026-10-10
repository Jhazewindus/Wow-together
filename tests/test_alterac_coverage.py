"""Alterac data regressions; current offers and terrain require player checks."""
import copy
import json
import sys
import unittest
from pathlib import Path

from test_addon import Client, ROOT

sys.path.insert(0, str(ROOT / 'tools'))
from build_quest_dataset import own_lua
from import_warcraftdb import apply_corrections, apply_stage_corrections
from supplement_quest_data import capture_history


class AlteracCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = own_lua(ROOT / 'WowTogether/QuestCatalogue.lua', 'catalogue')['quests']

    def test_strahnbrad_mystery_is_reviewed_horde_only(self):
        quests = {95534: copy.deepcopy(self.records[95534])}
        self.assertEqual(quests[95534]['side'], 'Horde')
        self.assertIn('quest=95534', quests[95534]['factionCorrectionSource'])
        self.assertEqual(apply_corrections(quests), [])
        quests[95534]['side'] = None
        quests[95534].pop('factionCorrectionSource')
        self.assertEqual(apply_corrections(quests), [95534])
        self.assertEqual(quests[95534]['side'], 'Horde')
        self.assertIn('quest=95534', quests[95534]['factionCorrectionSource'])
        self.assertEqual(apply_corrections(quests), [])

        c = Client(quests=(), use_catalogue=True)
        q = c.ns.CatalogueQuest(95534)
        self.assertEqual(q.side, 'Horde')
        c.ns.profile.faction = 'Alliance'
        self.assertFalse(c.ns.CatalogueAllowed(95534, c.ns.profile, c.ns.self)[0])

    def test_valik_stout_has_both_published_footpad_areas(self):
        alternatives = next(a['locations'] for a in self.records[535]['objectiveAlternatives']
                            if a['itemName'] == 'Southshore Stout')
        self.assertEqual({(p['entityID'], p['mapID'], round(p['x'], 3), round(p['y'], 3))
                          for p in alternatives}, {
            (2440, 1416, .582, .672), (2440, 1416, .584, .706)})

    def test_alterac_chain_handoffs_and_remaining_gaps_are_source_backed(self):
        # 92434 provides the key; 93680 also has a documented local object source.
        self.assertEqual(self.records[92434]['providedItems'][0]['entityID'], 279469)
        key_object = next(o for o in self.records[93680]['objectives'] if o['itemID'] == 279469)
        self.assertEqual((key_object['entityType'], key_object['entityID']), ('object', 670427))
        self.assertEqual((key_object['mapID'], key_object['x'], key_object['y']), (1416, .164, .893))
        already_enriched = {93680: copy.deepcopy(self.records[93680])}
        already_enriched[93680]['objectives'][0]['legacyStepKey'] = 'q:1416:npc:670427'
        self.assertEqual(apply_stage_corrections(already_enriched), [])
        c = Client(quests=(), use_catalogue=True)
        c.ns.active[93680] = 'Key to the City'
        c.lua.execute('C_Item={GetItemCount=function(id) return id == 279469 and 1 or 0 end}')
        progress = c.ns.GuideItemProgress(c.lua.table_from({
            'id':93680,'kind':'q','itemID':279469,'action':'gather','quantity':1}), c.ns.self)
        self.assertTrue(progress.finished)  # A carried 92434 reward avoids a second key farm.

        # The supplemental page capture adds the ordinary chain endpoints.
        for ident, giver, receiver, start, end in (
            (97287, 2410, 252085, (1424, .616, .208), (1416, .142, .6)),
            (96984, 269127, 2410, (1421, .686, .452), (1424, .616, .208)),
        ):
            quest = self.records[ident]
            self.assertEqual(quest['starts'][0]['entityID'], giver)
            self.assertEqual(quest['ends'][0]['entityID'], receiver)
            for role, expected in (('starts', start), ('ends', end)):
                point = quest[role][0]
                self.assertEqual(point['mapID'], expected[0])
                self.assertAlmostEqual(point['x'], expected[1])
                self.assertAlmostEqual(point['y'], expected[2])
        self.assertEqual(self.records[97287]['previousQuest'], 96984)
        self.assertEqual(self.records[96984]['questType'], 'Dungeon')
        # The source leaves one alternate objective source unmapped; don't invent it.
        self.assertEqual(self.records[96984]['objectives'][0]['entityID'], 246020)
        self.assertTrue(self.records[96984]['objectiveLocationsIncomplete'])
        alternate = next(t for t in self.records[96984]['npcTargets'] if t['entityID'] == 250657)
        self.assertNotIn('mapID', alternate)

    def test_new_supplement_does_not_discard_prior_hash_evidence(self):
        old = {'captured': '2026-10-07', 'evidence': {'old-page': {'sha256': 'abc'}}}
        existing = [{'captured': '2026-10-06', 'evidence': {'older': {'sha256': 'def'}}}]
        result = capture_history(old, existing)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], existing[0])
        self.assertEqual(result[1], old)
        self.assertEqual(capture_history(old, result), result)


if __name__ == '__main__':
    unittest.main()
