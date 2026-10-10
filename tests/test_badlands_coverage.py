"""Badlands data regressions; actual offers and terrain need beta checks."""
import copy
import unittest

from test_addon import Client, ROOT

import sys
sys.path.insert(0, str(ROOT / 'tools'))
from build_quest_dataset import own_lua
from import_warcraftdb import apply_stage_corrections


class BadlandsCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = own_lua(ROOT / 'WowTogether/QuestCatalogue.lua', 'catalogue')['quests']

    def test_amulet_delivery_follows_the_confirmed_chain(self):
        quest = self.records[723]
        self.assertEqual((quest['previousQuest'], quest['side']), (722, 'Alliance'))
        self.assertEqual(quest['providedItems'][0]['entityID'], 4635)
        self.assertEqual(quest['ends'][0]['entityID'], 2910)
        self.assertEqual(quest['ends'][0]['action'], 'talk')
        self.assertEqual(quest.get('objectives') or [], [])
        self.assertFalse(quest.get('objectiveLocationsIncomplete'))

    def test_liquid_stone_keeps_chest_sources_and_the_unmapped_potion_visible(self):
        quest = self.records[715]
        self.assertEqual(quest['levelingExcluded'], 'Alchemy profession quest (skill line 171).')
        self.assertEqual((quest['starts'][0]['entityID'], quest['ends'][0]['entityID']), (2920, 2920))
        self.assertEqual({(r['itemID'], r['quantity']) for r in quest['requiredItems']}, {(929, 1), (3823, 1)})
        chests = next(a['locations'] for a in quest['objectiveAlternatives'] if a['itemName'] == 'Healing Potion')
        self.assertEqual(len(chests), 7)
        self.assertEqual({(p['entityType'], p['entityID'], p['mapID'], p['sourceAreaID']) for p in chests},
                         {('object', 2857, 1418, 3)})
        self.assertTrue(quest['objectiveLocationsIncomplete'])  # Lesser Invisibility Potion source is unknown.

    def test_bronze_bracers_remain_a_required_item_without_an_invented_farm_point(self):
        quest = self.records[716]
        self.assertEqual(quest['requiredItems'][0]['itemID'], 2868)
        self.assertTrue(quest['objectiveLocationsIncomplete'])
        self.assertFalse(quest.get('objectives'))

    def test_both_faction_variants_keep_their_own_chain_and_all_three_item_drops(self):
        for ident, faction, starter, prerequisite, race_ids in (
            (735, 'Alliance', 2786, 727, None),
            (736, 'Horde', 2934, 728, [2, 5, 6, 8, 96]),
        ):
            quest = self.records[ident]
            self.assertEqual((quest['side'], quest['starts'][0]['entityID']), (faction, starter))
            self.assertEqual(quest['ends'][0]['entityID'], starter)
            self.assertEqual(quest['prerequisiteAny'], [prerequisite])
            self.assertTrue(quest['prerequisitesUnverified'])
            self.assertEqual(quest['questType'], 'Elite')
            self.assertEqual(quest['classMask'], 0)
            if race_ids is None:
                self.assertFalse(quest.get('allowedRaceIDs'))
            else:
                self.assertEqual(quest['allowedRaceIDs'], race_ids)
            self.assertEqual({p['itemID'] for p in quest['objectives']}, {4646, 4641, 4644})
            self.assertEqual({p['entityID'] for p in quest['objectives']}, {2417, 2937, 1060})
            alternatives = {g['itemName']: g['locations'] for g in quest['objectiveAlternatives']}
            self.assertEqual([len(alternatives[name]) for name in
                              ("Star of Xil'yeh", 'Hand of Dagun', 'The Legacy Heart')], [3, 4, 1])

        c = Client(quests=(), use_catalogue=True)
        self.assertTrue(c.ns.IsGroupQuest(735))
        self.assertTrue(c.ns.IsGroupQuest(736))

    def test_primitive_drawing_has_all_published_badlands_mob_sources_but_no_guessed_starter(self):
        quest = self.records[78823]
        self.assertFalse(quest.get('starts'))
        self.assertEqual((quest['ends'][0]['entityID'], quest['ends'][0]['mapID']), (715, 1434))
        self.assertEqual((quest['objectives'][0]['itemID'], quest['objectives'][0]['quantity']), (211269, 1))
        alternatives = next(g['locations'] for g in quest['objectiveAlternatives']
                            if g['itemName'] == 'Primitive Drawing')
        self.assertEqual({p['entityID'] for p in alternatives},
                         {2701, 2715, 2716, 2717, 2718, 2720, 2892, 2893, 2894, 2906, 2907})
        self.assertTrue(all(p['mapID'] == 1418 and p['sourceAreaID'] == 3 for p in alternatives))
        self.assertEqual(len(alternatives), 36)

    def test_reagent_run_ii_keeps_horde_elite_and_prior_handoff(self):
        quest = self.records[2203]
        self.assertEqual(quest['levelingExcluded'], 'Alchemy profession quest (skill line 171; minimum rank 210).')
        self.assertEqual((quest['side'], quest['questType'], quest['prerequisiteAny']), ('Horde', 'Elite', [2202]))
        self.assertTrue(quest['prerequisitesUnverified'])
        self.assertEqual((quest['requiredItems'][0]['itemID'], quest['requiredItems'][0]['quantity']), (7867, 3))
        self.assertEqual(quest['objectives'][0]['entityID'], 2726)

    def test_reviewed_stage_corrections_are_idempotent_and_guarded(self):
        ids = (715, 723, 735, 736, 78823)
        quests = {ident: copy.deepcopy(self.records[ident]) for ident in ids}
        self.assertEqual(apply_stage_corrections(quests), [])
        bad = copy.deepcopy(quests)
        bad[78823]['objectiveAlternatives'][0]['locations'][0]['x'] = 0.9
        original = copy.deepcopy(bad)
        with self.assertRaises(ValueError):
            apply_stage_corrections(bad)
        self.assertEqual(bad, original)


if __name__ == '__main__':
    unittest.main()
