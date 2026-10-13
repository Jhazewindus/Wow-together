import copy
import unittest
from pathlib import Path

from build_quest_dataset import own_lua
from import_warcraftdb import apply_corrections, apply_stage_corrections


ROOT = Path(__file__).resolve().parents[1]


class AzsharaCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue = own_lua(ROOT / 'WowTogether_QuestData/QuestCatalogue.lua', 'catalogue')
        cls.quests = cls.catalogue['quests']

    def test_hydraxian_prerequisite_chain_is_explicit(self):
        quests = copy.deepcopy(self.quests)
        apply_corrections(quests)
        self.assertEqual(quests[6821]['prerequisiteAll'], [6804, 6805])
        self.assertEqual(quests[6822]['previousQuest'], 6821)
        self.assertEqual(quests[6823]['previousQuest'], 6822)
        self.assertEqual(quests[6824]['previousQuest'], 6823)
        self.assertTrue(quests[6823]['pickupRequiresOffer'])
        # The coffer reward is not evidence that 6824 is an offer prerequisite.
        self.assertFalse(quests[7486].get('prerequisiteAny'))
        self.assertFalse(quests[7486].get('prerequisiteAll'))

    def test_supplied_ledger_is_delivery_not_farming(self):
        quests = copy.deepcopy(self.quests)
        apply_corrections(quests)
        apply_stage_corrections(quests)
        q = quests[8575]
        self.assertFalse(q['requirements'])
        self.assertFalse(q['objectives'])
        self.assertFalse(q.get('objectiveLocationsIncomplete'))
        self.assertEqual(q['providedItems'][0]['entityID'], 20949)

    def test_hippogryph_feather_has_captured_local_sources(self):
        alternatives = self.quests[3381]['objectiveAlternatives']
        self.assertEqual(len(alternatives), 7)
        self.assertEqual({p['entityID'] for alt in alternatives for p in alt['locations']},
                         {6375, 6377, 6378, 6379, 6380, 6648, 223068})
        self.assertTrue(all(p['mapID'] == 1447 and p['sourceAreaID'] == 16
                            for alt in alternatives for p in alt['locations']))

    def test_delivery_correction_keeps_unrelated_missing_work_visible(self):
        quests = copy.deepcopy(self.quests)
        apply_corrections(quests)
        quests[8575]['missingRequirements'] = [
            {'entityType': 'npc', 'entityID': 999999, 'name': 'unrelated objective'}]
        with self.assertRaises(ValueError):
            apply_stage_corrections(quests)

    def test_aq_campaign_stays_out_of_leveling_and_unknowns_stay_unknown(self):
        for quest_id in (8288, 8305, 8729):
            self.assertTrue(self.quests[quest_id].get('levelingExcluded'))
        for quest_id in (3381, 6821, 6822, 6824):
            q = self.quests[quest_id]
            self.assertTrue(q.get('objectiveLocationsIncomplete') or
                            not q.get('starts') or not q.get('ends') or
                            bool(q.get('missingRequirements')))


if __name__ == '__main__':
    unittest.main()
