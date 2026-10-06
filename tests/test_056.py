"""Short map previews, walking priorities, zone handoffs and dialog turn-ins."""
import math
import unittest

from test_addon import Client
from test_routes import catalogue, guide, map_canvas, quest
from test_050 import nearby, solo
from test_navigation import navigator


def current_client(data):
    c = solo()
    c.ns.db.config.currentQuestsFirst = True
    c.ns.db.config.nearbyPickups = False
    catalogue(c, data)
    c.lua.globals().entries = c.lua.table_from([
        {'questID': id, 'title': row['title'], 'isHeader': False}
        for id, row in data.items()], recursive=True)
    c.ns.ReadQuests(); c.ns.ReadRouteLocations()
    return c


def preview_client():
    c = current_client({900: quest(objectives=[
        {'mapID': 501, 'x': .3 + i * .1, 'y': .4, 'name': str(i)}
        for i in range(5)])})
    map_canvas(c)
    c.ns.ShowGuideOnMap(c.ns.GuideChoices()[1])
    return c


class MapPreviewTests(unittest.TestCase):
    def test_default_preview_toggle_and_ahead_controls_retain_complete_plan(self):
        c = preview_client()
        self.assertEqual(len(c.ns.selectedRoute.stops), 6)
        self.assertEqual(c.ns.routeStats.pins, 3)
        self.assertEqual(c.ns.routeStats.lines, 3)
        legend = c.ns.routeProvider.legend
        legend.full.OnClick()
        self.assertTrue(c.ns.Option('fullRoute'))
        self.assertEqual(c.ns.routeStats.pins, 6)
        legend.full.OnClick()
        legend.ahead.OnClick()  # 2 -> 0
        self.assertEqual(c.ns.routeStats.pins, 1)
        self.assertEqual(c.ns.routeStats.lines, 1)
        legend.ahead.OnClick()  # 0 -> 1
        self.assertEqual(c.ns.routeStats.pins, 2)
        self.assertEqual(len(c.ns.selectedRoute.stops), 6)
        c.ns.SetOption('mapLegend', False)
        self.assertTrue(legend.IsShown(legend))
        self.assertFalse(legend.caption.IsShown(legend.caption))

    def test_shared_hub_steps_do_not_consume_the_entire_preview(self):
        c = preview_client()
        route = c.lua.table_from({'stops': [
            {'mapID': 501, 'x': .2, 'y': .3},
            {'mapID': 501, 'x': .2, 'y': .3},
            {'mapID': 501, 'x': .4, 'y': .5},
            {'mapID': 501, 'x': .6, 'y': .7},
            {'mapID': 501, 'x': .8, 'y': .9}]}, recursive=True)
        self.assertEqual(len(c.ns.RouteDisplayStops(route)), 4)
        c.ns.SetOption('routeAhead', 0)
        self.assertEqual(len(c.ns.RouteDisplayStops(route)), 2)

    def test_preview_advances_on_quest_progress_instead_of_player_arrival(self):
        c = preview_client()
        old = c.ns.selectedRoute.stops[1].x
        c.lua.execute('C_Map.GetPlayerMapPosition=function() return {GetXY=function() return .3,.4 end} end')
        c.ns.DrawRoute()
        self.assertAlmostEqual(c.ns.selectedRoute.stops[1].x, old)
        c.lua.execute('C_QuestLog.GetNextWaypoint=function() return 501,.7,.4 end')
        c.ns.ReadRouteLocations(); c.ns.UpdateSelectedRoute(c.lua.table())
        self.assertAlmostEqual(c.ns.selectedRoute.stops[1].x, .7)
        self.assertAlmostEqual(c.ns.routeProvider.pins[1].stop.x, .7)
        self.assertLessEqual(c.ns.routeStats.pins, 3)

    def test_live_first_leg_redraws_without_replanning_or_reading_quest_logs(self):
        c = preview_client()
        c.lua.execute('''
        C_Map.GetPlayerMapPosition=function() return {GetXY=function() return .28,.38 end} end
        ''')
        c.ns.ReadQuests = c.lua.eval('function() error("geometry must not read quests") end')
        c.ns.GuideChoices = c.lua.eval('function() error("geometry must not plan quests") end')
        legend = c.ns.routeProvider.legend
        legend.OnUpdate(legend, 1.1)
        line = c.ns.routeProvider.lines[1]
        self.assertAlmostEqual(line.startPoint[3], 280)
        self.assertAlmostEqual(line.startPoint[4], -304)
        self.assertEqual(len(c.ns.selectedRoute.stops), 6)

    def test_foreign_map_explains_route_and_view_button_restores_it_after_combat(self):
        c = preview_client()
        world = c.lua.globals().WorldMapFrame
        world.SetMapID(world, 502)
        legend = c.ns.routeProvider.legend
        self.assertTrue(legend.IsShown(legend))
        self.assertIn('Test Coast', legend.caption.text)
        self.assertEqual(c.ns.routeStats.lines, 0)
        c.lua.globals().combat = True
        legend.zone.OnClick()
        self.assertEqual(world.mapID, 502)
        self.assertTrue(c.ns.routeZoneViewPending)
        c.lua.globals().combat = False
        c.ns.FlushRouteUpdates()
        self.assertEqual(world.mapID, 501)
        self.assertEqual(c.ns.routeStats.pins, 3)

    def test_foreign_player_position_never_becomes_a_source_map_origin(self):
        c = preview_client()
        c.lua.execute('C_Map.GetBestMapForUnit=function() return 502 end')
        c.ns.DrawRoute()
        self.assertEqual(c.ns.routeProvider.playerOrigin.mapID, 502)
        self.assertIsNone(c.ns.ProjectMapPoint(c.ns.routeProvider.playerOrigin, 501))
        self.assertEqual(c.ns.routeStats.lines, 2)
        self.assertAlmostEqual(c.ns.routeProvider.lines[1].startPoint[3], 300)

    def test_controls_stay_above_a_fullscreen_map(self):
        c = preview_client()
        c.lua.execute("function WorldMapFrame:GetFrameStrata() return 'FULLSCREEN' end")
        c.lua.execute("function captureStrata(self,value) self.strata=value end")
        c.ns.routeProvider.legend.SetFrameStrata = c.lua.globals().captureStrata
        c.ns.routeProvider.overlay.SetFrameStrata = c.lua.globals().captureStrata
        c.ns.DrawRoute()
        self.assertEqual(c.ns.routeProvider.legend.strata, 'FULLSCREEN')
        self.assertEqual(c.ns.routeProvider.overlay.strata, 'FULLSCREEN')


class CurrentTripTests(unittest.TestCase):
    def test_known_local_active_work_beats_remote_delivery_and_new_xp_with_discovery_on(self):
        c = current_client({900: nearby('Active local work'),
                            901: quest('Remote delivery', map_id=502)})
        c.lua.execute('C_QuestLog.IsComplete=function(id) return id==901 end')
        c.ns.ReadRouteLocations()
        c.ns.db.config.currentQuestsFirst = False
        c.ns.catalogue.quests[902] = c.lua.table_from(nearby('Huge new XP'), recursive=True)
        c.ns.catalogue.quests[902].xp = 1000000
        choices = list(c.ns.GuideChoices().values())
        self.assertEqual(choices[0].mode, 'current')
        self.assertEqual(choices[0].mapID, 501)
        self.assertEqual(choices[0].nextStop.id, 900)
        self.assertEqual(choices[1].mapID, 502)
        self.assertTrue(any(row.mode == 'circuit' for row in choices))

    def test_long_ready_turn_in_detour_waits_for_nearby_work(self):
        c = current_client({900: nearby('Local work'), 901: nearby('Far ready return')})
        c.ns.catalogue.quests[901].ends[1].x = .95
        c.ns.catalogue.quests[901].ends[1].y = .9
        c.lua.execute('C_QuestLog.IsComplete=function(id) return id==901 end')
        c.ns.ReadRouteLocations()
        route = c.ns.BuildGuideRoute(c.ns.GuideChoices()[1], True)
        self.assertEqual(route.stops[1].id, 900)
        self.assertEqual(route.stops[1].kind, 'q')
        self.assertEqual(route.stops[len(route.stops)].id, 901)
        self.assertEqual(route.stops[len(route.stops)].kind, 't')

    def test_zone_handoff_keeps_selection_and_uses_receiver_coordinates(self):
        c = current_client({900: nearby('Cross-zone return')})
        c.ns.catalogue.quests[900].ends[1].mapID = 502
        c.ns.catalogue.quests[900].ends[1].x = .8
        c.ns.catalogue.quests[900].ends[1].y = .6
        map_canvas(c)
        c.ns.ShowGuideOnMap(c.ns.GuideChoices()[1])
        key = c.ns.routeSelection.key
        c.lua.execute('C_QuestLog.IsComplete=function() return true end; C_QuestLog.GetNextWaypoint=function() return 502,.8,.6 end')
        c.ns.ReadRouteLocations(); c.ns.UpdateSelectedRoute(c.lua.table())
        self.assertEqual(c.ns.routeSelection.key, key)
        self.assertEqual(c.ns.selectedRoute.mapID, 502)
        self.assertIsNone(c.ns.routePaused)
        self.assertEqual(c.ns.selectedRoute.stops[1].kind, 't')
        self.assertIsNone(c.lua.globals().waypoint)
        self.assertEqual(c.ns.selectedRoute.stops[1].mapID, 502)
        self.assertEqual(c.ns.routeStats.lines, 0)
        c.ns.ViewRouteZone()
        self.assertEqual(c.ns.routeStats.pins, 1)
        self.assertEqual(c.ns.routeStats.lines, 0)  # Player is still in 501.
        self.assertAlmostEqual(c.ns.routeProvider.pins[1].point[4], 800)

    def test_local_walking_improvement_shortens_objective_loop_and_preserves_returns(self):
        points = [(.29, .67), (.46, .7), (.31, .61), (.62, .66), (.26, .39)]
        data = {900 + i: nearby(str(i)) for i in range(len(points))}
        for i, (x, y) in enumerate(points):
            data[900 + i]['objectives'][0].update(x=x, y=y)
        c = current_client(data)
        c.lua.execute('C_Map.GetMapWorldSize=function() return 1000,1000 end')
        route = c.ns.BuildGuideRoute(c.ns.GuideChoices()[1], True)
        def distance(a, b):
            return math.hypot(a[0] - b[0], a[1] - b[1]) * 1000
        remaining, position, baseline = list(points), (.21, .37), 0
        while remaining:
            point = min(remaining, key=lambda p: distance(position, p))
            baseline += distance(position, point)
            position = point; remaining.remove(point)
        baseline += distance(position, (.21, .37))
        self.assertLess(route.walkingYards, baseline - 1)
        self.assertEqual([s.kind for s in route.stops.values()], ['q'] * 5 + ['t'] * 5)
        self.assertEqual({s.id for s in route.stops.values()}, set(data))

    def test_arrow_context_explains_action_party_and_travel_in_two_lines(self):
        c = navigator()
        stop = c.ns.selectedRoute.stops[1]
        stop.forPlayer = 'You, Bob'
        stop.kind = 't'
        c.lua.execute('C_Map.GetBestMapForUnit=function() return 502 end')
        c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.context.text.splitlines(),
                         ['Hand in the completed quest.', 'Travel to Test Coast • 21.0, 27.0 • For You, Bob'])
        self.assertIsNone(c.ns.navigation.state.angle)
        c.ns.routePaused = 'Waiting'
        c.ns.UpdateNavigation()
        self.assertIn('retained', c.ns.navigation.context.text)


def dialog_client():
    c = Client(quests=(900,))
    c.guide_environment()
    c.lua.execute('''
    dialogQuest=900; rewardChoices=0; completable=true
    progressCalls=0; rewardCalls=0
    function GetQuestID() return dialogQuest end
    function IsQuestCompletable() return completable end
    function GetNumQuestChoices() return rewardChoices end
    function CompleteQuest() progressCalls=progressCalls+1 end
    function GetQuestReward(index) rewardCalls=rewardCalls+1; chosenReward=index end
    ''')
    c.ns.InitializeOffers()
    return c


class TurnInTests(unittest.TestCase):
    def test_off_by_default_and_probe_never_performs_quest_actions(self):
        c = dialog_client()
        c.ns.handlers.QUEST_PROGRESS(); c.ns.handlers.QUEST_COMPLETE()
        c.ns.Diagnostics()
        self.assertEqual(c.lua.globals().progressCalls, 0)
        self.assertEqual(c.lua.globals().rewardCalls, 0)
        self.assertIn('GetNumQuestChoices: present', c.ns.diagnosticsText.text)
        self.assertIn('Auto turn-in enabled: false', c.ns.diagnosticsText.text)

    def test_completed_open_dialog_with_no_choice_is_attempted_once_until_closed(self):
        c = dialog_client()
        c.ns.SetOption('autoTurnIn', True)
        c.ns.handlers.QUEST_PROGRESS(); c.ns.handlers.QUEST_PROGRESS()
        c.ns.handlers.QUEST_COMPLETE(); c.ns.handlers.QUEST_COMPLETE()
        self.assertEqual(c.lua.globals().progressCalls, 1)
        self.assertEqual(c.lua.globals().rewardCalls, 1)
        self.assertEqual(c.lua.globals().chosenReward, 0)
        self.assertFalse(c.ns.Completed(900))  # An attempted native action is not proof.
        c.ns.handlers.QUEST_FINISHED()
        c.ns.handlers.QUEST_COMPLETE()
        self.assertEqual(c.lua.globals().rewardCalls, 2)

    def test_reward_choices_always_stay_manual(self):
        for count in (1, 2, 4):
            with self.subTest(count=count):
                c = dialog_client()
                c.ns.db.config.autoTurnIn = True
                c.lua.globals().rewardChoices = count
                c.ns.handlers.QUEST_COMPLETE()
                self.assertEqual(c.lua.globals().rewardCalls, 0)
                self.assertIn('manually', c.ns.turnInStatus)

    def test_private_missing_or_invalid_reward_count_never_claims_rewards(self):
        for expression in ('secret', 'nil', '-1', '0.5', '101'):
            with self.subTest(expression=expression):
                c = dialog_client()
                c.ns.db.config.autoTurnIn = True
                c.lua.execute('rewardChoices=' + expression)
                c.ns.handlers.QUEST_COMPLETE()
                self.assertEqual(c.lua.globals().rewardCalls, 0)

    def test_combat_private_quest_and_unaccepted_dialog_do_not_trigger_actions(self):
        for setup in ('combat=true', 'dialogQuest=secret', 'dialogQuest=901', 'GetQuestReward=nil'):
            with self.subTest(setup=setup):
                c = dialog_client()
                c.ns.db.config.autoTurnIn = True
                c.lua.execute(setup)
                c.ns.handlers.QUEST_COMPLETE()
                self.assertEqual(c.lua.globals().rewardCalls, 0)
        for setup in ('completable=false', 'completable=secret', 'IsQuestCompletable=nil', 'CompleteQuest=nil', 'combat=true'):
            with self.subTest(setup=setup):
                c = dialog_client()
                c.ns.db.config.autoTurnIn = True
                c.lua.execute(setup)
                c.ns.handlers.QUEST_PROGRESS()
                self.assertEqual(c.lua.globals().progressCalls, 0)


if __name__ == '__main__':
    unittest.main()
