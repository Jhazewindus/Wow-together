import copy
import json
import unittest
from pathlib import Path

from test_addon import Client, ROOT

import sys
sys.path.insert(0, str(ROOT / 'tools'))
from build_quest_dataset import own_lua
from import_warcraftdb import apply_corrections, apply_stage_corrections


class SilithusCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue = own_lua(ROOT / 'WowTogether/QuestCatalogue.lua', 'catalogue')
        cls.quests = cls.catalogue['quests']
        cls.sources = json.loads((ROOT / 'research/silithus-2026-10-10/source-facts.json').read_text())

    def test_supplied_tablets_prism_and_colossus_husks_are_delivery_tokens(self):
        records = copy.deepcopy(self.quests)
        apply_stage_corrections(records)
        expected = {8287: 20405, 8314: 20463, 8857: 21534, 8858: 21535, 8859: 21533}
        for quest_id, item_id in expected.items():
            quest = records[quest_id]
            self.assertFalse(quest['requirements'])
            self.assertFalse(quest['objectives'])
            self.assertFalse(quest.get('missingRequirements'))
            self.assertFalse(quest.get('objectiveLocationsIncomplete'))
            self.assertEqual(quest['providedItems'][0]['entityID'], item_id)
            self.assertTrue(quest['ends'])

    def test_text_and_council_item_sources_keep_real_alternatives_and_unknowns(self):
        q = self.quests[8318]
        text_sources = {loc['entityID'] for alt in q['objectiveAlternatives'] for loc in alt['locations']}
        self.assertEqual(text_sources, {11880, 11881, 11882, 11883, 14479, 15201, 15213, 15308, 15541, 15542})
        self.assertFalse(q.get('objectiveLocationsIncomplete'))
        self.assertEqual(q['requiredItems'][0]['quantity'], 10)
        self.assertEqual(self.sources['entityPages']['item:20404']['sources'][0]['action'], 'loot')

        for quest_id, item_id, npcs in [
                (8332, 20513, {15209, 15211, 15212, 15307}),
                (8341, 20514, {15206, 15207, 15208, 15220})]:
            quest = self.quests[quest_id]
            alternatives = [a for a in quest['objectiveAlternatives'] if a['itemName'] in ('Abyssal Crest', 'Abyssal Signet')]
            self.assertEqual({loc['entityID'] for alt in alternatives for loc in alt['locations']}, npcs)
            self.assertIn(14344, {item['itemID'] for item in quest['requiredItems']})
            self.assertTrue(quest.get('objectiveLocationsIncomplete'))
            self.assertTrue(any(r.get('entityID') == 14344 for r in quest.get('missingRequirements', [])))

    def test_regal_rubbing_and_world_boss_gaps_remain_honest_and_grouped(self):
        glyph = self.quests[8309]
        self.assertTrue(glyph.get('objectiveLocationsIncomplete'))
        self.assertIn(20456, {r['entityID'] for r in glyph['missingRequirements']})
        self.assertNotIn(180453, {p['entityID'] for p in glyph['objectives']})
        self.assertEqual(self.quests[9248]['questType'], 'Elite')
        self.assertEqual(self.quests[9248]['requiredItems'][0]['itemID'], 20515)

    def test_raid_and_event_content_is_out_of_leveling_but_elites_remain(self):
        records = copy.deepcopy(self.quests)
        apply_corrections(records)
        apply_stage_corrections(records)
        for quest_id in [8315, 8316, 8351, 8352, 8376, 8377, 8378, 8379, 8380, 8381, 8382,
                         8556, 8557, 8558, *range(8689, 8713), 8743, 8745, 9023]:
            self.assertTrue(records[quest_id].get('levelingExcluded'), quest_id)
        c = Client(quests=(), use_catalogue=True)
        c.guide_environment(level=60)
        c.lua.globals().grouped = False
        c.ns.guideLevel = 'all'
        c.ns.db.config.classQuests = True
        c.ns.db.config.soloMode = True
        c.ns.ReadProfile()
        c.ns.profile.faction = 'Horde'
        c.ns.profile.raceID = 2
        c.ns.profile.level = 60
        guide = next(g for g in c.ns.LevelingGuideChoices().values() if g.zone == 'Silithus')
        c.ns.GenerateFixedGuide(guide, False)
        steps = [(int(step.id), step.kind) for step in guide.fixedPlan.values()]
        ids = {ident for ident, _ in steps}
        for quest_id in (8315, 8316, 8351, 8352, 8556, 8557, 8558, 8743, 8745, 9023):
            self.assertNotIn(quest_id, ids)
        for quest_id in (8306, 8309, 8314, 8332, 8341, 9248):
            self.assertIn(quest_id, ids)
            self.assertTrue(c.ns.IsGroupQuest(quest_id))
            self.assertEqual(c.ns.QuestGroupWarning(quest_id),
                             'Elite quest: bring a party for its objectives, or use Skip quest.')
        for quest_id, item_id in [(8287, 20405), (8314, 20463)]:
            talks = [kind for ident, kind in steps if ident == quest_id and kind == 'q']
            self.assertTrue(talks)  # The step is a hand-in visit, not an item farm.
            self.assertTrue(all(step.action == 'talk' for step in guide.fixedPlan.values()
                                if int(step.id) == quest_id and step.kind == 'q'))
            self.assertEqual(self.quests[quest_id]['providedItems'][0]['entityID'], item_id)

    def test_reviewed_import_corrections_are_idempotent_and_guarded(self):
        records = {9248: copy.deepcopy(self.quests[9248])}
        self.assertEqual(apply_corrections(records), [])
        self.assertEqual(apply_stage_corrections(records), [])
        self.assertEqual(records[9248]['questType'], 'Elite')
        altered = copy.deepcopy(records)
        altered[9248]['questType'] = 'Raid'
        with self.assertRaises(ValueError):
            apply_corrections(altered)


if __name__ == '__main__':
    unittest.main()
