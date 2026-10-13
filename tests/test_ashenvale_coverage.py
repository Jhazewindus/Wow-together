"""Ashenvale data regressions; validate routes in game before trusting terrain."""
import copy
import unittest

from test_addon import Client, ROOT

import sys
sys.path.insert(0, str(ROOT / 'tools'))
from build_quest_dataset import own_lua
from import_warcraftdb import apply_corrections


class AshenvaleCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = own_lua(ROOT / 'WowTogether_QuestData/QuestCatalogue.lua', 'catalogue')['quests']

    def test_escape_choices_are_mutually_exclusive_and_share_the_proven_gate(self):
        force, stealth = self.records[994], self.records[995]
        self.assertEqual(force['prerequisiteAny'], [993])
        self.assertEqual(stealth['prerequisiteAny'], [993])
        self.assertEqual(force['exclusiveQuests'], [995])
        self.assertEqual(stealth['exclusiveQuests'], [994])
        self.assertEqual(force['starts'][0]['entityID'], stealth['starts'][0]['entityID'])
        self.assertEqual(force['ends'][0]['entityID'], stealth['ends'][0]['entityID'])

    def test_shandrina_handoff_has_both_item_objectives(self):
        quest = self.records[86757]
        self.assertEqual((quest['starts'][0]['entityID'], quest['ends'][0]['entityID']), (3955, 3955))
        self.assertEqual({(p['itemID'], p['quantity'], p['entityID']) for p in quest['objectives']},
                         {(279505, 6, 11682), (279507, 4, 11680)})
        self.assertTrue(all(p['mapID'] == 1440 for p in quest['objectives']))

    def test_battleground_care_packages_are_tiered_and_dailies_are_not_leveling_stops(self):
        for ident, alternatives in ((7863, {7864, 7865}), (7864, {7863, 7865}),
                                    (7865, {7863, 7864}), (7866, {7867, 7868}),
                                    (7867, {7866, 7868}), (7868, {7866, 7867})):
            quest = self.records[ident]
            self.assertEqual(set(quest['exclusiveQuests']), alternatives)
            self.assertTrue(quest['pickupRequiresOffer'])
        for ident in (79090, 79098):
            self.assertEqual(self.records[ident]['levelingExcluded'], 'Daily repeatable PvP quest')

    def test_kor_gem_keeps_published_class_and_race_mask_and_unknown_quantity(self):
        quest = self.records[95042]
        self.assertEqual((quest['side'], quest['classMask'], quest['raceMask']), ('Horde', 2, 16))
        self.assertTrue(quest['requirements'][0]['quantityUnknown'])

    def test_reviewed_identity_and_exclusive_corrections_are_idempotent_and_guarded(self):
        records = {ident: copy.deepcopy(self.records[ident]) for ident in (95042, 994, 995)}
        original = copy.deepcopy(records)
        apply_corrections(records)
        self.assertEqual(records, original)
        self.assertEqual(records[95042]['raceMask'], 16)
        bad = copy.deepcopy(records)
        bad[95042]['raceMask'] = 32
        with self.assertRaises(ValueError):
            apply_corrections(bad)

    def test_dailies_do_not_restore_ordinary_51_60_ashenvale_guides(self):
        client = Client(quests=(), use_catalogue=True)
        client.guide_environment(level=55)
        client.ns.profile.faction = 'Horde'
        client.ns.db.config.classQuests = False
        client.ns.ReadProfile()
        guides = [g for g in client.ns.LevelingGuideChoices().values() if g.zone == 'Ashenvale']
        self.assertFalse(guides)


if __name__ == '__main__':
    unittest.main()
