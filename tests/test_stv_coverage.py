"""Stranglethorn data regressions; native offers and approaches need players."""
import copy
import json
import sys
import unittest

from test_addon import Client, ROOT
from test_089 import identity
from test_063 import order
from test_routes import guide

sys.path.insert(0, str(ROOT / 'tools'))
from build_quest_dataset import own_lua
from import_warcraftdb import apply_stage_corrections


def client(faction='Horde', class_id=9, level=40):
    c = Client(quests=(), use_catalogue=True)
    c.guide_environment(level=level); identity(c)
    race = 2 if faction == 'Horde' else 1
    c.lua.execute("function UnitFactionGroup() return '" + faction + "' end; "
                  "function UnitClass() return 'Test','TEST'," + str(class_id) + " end; "
                  "function UnitRace() return 'Test','Test'," + str(race) + " end")
    c.lua.globals().grouped = False
    c.ns.ReadProfile(); c.ns.UpdateRoster(); c.ns.SetOption('classQuests', True)
    return c


class StranglethornFactsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.quests = own_lua(ROOT / 'WowTogether/QuestCatalogue.lua', 'catalogue')['quests']

    def test_supplied_cross_zone_deliveries_retain_required_items(self):
        for ident, item in ((3511, 10610), (3621, 10738)):
            q = self.quests[ident]
            self.assertFalse(q.get('requirements'))
            self.assertFalse(q.get('objectiveLocationsIncomplete'))
            self.assertEqual([(r['itemID'], r['quantity']) for r in q['requiredItems']], [(item, 1)])
            self.assertEqual(q['providedItems'][0]['entityID'], item)
            self.assertTrue(all(p['action'] == 'talk' for p in q['ends']))
        self.assertEqual(self.quests[3511]['prerequisiteAny'], [3510])
        self.assertEqual(self.quests[3621]['prerequisiteAny'], [3602])

    def test_yenniku_uses_the_supplied_gem_without_inventing_a_kill(self):
        c = client(); g = guide(c, (592,)); g.fixedRoute = True
        c.ns.GenerateFixedGuide(g, False)
        s = next(s for s in g.fixedPlan.values() if s.kind == 'q')
        self.assertEqual((s.entityID, s.itemID, s.quantity), (2530, 3913, 1))
        self.assertEqual(c.ns.GuideStepAction(s), 'Use Soul Gem on Yenniku')
        self.assertEqual(c.ns.CatalogueQuest(592).requiredItems[1].itemID, 3913)
        c.ns.active[592] = 'Saving Yenniku'
        c.lua.execute('C_Item={GetItemCount=function() return 1 end}')
        self.assertIsNone(c.ns.GuideItemProgress(s, c.ns.self, 1))
        self.assertFalse(c.ns.Completed(592))

    def test_chest_quantity_and_current_captain_point_keep_elite_work(self):
        q = self.quests[8551]
        self.assertEqual(q['questType'], 'Elite')
        self.assertEqual([(r['itemID'], r['quantity']) for r in q['requiredItems']], [(3932, 1)])
        self.assertEqual((q['objectives'][0]['entityID'], q['objectives'][0]['quantity']), (1492, 1))
        for role in ('starts', 'ends'):
            self.assertAlmostEqual(q[role][0]['x'], .266)
            self.assertAlmostEqual(q[role][0]['y'], .734)
        self.assertIsNotNone(client().ns.QuestGroupWarning(8551))

    def test_current_captain_ids_are_distinct_and_old_variants_remain_unmapped(self):
        for ident in (614, 615, 618, 620):
            self.assertFalse(self.quests[ident].get('starts'))
            self.assertFalse(self.quests[ident].get('ends'))
        self.assertEqual(self.quests[8552]['startRefs'][0]['entityID'], 3985)
        self.assertFalse(self.quests[8552].get('starts'))
        self.assertEqual(self.quests[8552]['ends'][0]['entityID'], 2500)
        self.assertEqual(self.quests[8553]['starts'][0]['entityID'], 2500)
        self.assertEqual(self.quests[8553]['ends'][0]['entityID'], 2594)
        self.assertEqual(self.quests[8553]['objectives'][0]['action'], 'talk')
        for ident in (8552, 8553, 8554):
            self.assertTrue(self.quests[ident].get('prerequisitesUnverified') or
                            not self.quests[ident].get('prerequisitesRead'))
            self.assertEqual(self.quests[ident]['minLevel'], 35)

    def test_negolash_lure_is_not_faked_by_mapping_a_giver_or_spawn(self):
        q = self.quests[8554]
        self.assertEqual(q['questType'], 'Elite')
        self.assertEqual((q['starts'][0]['entityID'], q['ends'][0]['entityID']), (2594, 2500))
        self.assertEqual([(r['itemID'], r['quantity']) for r in q['requiredItems']], [(3935, 1)])
        self.assertFalse(q['objectives'])
        self.assertTrue(q['objectiveLocationsIncomplete'])
        self.assertEqual(q['missingRequirements'][0]['entityID'], 3935)

    def test_green_hills_reward_candidate_is_withheld_without_dropping_pages(self):
        q = self.quests[338]
        self.assertFalse(q['objectives'])
        self.assertTrue(q['objectiveLocationsIncomplete'])
        self.assertEqual({r['itemID'] for r in q['requiredItems']}, {2756, 2757, 2758, 2759})
        self.assertEqual(sum(len(self.quests[i]['requiredItems']) for i in (339, 340, 341, 342)), 15)
        self.assertFalse(self.quests[1796]['objectives'])
        self.assertTrue(self.quests[1036]['unmodeledObjectiveKinds'])

    def test_staging_is_atomic_idempotent_and_rejects_conflicting_new_facts(self):
        rows = copy.deepcopy(self.quests)
        self.assertEqual(apply_stage_corrections(rows), [])
        self.assertEqual(rows, self.quests)
        for ident, role in ((8553, 'starts'), (592, 'objectives'), (8551, 'ends')):
            rows = copy.deepcopy(self.quests); rows[ident][role][0]['x'] = .9
            invalid = copy.deepcopy(rows)
            with self.subTest(quest=ident), self.assertRaises(ValueError):
                apply_stage_corrections(rows)
            self.assertEqual(rows, invalid)
        rows = copy.deepcopy(self.quests); rows[8554]['requiredItems'][0]['quantity'] = 2
        invalid = copy.deepcopy(rows)
        with self.assertRaises(ValueError): apply_stage_corrections(rows)
        self.assertEqual(rows, invalid)


class StranglethornGuideTests(unittest.TestCase):
    def test_named_unknown_escort_stays_adjacent_and_waits_for_actual_parent_handin(self):
        c = client(); g = guide(c, (97329, 97331, 97048)); g.fixedRoute = True
        c.ns.GenerateFixedGuide(g, False)
        stages = list(g.fixedPlan.values())
        i = next(i for i, s in enumerate(stages) if s.id == 97331 and s.kind == 'q')
        self.assertEqual((stages[i-1].id, stages[i-1].kind), (97331, 'a'))
        self.assertEqual(c.ns.GuideStepAction(stages[i]), 'Escort Zimmix Sputterspark')
        self.assertTrue(stages[i].unknownLocation)
        self.assertIsNone(stages[i].quantity)
        c.ns.active[97329] = "Where's the Key?"; c.ns.readyToTurnIn[97329] = True
        self.assertFalse(c.ns.CataloguePrerequisitesAllowed(97331, c.ns.self)[0])
        c.lua.globals().finished[97329] = True
        self.assertTrue(c.ns.CataloguePrerequisitesAllowed(97331, c.ns.self))

    def test_class_quest_setting_preserves_ordinary_work_and_identity_gates(self):
        c = client(); c.ns.SetOption('classQuests', False)
        self.assertFalse(c.ns.ClassQuestEnabled(1796))
        self.assertTrue(c.ns.ClassQuestEnabled(8551))
        c.ns.SetOption('classQuests', True)
        self.assertTrue(c.ns.CatalogueIdentityAllowed(1796, c.ns.profile))
        c.ns.profile.classID = 1
        self.assertFalse(c.ns.CatalogueIdentityAllowed(1796, c.ns.profile)[0])

    def test_faction_chapters_keep_fixed_order_through_mid_quest_progress(self):
        for faction in ('Horde', 'Alliance'):
            c = client(faction); c.ns.guideLevel = 'all'
            guides = [g for g in c.ns.LevelingGuideChoices().values() if g.zone == 'Stranglethorn Vale']
            self.assertEqual({g.key.split(':')[-1] for g in guides}, {'31-40', '41-50', '51-60'})
            for g in guides:
                c.ns.BuildGuideRoute(g, False); before = order(g)
                self.assertTrue({r.id for r in g.records.values()} <= {s.id for s in g.fixedPlan.values()})
                c.ns.active[8553] = "The Captain's Cutlass"; c.lua.globals().finished[8551] = True
                c.ns.BuildGuideRoute(g, False)
                self.assertEqual(order(g), before)


if __name__ == '__main__': unittest.main()
