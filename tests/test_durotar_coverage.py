"""Reviewed Durotar facts and full guide behavior under Lua 5.1."""
import copy
import sys
import unittest

from test_addon import Client, ROOT
from test_089 import identity
from test_063 import order
from test_routes import guide

sys.path.insert(0, str(ROOT / 'tools'))
from build_quest_dataset import own_lua
from import_warcraftdb import apply_stage_corrections

DELIVERIES = {1518: 6656, 1521: 6656, 1524: 6653, 1527: 6654}


def client():
    c = Client(quests=(), use_catalogue=True)
    c.guide_environment(level=12)
    c.lua.globals().grouped = False
    identity(c)
    c.ns.UpdateRoster()
    return c


class DurotarStageFactsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.quests = own_lua(ROOT / 'WowTogether/QuestCatalogue.lua', 'catalogue')['quests']

    def test_delivery_items_remain_required_and_are_not_farming_objectives(self):
        for ident, item in DELIVERIES.items():
            q = self.quests[ident]
            with self.subTest(quest=ident):
                self.assertFalse(q.get('requirements'))
                self.assertFalse(q.get('missingRequirements'))
                self.assertFalse(q.get('objectiveLocationsIncomplete'))
                self.assertEqual([(r['itemID'], r['quantity']) for r in q['requiredItems']], [(item, 1)])
                self.assertIn(item, [r['entityID'] for r in q['providedItems']])
                self.assertEqual(q['classMask'], 64)

    def test_fire_work_preserves_tar_and_adds_the_explicit_pouch_drop(self):
        q = self.quests[1525]
        points = {p['itemID']: p for p in q['objectives']}
        self.assertEqual(set(points), {5026, 6652})
        self.assertEqual((points[5026]['entityID'], points[5026]['mapID']), (3267, 1413))
        self.assertEqual((points[6652]['entityID'], points[6652]['mapID']), (3199, 1411))
        self.assertEqual((points[6652]['x'], points[6652]['y']), (.518, .258))
        self.assertEqual(points[6652]['action'], 'loot')
        self.assertTrue(all(p['quantity'] == 1 for p in points.values()))
        self.assertEqual(q['prerequisiteAny'], [1524])
        self.assertFalse(q.get('missingRequirements'))

    def test_reapplication_is_idempotent_and_cannot_erase_new_work(self):
        rows = copy.deepcopy(self.quests)
        self.assertEqual(apply_stage_corrections(rows), [])
        for key, value in (('title', 'Different quest'), ('classMask', 0),
                           ('objectives', [{'name': 'New independent work'}]),
                           ('otherLocationsIncomplete', True)):
            rows = {1518: copy.deepcopy(self.quests[1518])}
            rows[1518][key] = value
            before = copy.deepcopy(rows)
            with self.subTest(field=key), self.assertRaises(ValueError):
                apply_stage_corrections(rows)
            self.assertEqual(rows, before)

    def test_conflicting_location_does_not_replace_existing_evidence(self):
        rows = {1525: copy.deepcopy(self.quests[1525])}
        rows[1525]['objectives'][-1]['x'] = .9
        before = copy.deepcopy(rows)
        with self.assertRaises(ValueError):
            apply_stage_corrections(rows)
        self.assertEqual(rows, before)

    def test_unresolved_and_edition_facts_remain_explicit(self):
        for ident in (785, 96873, 96874, 99123):
            q = self.quests[ident]
            self.assertTrue(not q.get('starts') or q.get('objectiveLocationsIncomplete'))
        self.assertTrue(self.quests[787]['pickupRequiresOffer'])
        self.assertIn(2, self.quests[787]['allowedRaceIDs'])
        self.assertIn(8, self.quests[787]['allowedRaceIDs'])
        self.assertTrue(self.quests[5843]['levelingExcluded'])


class DurotarGuideBehaviorTests(unittest.TestCase):
    def test_unmapped_escort_names_the_npc_and_stays_adjacent_to_acceptance(self):
        c = client()
        g = guide(c, (99123, 4402, 5441)); g.fixedRoute = True
        c.ns.GenerateFixedGuide(g, False)
        plan = list(g.fixedPlan.values())
        index = next(i for i, s in enumerate(plan) if s.id == 99123 and s.kind == 'q')
        stop = plan[index]
        self.assertEqual((plan[index - 1].id, plan[index - 1].kind), (99123, 'a'))
        self.assertTrue(stop.unknownLocation)
        self.assertIsNone(stop.x)
        self.assertIsNone(stop.quantity)
        self.assertEqual(c.ns.GuideStepAction(stop), "Escort Pal'juh")

    def test_real_handins_unlock_scorpid_and_either_medallion_branch(self):
        for parent, child in ((788, 789), (792, 794), (1499, 794)):
            c = client()
            c.ns.active[parent] = c.ns.CatalogueQuest(parent).title
            c.ns.readyToTurnIn[parent] = True
            c.ns.offered[child] = True
            with self.subTest(parent=parent):
                self.assertFalse(c.ns.CataloguePrerequisitesAllowed(child, c.ns.self)[0])
                c.ns.handlers.QUEST_TURNED_IN(parent)
                c.lua.globals().finished[parent] = True
                self.assertTrue(c.ns.CataloguePrerequisitesAllowed(child, c.ns.self))

    def test_corrected_deliveries_keep_accept_work_and_handin_in_full_preview(self):
        c = client()
        g = guide(c, tuple(DELIVERIES)); g.fixedRoute = True
        c.ns.GenerateFixedGuide(g, False)
        for ident in DELIVERIES:
            stages = [s for s in g.fixedPlan.values() if s.id == ident]
            self.assertEqual([s.kind for s in stages], ['a', 'q', 't'])
            self.assertFalse(any(s.unknownLocation for s in stages))
            self.assertEqual((stages[1].mapID, stages[1].x, stages[1].y),
                             (stages[2].mapID, stages[2].x, stages[2].y))
            self.assertEqual(stages[1].action, 'talk')
            self.assertEqual(c.ns.GuideStepAction(stages[1]), 'Speak to ' + stages[1].npcName)

    def test_pouch_instruction_uses_item_and_mob_without_research_text(self):
        c = client()
        g = guide(c, (1525,)); g.fixedRoute = True
        c.ns.GenerateFixedGuide(g, False)
        stop = next(s for s in g.fixedPlan.values() if s.itemID == 6652 and s.kind == 'q')
        self.assertEqual(stop.quantity, 1)
        self.assertIn('Reagent Pouch', c.ns.GuideStepAction(stop))
        self.assertEqual(stop.npcName, 'Burning Blade Cultist')
        self.assertNotIn('baseline', c.ns.GuideStepAction(stop))

    def test_class_parchments_and_shaman_steps_keep_the_existing_opt_out(self):
        c = client()
        for ident, mask in ((2383, 1), (3087, 4), (3088, 8), (3089, 64), (3090, 256), (98576, 128)):
            self.assertEqual(c.ns.CatalogueQuest(ident).classMask, mask)
        c.ns.SetOption('classQuests', False)
        self.assertFalse(c.ns.ClassQuestEnabled(1525))
        self.assertTrue(c.ns.ClassQuestEnabled(788))
        c.ns.SetOption('classQuests', True)
        self.assertTrue(c.ns.ClassQuestEnabled(1525))
        c.ns.profile.classID = 1
        self.assertFalse(c.ns.CatalogueIdentityAllowed(1525, c.ns.profile)[0])
        c.ns.profile.classID, c.ns.profile.faction = 7, 'Alliance'
        self.assertFalse(c.ns.CatalogueIdentityAllowed(1525, c.ns.profile)[0])

    def test_zone_compilation_keeps_edition_out_and_mid_progress_order(self):
        c = client(); c.ns.guideLevel = '1-10'
        g = next(g for g in c.ns.LevelingGuideChoices().values()
                 if g.key == 'level-zone:kalimdor/durotar:levels:1-10')
        c.ns.BuildGuideRoute(g, False)
        before = order(g)
        self.assertTrue({r.id for r in g.records.values()}.issubset({s.id for s in g.fixedPlan.values()}))
        self.assertNotIn(5843, {s.id for s in g.fixedPlan.values()})
        self.assertTrue({4402, 5441, 788, 789, 792, 794}.issubset({s.id for s in g.fixedPlan.values()}))
        c.ns.active[1518] = 'Call of Earth'
        c.lua.globals().finished[788] = True
        c.ns.BuildGuideRoute(g, False)
        self.assertEqual(order(g), before)


if __name__ == '__main__':
    unittest.main()
