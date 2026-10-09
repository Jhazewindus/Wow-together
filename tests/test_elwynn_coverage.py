"""Reviewed Elwynn facts; native beta offers and terrain still need players."""
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
from apply_quest_stage_corrections import apply


def client(class_id=1, level=10):
    c = Client(quests=(), use_catalogue=True)
    c.guide_environment(level=level)
    identity(c)
    c.lua.execute("function UnitRace() return 'Human','Human',1 end; "
                  "function UnitFactionGroup() return 'Alliance','Alliance' end; "
                  "function UnitClass() return 'Test','TEST'," + str(class_id) + " end")
    c.lua.globals().grouped = False
    c.ns.ReadProfile(); c.ns.UpdateRoster()
    c.ns.SetOption('classQuests', True)
    return c


class ElwynnFactsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.quests = own_lua(ROOT / 'WowTogether/QuestCatalogue.lua', 'catalogue')['quests']

    def test_supplied_letters_keep_handin_items_and_mapped_speech(self):
        for ident, item in ((2205, 7674), (3100, 9542), (3102, 9555)):
            c = client(4 if ident != 3100 else 1)
            q = self.quests[ident]
            self.assertFalse(q.get('requirements'))
            self.assertFalse(q.get('objectiveLocationsIncomplete'))
            self.assertEqual([(r['itemID'], r['quantity']) for r in q['requiredItems']], [(item, 1)])
            self.assertEqual(q['providedItems'][0]['entityID'], item)
            g = guide(c, (ident,)); g.fixedRoute = True
            c.ns.GenerateFixedGuide(g, False)
            work = next(s for s in g.fixedPlan.values() if s.id == ident and s.kind == 'q')
            self.assertEqual(work.action, 'talk')
            self.assertFalse(work.unknownLocation)
            self.assertTrue(c.ns.GuideStepAction(work).startswith('Speak to '))
        self.assertEqual((q['ends'][0]['x'], q['ends'][0]['y']), (.504, .398))

    def test_heads_require_one_item_and_keep_foreign_work_and_unknown_unlocks(self):
        for ident, item, npc, map_id in ((1678, 6799, 6113, 1426), (1683, 6805, 6128, 1438)):
            q = self.quests[ident]
            self.assertEqual([(r['itemID'], r['quantity']) for r in q['requiredItems']], [(item, 1)])
            self.assertEqual(q['requirements'][0]['quantity'], 1)
            point = q['objectives'][0]
            self.assertEqual((point['itemID'], point['quantity'], point['entityID'], point['mapID']),
                             (item, 1, npc, map_id))
            self.assertNotIn('quantityUnknown', point)
            self.assertTrue(q['prerequisitesUnverified'])
            self.assertEqual(q['classMask'], 1)
            self.assertNotIn('exclusiveQuests', q)

    def test_bartleby_is_a_duel_without_an_invented_count(self):
        c = client(); g = guide(c, (1640,)); g.fixedRoute = True
        c.ns.GenerateFixedGuide(g, False)
        stop = next(s for s in g.fixedPlan.values() if s.id == 1640 and s.kind == 'q')
        self.assertEqual(c.ns.GuideStepAction(stop), 'Complete the duel with Bartleby')
        self.assertTrue(stop.quantityUnknown)
        self.assertIsNone(stop.quantity)
        self.assertEqual(set(c.ns.CatalogueQuest(1640).prerequisiteAny.values()), {1639, 1678, 1683})

    def test_applejack_exchange_is_optional_acquisition_not_a_forced_repeatable(self):
        c = client(); q = c.ns.CatalogueQuest(91738)
        self.assertIsNone(q.previousQuest)
        self.assertIsNone(q.prerequisiteAny)
        self.assertEqual((q.requiredItems[1].itemID, q.requiredItems[1].quantity), (247824, 1))
        g = guide(c, (91738,)); g.fixedRoute = True
        c.ns.GenerateFixedGuide(g, False)
        stop = next(s for s in g.fixedPlan.values() if s.kind == 'q')
        self.assertEqual((stop.entityID, stop.mapID, stop.x, stop.y), (562131, 1429, .245, .582))
        self.assertIn('exchange 4 Shiny Red Apples at Applejack Still', c.ns.GuideStepAction(stop))
        self.assertIsNone(c.ns.GuideItemProgress(stop, c.ns.self, 1))
        c.ns.active[91738] = q.title
        c.lua.execute('C_Item={GetItemCount=function(id) if id==247824 then return 1 else return 4 end end}')
        self.assertTrue(c.ns.GuideItemProgress(stop, c.ns.self, 1).finished)
        self.assertFalse(c.ns.Completed(91738))
        c.lua.execute('C_Item.GetItemCount=function() return 0 end')
        self.assertFalse(c.ns.GuideItemProgress(stop, c.ns.self, 1).finished)

    def test_corrections_are_idempotent_and_conflicts_are_atomic(self):
        rows = copy.deepcopy(self.quests)
        self.assertEqual(apply_stage_corrections(rows), [])
        self.assertEqual(rows, self.quests)
        for ident, field in ((1678, 'requirements'), (1640, 'objectives'), (91738, 'objectives'), (3102, 'ends')):
            rows = copy.deepcopy(self.quests)
            rows[ident][field][0]['entityID'] = 999999
            before = copy.deepcopy(rows)
            with self.subTest(quest=ident), self.assertRaises(ValueError):
                apply_stage_corrections(rows)
            self.assertEqual(rows, before)

    def test_placeholder_is_excluded_without_deleting_source_gaps(self):
        q = self.quests[7962]
        self.assertEqual(q['levelingExcluded'], 'Historical testing-only quest')
        self.assertFalse(q.get('starts'))
        self.assertFalse(q.get('ends'))
        self.assertTrue(q['objectiveLocationsIncomplete'])
        self.assertTrue(self.quests[91753]['objectiveLocationsIncomplete'])
        self.assertFalse(self.quests[95771]['objectives'])
        for ident in (95771, 91753):
            self.assertNotIn('levelingExcluded', self.quests[ident])
        self.assertIn(1, self.quests[91753]['allowedRaceIDs'])

    def test_packed_changes_are_only_the_reviewed_eight_records(self):
        review = json.loads((ROOT / 'research/elwynn-forest-2026-10-08/record-changes.json').read_text())
        self.assertEqual(set(review['changed_quest_ids']), {1640, 1678, 1683, 2205, 3100, 3102, 7962, 91738})
        self.assertEqual(apply(ROOT / 'WowTogether'), [])


class ElwynnGuideTests(unittest.TestCase):
    def test_letters_wait_for_actual_kobold_cleanup_handin(self):
        c = client(); c.ns.active[7] = 'Kobold Camp Cleanup'; c.ns.readyToTurnIn[7] = True
        self.assertFalse(c.ns.CataloguePrerequisitesAllowed(3100, c.ns.self)[0])
        c.lua.globals().finished[7] = True
        self.assertTrue(c.ns.CataloguePrerequisitesAllowed(3100, c.ns.self))

    def test_class_setting_filters_effective_route_without_recompiling_scope(self):
        c = client(); c.lua.globals().finished[7] = True
        c.ns.active[3100] = 'Simple Letter'
        c.lua.globals().playerLevel = 5
        c.ns.ReadProfile(); c.ns.UpdateRoster()
        g = guide(c, (47, 3100)); g.fixedRoute = True
        route = c.ns.BuildFixedGuideRoute(g, False)
        before = order(g)
        self.assertIn(3100, {s.id for s in route.previewStops.values()})
        c.ns.SetOption('classQuests', False)
        route = c.ns.BuildFixedGuideRoute(g, False)
        self.assertNotIn(3100, {s.id for s in route.previewStops.values()})
        self.assertIn(47, {s.id for s in route.previewStops.values()})
        self.assertEqual(order(g), before)
        self.assertFalse(c.ns.GuideQuestSkipped(3100))

    def test_complete_human_scope_and_mid_progress_keep_fixed_order(self):
        for class_id in (1, 4, 8):
            c = client(class_id, level=1)
            g = next(g for g in c.ns.LevelingGuideChoices().values()
                     if g.key == 'level-zone:eastern-kingdoms/elwynn-forest:levels:1-10')
            c.ns.BuildGuideRoute(g, False)
            before = order(g); planned = {s.id for s in g.fixedPlan.values()}
            self.assertTrue({7, 47, 60, 91738, 95771}.issubset(planned))
            self.assertNotIn(7962, planned)
            self.assertTrue({r.id for r in g.records.values()}.issubset(planned))
            c.lua.globals().finished[7] = True
            c.ns.active[47] = 'Gold Dust Exchange'
            c.lua.globals().playerLevel = 10
            c.ns.ReadProfile(); c.ns.UpdateRoster()
            c.ns.BuildGuideRoute(g, False)
            self.assertEqual(order(g), before)

    def test_hogger_retains_elite_facts_pending_shared_chapter_fix(self):
        q = ElwynnFactsTests.quests[176]
        self.assertEqual((q['level'], q['minLevel'], q['questType']), (11, 5, 'Elite'))
        self.assertNotIn('levelingExcluded', q)
        self.assertEqual((q['objectives'][0]['entityID'], q['objectives'][0]['quantity']), (448, 1))


if __name__ == '__main__':
    unittest.main()
