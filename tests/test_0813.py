"""Guide completion requires quest history, independently of runtime filters.

Lua 5.1 host checks reproduce false completion; they do not certify beta APIs.
"""
import unittest

from test_addon import Client
from test_063 import guide_client, zone, order
from test_066 import reload
from test_routes import map_canvas


def start(c):
    g = zone(c)
    c.ns.ActivateRoute(g)
    return g


class GuideCompletionTests(unittest.TestCase):
    def test_level_filters_do_not_complete_unfinished_guide(self):
        for level in (5, 23):
            with self.subTest(level=level):
                c = guide_client(2); g = start(c); before = order(g)
                c.lua.globals().playerLevel = level; c.ns.ReadProfile()
                c.ns.UpdateFixedGuideRoute(g)
                self.assertIsNone(c.ns.selectedRoute.complete)
                self.assertEqual(len(c.ns.selectedRoute.stops), 0)
                self.assertEqual(c.ns.selectedRoute.remainingSteps, 6)
                self.assertEqual(c.ns.selectedRoute.completionProgress.unfinished, 2)
                self.assertIn('outside your leveling range', c.ns.routePaused)
                self.assertEqual(order(g), before)
                self.assertFalse(c.ns.Completed(900))

    def test_finishing_current_band_does_not_finish_later_quests(self):
        c = guide_client(3); c.ns.catalogue.quests[902].level = 20
        g = start(c); before = order(g)
        c.lua.execute('finished[900]=true; finished[901]=true')
        c.ns.UpdateFixedGuideRoute(g)
        self.assertIsNone(c.ns.selectedRoute.complete)
        self.assertEqual(c.ns.selectedRoute.completionProgress.completed, 2)
        self.assertEqual(c.ns.selectedRoute.completionProgress.unfinished, 1)
        c.lua.globals().playerLevel = 20; c.ns.ReadProfile(); c.ns.Refresh()
        self.assertEqual({s.id for s in c.ns.selectedRoute.stops.values()}, {902})
        self.assertEqual(order(g), before)
        self.assertIsNone(c.ns.routePaused)

    def test_skipping_every_step_does_not_confirm_quest_completion(self):
        c = guide_client(2); g = start(c)
        for s in g.fixedPlan.values():
            steps = c.ns.db.guideSkips[c.ns.self].steps
            if steps[s.id] is None: steps[s.id] = c.lua.table()
            steps[s.id][c.ns.GuideStepKey(s)] = True
        c.ns.Refresh()
        self.assertIsNone(c.ns.selectedRoute.complete)
        self.assertEqual(c.ns.selectedRoute.remainingSteps, 0)
        self.assertEqual(c.ns.selectedRoute.completionProgress.unfinished, 2)
        self.assertIn('skipped', c.ns.routePaused)
        c.ns.ResetGuideSkips()
        self.assertEqual(len(c.ns.selectedRoute.stops), 6)

    def test_skipped_quests_remain_distinct_and_reload_safe(self):
        c = guide_client(2); g = start(c)
        c.ns.db.guideSkips[c.ns.self].quests[900] = True
        c.ns.db.guideSkips[c.ns.self].quests[901] = True
        c.ns.Refresh()
        self.assertIsNone(c.ns.selectedRoute.complete)
        self.assertEqual(c.ns.selectedRoute.completionProgress.skipped, 2)
        fresh = reload(c)
        self.assertIsNone(fresh.ns.selectedRoute.complete)
        self.assertIn('skipped', fresh.ns.routePaused)
        self.assertEqual(order(fresh.ns.routeSelection), order(g))

    def test_true_completion_preserves_summary_and_waits_for_turn_in(self):
        c = guide_client(2); g = start(c)
        c.ns.active[900] = 'Quest 0'; c.ns.readyToTurnIn[900] = True
        c.lua.globals().finished[901] = True
        c.ns.Refresh()
        self.assertIsNone(c.ns.selectedRoute.complete)
        self.assertEqual([s.kind for s in c.ns.selectedRoute.stops.values()], ['t'])
        c.ns.active[900] = None; c.lua.globals().finished[900] = True
        c.ns.Refresh()
        self.assertTrue(c.ns.selectedRoute.complete)
        self.assertTrue(c.ns.selectedRoute.fixed)
        self.assertEqual(c.ns.selectedRoute.totalSteps, 6)
        self.assertEqual(c.ns.selectedRoute.completionProgress.completed, 2)
        self.assertEqual(c.ns.selectedRoute.completionProgress.unfinished, 0)

    def test_missing_plan_and_unknown_history_do_not_complete(self):
        c = guide_client(2); g = start(c)
        g.fixedPlan = c.lua.table()
        c.lua.execute('C_QuestLog.IsQuestFlaggedCompleted=function() return nil end')
        c.ns.Refresh()
        self.assertIsNone(c.ns.selectedRoute.complete)
        self.assertEqual(c.ns.selectedRoute.completionProgress.unknown, 2)
        self.assertIn('steps are unavailable', c.ns.routePaused)

    def test_elite_work_is_waiting_when_solo_and_can_return_in_party(self):
        c = guide_client(2); g = start(c); before = order(g)
        for q in c.ns.catalogue.quests.values(): q.questType = 'Elite'
        c.ns.Refresh()
        self.assertIsNone(c.ns.selectedRoute.complete)
        self.assertEqual(c.ns.selectedRoute.remainingSteps, 6)
        self.assertIn('need a group', c.ns.routePaused)
        c.lua.globals().grouped = True
        c.unit_names({'player': ['Alice', 'TestRealm'], 'party1': ['Bob', 'TestRealm']})
        c.receive('1|S|1|1|1|')
        c.receive('1|P|12|2|501|Test Coast')
        c.receive('1|C|2|1|1|')
        c.receive('1|K|2|1|1|900,901')
        c.ns.Refresh()
        self.assertEqual({s.id for s in c.ns.selectedRoute.stops.values()}, {900, 901})
        self.assertEqual(order(g), before)

    def test_shipped_hillsbrad_unfinished_filtered_quests_are_not_complete(self):
        unfinished = {539, 509, 546}  # Three quest titles visible in the report.
        c = Client(quests=unfinished, use_catalogue=True)
        c.guide_environment(level=35)
        c.lua.globals().grouped, c.lua.globals().peer = False, None
        c.ns.UpdateRoster(); map_canvas(c); c.ns.guideLevel = 'all'
        g = next(g for g in c.ns.LevelingGuideChoices().values()
                 if g.key == 'level-zone:eastern-kingdoms/hillsbrad-foothills')
        self.assertTrue(unfinished.issubset({r.id for r in g.records.values()}))
        for r in g.records.values():
            if r.id not in unfinished: c.lua.globals().finished[r.id] = True
        c.ns.ActivateRoute(g); before = order(g); c.ns.Refresh()
        self.assertIsNone(c.ns.selectedRoute.complete)
        self.assertEqual(c.ns.selectedRoute.completionProgress.unfinished, 3)
        self.assertEqual(len(c.ns.selectedRoute.stops), 0)
        self.assertIn('outside your leveling range', c.ns.routePaused)
        c.ns.ScanGuideProgress(); c.drain()
        self.assertEqual(order(c.ns.routeSelection), before)
        self.assertIsNone(c.ns.selectedRoute.complete)
        c.ns.Diagnostics()
        self.assertIn('3 unfinished', c.ns.diagnosticsText.text)

    def test_reported_level_24_hillsbrad_keeps_souvenirs_and_later_work(self):
        c = Client(quests=(539, 509, 546), use_catalogue=True)
        c.guide_environment(level=24)
        c.lua.globals().grouped, c.lua.globals().peer = False, None
        c.ns.UpdateRoster(); map_canvas(c)
        c.ns.profile.classID, c.ns.profile.raceID = 7, 96
        g = next(g for g in c.ns.LevelingGuideChoices().values()
                 if g.key == 'level-zone:eastern-kingdoms/hillsbrad-foothills')
        for r in g.records.values():
            if r.id not in (539, 509, 546): c.lua.globals().finished[r.id] = True
        c.ns.ActivateRoute(g); c.ns.Refresh(); before = order(g)
        self.assertIsNone(c.ns.selectedRoute.complete)
        self.assertEqual({s.id for s in c.ns.selectedRoute.stops.values()}, {546})
        self.assertEqual(c.ns.selectedRoute.completionProgress.unfinished, 3)
        c.ns.db.guideSkips[c.ns.self].quests[546] = True
        c.ns.Refresh()
        self.assertIsNone(c.ns.selectedRoute.complete)
        self.assertEqual(c.ns.selectedRoute.completionProgress.skipped, 1)
        c.lua.globals().playerLevel = 28; c.ns.ReadProfile(); c.ns.Refresh()
        self.assertEqual({s.id for s in c.ns.selectedRoute.stops.values()}, {539, 509})
        self.assertEqual(order(g), before)

    def test_hover_tooltip_follows_loading_and_completion_state(self):
        c = guide_client(2); g = start(c)
        c.lua.execute('''GameTooltip = {lines={}}
            function GameTooltip:SetOwner(owner) self.owner=owner; self.lines={} end
            function GameTooltip:IsOwned(owner) return self.owner==owner end
            function GameTooltip:ClearLines() self.lines={} end
            function GameTooltip:AddLine(text) self.lines[#self.lines+1]=text end
            function GameTooltip:Show() self.shown=true end
            function GameTooltip:Hide() self.shown=false; self.owner=nil end''')
        c.ns.routePlanning = c.lua.table_from({'guide': g})
        c.ns.UpdateNavigation(); c.ns.navigation.OnEnter(c.ns.navigation)
        tooltip = c.lua.globals().GameTooltip
        self.assertIn('Loading route', '\n'.join(tooltip.lines.values()))
        c.ns.routePlanning = None
        c.lua.execute('finished[900]=true; finished[901]=true')
        c.ns.Refresh()
        text = '\n'.join(tooltip.lines.values())
        self.assertNotIn('Loading route', text)
        self.assertIn('Guide complete', text)


if __name__ == '__main__':
    unittest.main()
