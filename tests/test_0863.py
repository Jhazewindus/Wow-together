"""Opt-in difficulty range for one fixed guide; real beta rendering needs testing."""
import unittest

from test_063 import guide_client, zone, order, primitive
from test_061 import world_quest
from test_061 import run_plan
from test_066 import reload


def paused(count=2):
    c = guide_client(count)
    g = zone(c)
    for i in range(count):
        c.ns.catalogue.quests[900 + i].level = 30 if i % 2 else 17
    c.lua.globals().playerLevel = 25
    c.ns.ReadProfile()
    c.lua.execute('C_Map.GetMapWorldSize=function()return 1000,1000 end; function GetPlayerFacing()return 0 end')
    c.lua.globals().WorldMapFrame.SetMapID(c.lua.globals().WorldMapFrame, 501)
    c.ns.db.config.fullRoute = True
    c.ns.db.config.classTraining = False
    c.ns.db.config.nearbyFlights = False
    c.ns.db.config.hearthstoneTips = False
    c.ns.ActivateRoute(g)
    c.ns.Refresh()
    c.ns.UpdateNavigation()
    return c, g


class ContinueGuideTests(unittest.TestCase):
    def test_button_resumes_all_difficulty_levels_and_repaints_without_reordering(self):
        c, g = paused()
        before, skips = order(g), primitive(c.ns.db.guideSkips)
        self.assertEqual(len(c.ns.selectedRoute.stops), 0)
        button = c.ns.navigation['continue']
        self.assertTrue(button.IsShown(button))
        self.assertFalse(c.ns.navigation.skipStep.IsShown(c.ns.navigation.skipStep))
        c.ns.window.Hide(c.ns.window)
        c.ns.window.sizing = True
        button.OnClick()
        self.assertEqual({s.id for s in c.ns.selectedRoute.stops.values()}, {900, 901})
        self.assertIsNone(c.ns.routePaused)
        self.assertEqual(order(g), before)
        self.assertEqual(primitive(c.ns.db.guideSkips), skips)
        self.assertGreater(c.ns.routeStats.pins, 0)
        self.assertGreater(c.ns.routeStats.lines, 0)
        self.assertFalse(button.IsShown(button))
        self.assertTrue(c.ns.navigation.skipStep.IsShown(c.ns.navigation.skipStep))
        self.assertFalse(c.ns.LevelingValue(900)[0])
        self.assertFalse(c.ns.LevelingValue(901)[0])
        self.assertEqual(c.ns.PreferredQuestLevels(), (22, 28))
        self.assertFalse(c.ns.Completed(900))
        self.assertTrue(c.ns.db.guideState[c.ns.self].guide.continueOutsideLevels)

    def test_accepted_higher_level_work_and_ready_returns_progress_normally(self):
        c, g = paused()
        c.lua.globals().entries[1] = c.lua.table_from({'questID': 901, 'title': 'Quest 1', 'isHeader': False})
        c.ns.ReadQuests(); c.ns.Refresh()
        c.ns.ContinueGuideAnyway()
        stages = [(s.id, s.kind) for s in c.ns.selectedRoute.stops.values()]
        self.assertIn((901, 'q'), stages)
        self.assertNotIn((901, 'a'), stages)
        c.ns.readyToTurnIn[901] = True
        c.ns.Refresh()
        stages = [(s.id, s.kind) for s in c.ns.selectedRoute.stops.values()]
        self.assertNotIn((901, 'q'), stages)
        self.assertIn((901, 't'), stages)
        self.assertFalse(c.ns.Completed(901))

    def test_pause_resume_keeps_the_choice_in_the_checkpoint(self):
        c, g = paused()
        c.ns.ContinueGuideAnyway()
        before = order(g)
        c.ns.PauseGuideSession()
        self.assertIsNone(c.ns.routeSelection)
        self.assertTrue(c.ns.PausedSessionCheckpoint().guide.continueOutsideLevels)
        c.ns.ResumeGuideSession(); run_plan(c); c.drain()
        self.assertTrue(c.ns.routeSelection.continueOutsideLevels)
        self.assertEqual(order(c.ns.routeSelection), before)
        self.assertEqual({s.id for s in c.ns.selectedRoute.stops.values()}, {900, 901})

    def test_unknown_requirements_remain_a_confirmation_pause(self):
        c, g = paused()
        c.ns.catalogue.detailSource = 'Synthetic detailed source'
        c.ns.catalogue.quests[901].prerequisitesRead = True
        c.ns.ContinueGuideAnyway()
        self.assertEqual(c.ns.selectedRoute.pendingStop.id, 900)
        self.assertIn('requirements', c.ns.routePaused)
        self.assertFalse(c.ns.CanContinueGuideAnyway())
        self.assertFalse(c.ns.CanAutoAcceptGuideQuest(900))

    def test_manual_quest_and_step_skips_survive_the_override(self):
        c, g = paused(3)
        c.ns.db.guideSkips[c.ns.self].quests[900] = True
        step = next(s for s in g.fixedPlan.values() if s.id == 901 and s.kind == 'a')
        c.ns.db.guideSkips[c.ns.self].steps[901] = c.lua.table_from({c.ns.GuideStepKey(step): True})
        c.ns.Refresh()
        before = primitive(c.ns.db.guideSkips)
        c.ns.ContinueGuideAnyway()
        self.assertEqual(primitive(c.ns.db.guideSkips), before)
        self.assertNotIn(900, {s.id for s in c.ns.selectedRoute.stops.values()})
        self.assertFalse(any(s.id == 901 and s.kind == 'a' for s in c.ns.selectedRoute.stops.values()))
        self.assertTrue(c.ns.GuideQuestSkipped(900))
        self.assertFalse(c.ns.Completed(900))

    def test_pickup_requirements_and_confirmed_absences_are_still_gates(self):
        c, g = paused(8)
        c.lua.execute("function UnitClass()return 'Shaman','SHAMAN',7 end; function UnitRace()return 'Orc','Orc',2 end")
        c.ns.ReadProfile()
        c.lua.globals().pyBand = lambda a, b: int(a) & int(b)
        c.lua.globals().pyShift = lambda a, b: int(a) << int(b)
        c.lua.execute('bit={band=function(a,b)return pyBand(a,b)end,lshift=function(a,b)return pyShift(a,b)end}')
        c.ns.catalogue.quests[900].minLevel = 26
        c.ns.catalogue.quests[899] = c.lua.table_from(world_quest('External prerequisite'), recursive=True)
        c.ns.catalogue.quests[901].previousQuest = 899
        c.ns.ObservedPickupAvailable = c.lua.eval('function(id)if id==902 then return false end end')
        c.ns.catalogue.quests[903].classMask = 64
        c.ns.db.config.classQuests = False
        c.ns.catalogue.quests[904].side = 'Alliance'
        c.ns.catalogue.quests[905].classMask = 1
        c.ns.catalogue.quests[906].raceMask = 1
        c.ns.ContinueGuideAnyway()
        self.assertEqual({s.id for s in c.ns.selectedRoute.stops.values()}, {907})
        self.assertEqual({s.id for s in c.ns.selectedRoute.previewStops.values()}, {907})
        self.assertFalse(c.ns.CatalogueAllowed(900, c.ns.profile, c.ns.self)[0])
        self.assertFalse(c.ns.Completed(901))
        self.assertFalse(c.ns.IsGroupQuest(907))

    def test_confirmed_guide_offer_can_autoaccept_but_unrelated_offer_cannot(self):
        c, g = paused()
        c.ns.offered[900], c.ns.offered[901] = True, True
        c.ns.catalogue.quests[999] = c.lua.table_from(world_quest('Unrelated', level=30), recursive=True)
        c.ns.offered[999] = True
        self.assertFalse(c.ns.CanAutoAcceptGuideQuest(901))
        c.ns.ContinueGuideAnyway()
        self.assertTrue(c.ns.CanAutoAcceptGuideQuest(901))
        self.assertFalse(c.ns.CanAutoAcceptGuideQuest(999))
        c.ns.catalogue.quests[901].minLevel = 26
        self.assertFalse(c.ns.CanAutoAcceptGuideQuest(901))

    def test_saved_choice_survives_reload_and_scan_but_stop_resets_it(self):
        c, g = paused()
        c.ns.ContinueGuideAnyway()
        before = order(g)
        fresh = reload(c)
        self.assertTrue(fresh.ns.routeSelection.continueOutsideLevels)
        self.assertEqual(order(fresh.ns.routeSelection), before)
        fresh.ns.ScanGuideProgress(); fresh.drain()
        self.assertTrue(fresh.ns.routeSelection.continueOutsideLevels)
        self.assertEqual(order(fresh.ns.routeSelection), before)
        old = fresh.ns.routeSelection
        fresh.ns.StopGuide(False)
        self.assertIsNone(old.continueOutsideLevels)
        self.assertIsNone(fresh.ns.db.guideState[fresh.ns.self])
        fresh.ns.ActivateRoute(old); fresh.ns.Refresh()
        self.assertFalse(fresh.ns.GuideDifficultyOverride(old))
        self.assertEqual(len(fresh.ns.selectedRoute.stops), 0)

    def test_switching_guides_restores_default_difficulty_and_keeps_other_skips(self):
        c, g = paused()
        c.ns.ContinueGuideAnyway()
        other = c.ns.MergeCurrentQuests(g)
        self.assertIsNone(other.continueOutsideLevels)
        c.ns.ActivateRoute(other); c.ns.Refresh()
        self.assertIsNone(g.continueOutsideLevels)
        self.assertEqual(len(c.ns.selectedRoute.stops), 0)
        self.assertTrue(c.ns.CanContinueGuideAnyway())

    def test_busy_and_non_level_pauses_never_offer_the_override(self):
        c, g = paused()
        c.ns.guideScanning = c.lua.table_from({'guide': g})
        c.ns.UpdateNavigation()
        self.assertFalse(c.ns.navigation['continue'].IsShown(c.ns.navigation['continue']))
        c.ns.ContinueGuideAnyway()
        self.assertIsNone(g.continueOutsideLevels)
        c.ns.guideScanning = None
        c.ns.selectedRoute.rangePaused = None
        c.ns.routePaused = 'Finish the prerequisite first.'
        c.ns.UpdateNavigation()
        self.assertFalse(c.ns.CanContinueGuideAnyway())
        c.ns.ContinueGuideAnyway()
        self.assertIsNone(g.continueOutsideLevels)
        for mode in ('profession', 'dungeon', 'travel', 'current'):
            g.mode, g.continueOutsideLevels = mode, True
            self.assertFalse(c.ns.GuideDifficultyOverride(g))

    def test_elite_warnings_remain_and_list_uses_the_selected_guide_choice(self):
        c, g = paused()
        c.ns.catalogue.quests[901].questType = 'Elite'
        c.ns.ContinueGuideAnyway()
        self.assertIn('party', c.ns.QuestGroupWarning(901))
        c.ns.ShowGuideQuestList(g); c.drain()
        rows = list(c.ns.guideQuestList.rows.values())
        self.assertFalse(any('Outside level range' in (r.state.text or '') for r in rows))
        self.assertTrue(any('Elite' in (r.state.text or '') for r in rows))
        self.assertIn('Available', rows[0].state.text)
        c.ns.Diagnostics()
        self.assertIn('all quest levels by player choice', c.ns.diagnosticsText.text)


if __name__ == '__main__':
    unittest.main()
