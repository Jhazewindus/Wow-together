"""Regression coverage for visible map geometry and quest-log-first planning."""
import unittest

from test_addon import Client
from test_routes import catalogue, guide, map_canvas, quest, route_client
from test_050 import nearby, solo
from test_040 import objectives


def viewport(c, left=0, right=1, top=0, bottom=1):
    map_canvas(c)
    c.lua.execute('''
    viewport=CreateFrame('Frame'); viewport:SetSize(800,600)
    view={left=0,right=1,top=0,bottom=1}
    function WorldMapFrame:GetCanvasContainer() return viewport end
    function WorldMapFrame:GetViewRect()
      return {GetLeft=function() return view.left end,GetRight=function() return view.right end,
        GetTop=function() return view.top end,GetBottom=function() return view.bottom end}
    end
    ''')
    view = c.lua.globals().view
    view.left, view.right, view.top, view.bottom = left, right, top, bottom


def current_client():
    c = solo()
    c.ns.db.config.currentQuestsFirst = True
    c.ns.db.config.nearbyPickups = False  # Exercise the explicitly strict mode.
    catalogue(c, {900: nearby('Ready A', level=2, minLevel=1),
                  901: nearby('Ready B', level=3, minLevel=1),
                  902: nearby('Work here', level=5, minLevel=1),
                  903: nearby('Huge new XP', level=3, minLevel=1)})
    c.ns.catalogue.quests[903].xp = 1000000
    c.ns.profile.level = 3
    c.lua.execute("entries={{questID=900,title='Ready A',isHeader=false},{questID=901,title='Ready B',isHeader=false},{questID=902,title='Work here',isHeader=false}}; C_QuestLog.IsComplete=function(id) return id==900 or id==901 end")
    c.ns.ReadQuests()
    c.ns.ReadRouteLocations()
    return c


class CurrentQuestTests(unittest.TestCase):
    def test_activity_pickup_prompts_wait_while_current_logs_have_quests(self):
        c = current_client()
        c.ns.catalogue.quests[904] = c.lua.table_from(nearby('Dungeon pickup', categoryPath='dungeons/test-cavern'), recursive=True)
        c.ns.profile.level = 10
        c.ns.activityRevision = 1
        c.ns.ScheduleActivitySuggestions()
        c.drain()
        self.assertIsNone(c.ns.activityPrompt)
        c.ns.SetOption('currentQuestsFirst', False)
        c.drain()
        self.assertTrue(c.ns.activityPrompt.IsShown(c.ns.activityPrompt))

    def test_an_existing_discovery_route_switches_to_current_logs_when_enabled(self):
        c = current_client()
        map_canvas(c)
        c.ns.SetOption('currentQuestsFirst', False)
        circuit = next(choice for choice in c.ns.GuideChoices().values() if choice.mode == 'circuit')
        c.ns.ShowGuideOnMap(circuit)
        c.ns.SetOption('currentQuestsFirst', True)
        self.assertEqual(c.ns.routeSelection.mode, 'current')
        self.assertEqual(c.ns.selectedRoute.stops[1].kind, 't')
        self.assertFalse(any(stop.kind == 'a' for stop in c.ns.selectedRoute.stops.values()))

    def test_level_three_ready_turn_ins_beat_new_pickup_xp_without_zone_assumptions(self):
        c = current_client()
        choices = c.ns.GuideChoices()
        self.assertGreater(len(choices), 0)
        choice = choices[1]
        self.assertEqual(choice.mode, 'current')
        self.assertEqual(choice.title, 'Turn in 2 ready quests')
        self.assertEqual({r.id for r in choice.records.values()}, {900, 901, 902})
        route = c.ns.BuildGuideRoute(choice, True)
        self.assertEqual([s.kind for s in route.stops.values()], ['t', 't', 'q', 't'])
        self.assertFalse(any(s.id == 903 or s.kind == 'a' for s in route.stops.values()))
        self.assertIn('quest logs', choice.reason)

    def test_current_quests_first_defaults_on_and_can_be_disabled(self):
        self.assertTrue(Client(quests=()).ns.Option('currentQuestsFirst'))
        c = current_client()
        c.ns.SetOption('currentQuestsFirst', False)
        self.assertTrue(any(choice.mode == 'circuit' for choice in c.ns.GuideChoices().values()))

    def test_party_union_includes_peer_only_quests_without_pickups_for_other_members(self):
        c = current_client()
        c.lua.globals().grouped = True
        c.unit_names({'player': ['Alice', 'TestRealm'], 'party1': ['Bob', 'TestRealm']})
        c.receive('1|S|1|1|1|903')
        c.receive('1|P|3|2|501|Test Coast')
        c.receive('1|R|1|903|501|24000|40000|q')
        choice = c.ns.GuideChoices()[1]
        self.assertEqual({r.id for r in choice.records.values()}, {900, 901, 902, 903})
        route = c.ns.BuildGuideRoute(choice, True)
        peer_stops = [s for s in route.stops.values() if s.id == 903]
        self.assertTrue(peer_stops)
        self.assertTrue(all(s.memberKey == 'Bob-TestRealm' for s in peer_stops))
        self.assertFalse(any(s.kind == 'a' for s in route.stops.values()))

    def test_ready_player_can_deliver_first_and_peer_objectives_remain_afterward(self):
        c = current_client()
        map_canvas(c)
        c.lua.globals().grouped = True
        c.unit_names({'player': ['Alice', 'TestRealm'], 'party1': ['Bob', 'TestRealm']})
        c.receive('1|S|1|1|1|900')
        c.receive('1|P|3|2|501|Test Coast')
        c.receive('1|R|1|900|501|24000|40000|q')
        route = c.ns.BuildGuideRoute(c.ns.GuideChoices()[1], True)
        self.assertEqual(route.stops[1].kind, 't')
        self.assertTrue(any(s.id == 900 and s.kind == 'q' and s.memberKey == 'Bob-TestRealm' for s in route.stops.values()))
        c.ns.ShowGuideOnMap(c.ns.GuideChoices()[1])
        c.lua.execute("entries={{questID=901,title='Ready B',isHeader=false},{questID=902,title='Work here',isHeader=false}}; finished[900]=true")
        c.ns.SyncNow(False)
        self.assertTrue(any(s.id == 900 and s.kind == 'q' for s in c.ns.selectedRoute.stops.values()))

    def test_public_objective_completion_overrides_stale_objective_waypoint(self):
        c = current_client()
        c.lua.execute('C_QuestLog.IsComplete=function() return false end; C_QuestLog.GetNextWaypoint=function() return 501,.24,.4 end')
        c.ns.ReadRouteLocations()
        objectives(c, id=900, have=6, need=6, done=True)
        stop = c.ns.RouteStop(c.ns.CatalogueRecord(900), c.ns.self)
        self.assertEqual(stop.kind, 't')
        self.assertAlmostEqual(stop.x, .21)
        self.assertAlmostEqual(stop.y, .37)

    def test_missing_turn_in_coordinates_do_not_relabel_old_objective_as_turn_in(self):
        c = current_client()
        c.ns.catalogue.quests[900].ends = None
        c.lua.execute('C_QuestLog.IsComplete=function() return false end; C_QuestLog.GetNextWaypoint=function() return 501,.24,.4 end')
        c.ns.ReadRouteLocations()
        objectives(c, id=900, have=6, need=6, done=True)
        self.assertIsNone(c.ns.RouteStop(c.ns.CatalogueRecord(900), c.ns.self))

    def test_no_logged_quests_returns_to_discovery_and_missing_peer_logs_wait(self):
        c = current_client()
        c.lua.execute('entries={}')
        c.ns.ReadQuests()
        self.assertTrue(any(choice.mode == 'circuit' for choice in c.ns.GuideChoices().values()))
        c.lua.globals().grouped = True
        c.unit_names({'player': ['Alice', 'TestRealm'], 'party1': ['Bob', 'TestRealm']})
        self.assertEqual(len(c.ns.GuideChoices()), 0)
        self.assertIn("friends' quest logs", c.ns.currentGuideStatus)

    def test_unknown_active_quest_locations_are_reported_without_switching_to_new_quests(self):
        c = current_client()
        c.lua.execute("entries={{questID=99999,title='Unknown active',isHeader=false}}")
        c.ns.ReadQuests(); c.ns.ReadRouteLocations()
        choice = c.ns.GuideChoices()[1]
        self.assertEqual(choice.target.id, 99999)
        self.assertFalse(choice.hasPoint)
        self.assertIn('no verified destination', choice.reason)

    def test_current_route_clears_after_last_participant_and_keeps_prior_snapshot_during_reload(self):
        c = current_client()
        map_canvas(c)
        c.lua.execute("entries={{questID=900,title='Ready A',isHeader=false}}")
        c.ns.ReadQuests(); c.ns.ReadRouteLocations()
        c.lua.globals().grouped = True
        c.unit_names({'player': ['Alice', 'TestRealm'], 'party1': ['Bob', 'TestRealm']})
        c.receive('1|S|1|1|1|900'); c.receive('1|P|3|2|501|Test Coast')
        c.receive('1|R|1|900|501|24000|40000|q')
        c.ns.ShowGuideOnMap(c.ns.GuideChoices()[1])
        c.lua.execute('entries={}; finished[900]=true')
        c.ns.SyncNow(False)
        self.assertIsNotNone(c.ns.selectedRoute)
        c.receive('1|H')
        self.assertIsNotNone(c.ns.routePaused)
        self.assertGreater(c.ns.routeStats.pins, 0)
        c.receive('1|S|3|1|1|')
        self.assertIsNone(c.ns.selectedRoute)


class ViewportTests(unittest.TestCase):
    def test_route_uses_visible_viewport_not_canvas_size_and_explicit_anchor_points(self):
        c = route_client()
        viewport(c)
        c.ns.ShowGuideOnMap(guide(c))
        line = c.ns.routeProvider.lines[1]
        self.assertEqual(line.startPoint[1], 'TOPLEFT')
        self.assertAlmostEqual(line.startPoint[3], .21 * 800)
        self.assertAlmostEqual(line.startPoint[4], -.37 * 600)
        self.assertEqual(c.ns.routeStats.surface, 'Viewport projection')
        self.assertTrue(c.ns.routeProvider.overlay.IsShown(c.ns.routeProvider.overlay))
        self.assertEqual(c.ns.routeProvider.overlay.parent.width, 800)
        self.assertEqual(c.ns.routeStats.pins, 2)
        self.assertEqual(c.ns.routeStats.lines, 3)

    def test_pan_zoom_and_resize_project_and_clip_in_viewport_coordinates(self):
        c = route_client()
        viewport(c, left=.1, right=.5, top=.2, bottom=.6)
        c.ns.ShowGuideOnMap(guide(c))
        self.assertEqual(c.ns.routeStats.pins, 1)  # Objective x=.6 lies outside this view.
        pin = c.ns.routeProvider.pins[1]
        self.assertAlmostEqual(pin.point[4], 200)
        self.assertAlmostEqual(pin.point[5], -75)
        for line in c.ns.routeProvider.lines.values():
            if line.IsShown(line):
                for point in (line.startPoint, line.endPoint):
                    self.assertGreaterEqual(point[3], 0)
                    self.assertLessEqual(point[3], 800)
                    self.assertGreaterEqual(point[4], -600)
                    self.assertLessEqual(point[4], 0)
        view = c.lua.globals().view
        view.left, view.right = .4, .8
        c.ns.routeProvider.OnCanvasPanChanged(c.ns.routeProvider)
        self.assertEqual(c.ns.routeStats.pins, 1)
        self.assertAlmostEqual(c.ns.routeProvider.pins[1].point[4], 400)
        target = c.lua.globals().viewport
        target.SetSize(target, 1600, 1200)
        c.ns.routeProvider.OnCanvasSizeChanged(c.ns.routeProvider)
        c.drain()
        self.assertAlmostEqual(c.ns.routeProvider.pins[1].point[4], 800)

    def test_zoom_rechecks_next_frame_after_view_rectangle_cache_changes(self):
        c = route_client()
        viewport(c)
        c.ns.ShowGuideOnMap(guide(c))
        c.ns.routeProvider.OnCanvasScaleChanged(c.ns.routeProvider)
        c.lua.execute('view.left=.1; view.right=.5; view.top=.2; view.bottom=.6')
        c.drain()
        self.assertEqual(c.ns.routeStats.pins, 1)
        self.assertAlmostEqual(c.ns.routeProvider.pins[1].point[4], 200)

    def test_private_view_rectangle_hides_drawing_and_reports_waiting(self):
        c = route_client()
        viewport(c)
        c.ns.ShowGuideOnMap(guide(c))
        c.lua.globals().view.left = c.lua.globals().secret
        c.ns.DrawRoute()
        self.assertEqual(c.ns.routeStats.pins, 0)
        self.assertEqual(c.ns.routeStats.lines, 0)
        self.assertIn('restricted', c.ns.routeStats.status)

    def test_clipping_segments_at_every_edge_without_drawing_outside(self):
        c = route_client()
        self.assertEqual(c.ns.ClipRouteSegment(-100, 50, 900, 50, 800, 600), (0, 50, 800, 50))
        self.assertEqual(c.ns.ClipRouteSegment(50, -100, 50, 700, 800, 600), (50, 0, 50, 600))
        self.assertIsNone(c.ns.ClipRouteSegment(-100, -100, -20, -20, 800, 600))

    def test_neighboring_markers_cluster_and_legend_reports_visible_places(self):
        c = route_client()
        viewport(c)
        c.ns.routeSelection = guide(c)
        c.ns.selectedRoute = c.lua.table_from({'mapID': 501, 'stops': [
            {'id': 900+i, 'mapID': 501, 'x': .2+i*.001, 'y': .25, 'kind': 't', 'title': 'Ready', 'label': 'Deliver'} for i in range(4)]}, recursive=True)
        c.lua.globals().WorldMapFrame.mapID = 501
        c.ns.AttachRouteProvider(); c.ns.DrawRoute()
        self.assertEqual(c.ns.routeStats.pins, 1)
        self.assertIn('4 stops • 1 visible place', c.ns.routeProvider.legend.caption.text)
        self.assertEqual(c.ns.routeProvider.pins[1].number.text, '1/2/+2')
        self.assertEqual(len(c.ns.routeProvider.pins[1].group.stops), 4)


if __name__ == '__main__':
    unittest.main()
