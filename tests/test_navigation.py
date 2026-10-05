"""Direction geometry and route lifecycle checks; beta APIs still need probing."""
import math
import unittest

from test_routes import guide, map_canvas, route_client


def navigator(x=.21, y=.27):
    c = route_client()
    c.lua.execute('C_Map.GetMapWorldSize=function() return 1000,1000 end; function GetPlayerFacing() return facing end; facing=0')
    c.ns.routeSelection = guide(c)
    c.ns.selectedRoute = c.lua.table_from({'mapID': 501, 'stops': [{'id': 900, 'mapID': 501,
        'x': x, 'y': y, 'kind': 'a', 'title': 'Pickup quest', 'label': 'Talk to the starter'}]}, recursive=True)
    c.ns.UpdateNavigation()
    return c


class NavigationTests(unittest.TestCase):
    def test_cardinal_bearings_and_distance_follow_public_map_scale(self):
        for x, y, angle in ((.21, .27, 0), (.31, .37, -math.pi/2),
                            (.21, .47, math.pi), (.11, .37, math.pi/2)):
            c = navigator(x, y)
            state = c.ns.navigation.state
            self.assertAlmostEqual(state.distance, 100)
            self.assertAlmostEqual(math.cos(state.angle), math.cos(angle))
            self.assertAlmostEqual(math.sin(state.angle), math.sin(angle))
            self.assertTrue(c.ns.navigation.IsShown(c.ns.navigation))

    def test_turning_west_toward_north_points_right_and_movement_reduces_distance(self):
        c = navigator()
        c.lua.globals().facing = math.pi/2
        c.ns.navigation.OnUpdate(c.ns.navigation, .1)
        self.assertAlmostEqual(c.ns.navigation.state.angle, -math.pi/2)
        point = c.ns.navigation.icon.lines[1].startPoint
        self.assertAlmostEqual(point[3], 21)
        self.assertAlmostEqual(point[4], 0, places=5)
        c.lua.execute('C_Map.GetPlayerMapPosition=function() return {GetXY=function() return .21,.32 end} end')
        c.ns.navigation.OnUpdate(c.ns.navigation, .1)
        self.assertAlmostEqual(c.ns.navigation.state.distance, 50)

    def test_physical_map_aspect_ratio_is_used_for_diagonal_bearing(self):
        c = navigator(.31, .27)
        c.lua.execute('C_Map.GetMapWorldSize=function() return 2000,1000 end')
        state = c.ns.NavigationState()
        self.assertAlmostEqual(state.distance, math.sqrt(200**2 + 100**2))
        self.assertAlmostEqual(state.angle, math.atan2(-200, 100))

    def test_arrival_does_not_accept_advance_or_complete_a_quest(self):
        c = navigator(.21, .37)
        c.lua.execute('function AcceptQuest() error("unexpected acceptance") end')
        state = c.ns.NavigationState()
        self.assertTrue(state.arrived)
        self.assertEqual(state.status, 'Pick up Pickup quest')
        self.assertIsNone(state.angle)
        self.assertIsNotNone(c.ns.routeSelection)
        self.assertEqual(c.ns.selectedRoute.stops[1].kind, 'a')
        self.assertFalse(c.ns.Completed(900))

    def test_private_or_missing_position_scale_and_facing_never_make_a_bearing(self):
        replacements = (
            ('C_Map.GetBestMapForUnit=function() return secret end', 'Position unavailable'),
            ('C_Map.GetPlayerMapPosition=function() return secret end', 'Position unavailable'),
            ('C_Map.GetPlayerMapPosition=function() return {GetXY=function() return secret,.37 end} end', 'Position unavailable'),
            ('C_Map.GetMapWorldSize=function() return 1000,secret end', 'Map scale unavailable'),
            ('C_Map.GetMapWorldSize=nil', 'Map scale unavailable'),
            ('GetPlayerFacing=function() return secret end', 'Direction unavailable'),
            ('GetPlayerFacing=nil', 'Direction unavailable'),
            ('GetPlayerFacing=function() return 0/0 end', 'Direction unavailable'),
            ('C_Map.GetMapWorldSize=function() return math.huge,1000 end', 'Map scale unavailable'))
        for replacement, status in replacements:
            c = navigator()
            c.lua.execute(replacement)
            c.ns.UpdateNavigation()
            self.assertEqual(c.ns.navigation.state.status, status)
            self.assertIsNone(c.ns.navigation.state.angle)
            self.assertTrue(c.ns.navigation.symbol.IsShown(c.ns.navigation.symbol))
            for line in c.ns.navigation.icon.lines.values():
                self.assertFalse(line.IsShown(line))

    def test_missing_drawing_api_is_reported_without_crashing(self):
        c = navigator()
        c.ns.navigation.icon.CreateLine = False
        c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.state.status, 'Arrow drawing unavailable')
        self.assertIsNone(c.ns.navigation.state.angle)

    def test_other_zone_or_waiting_snapshot_has_no_stale_direction(self):
        c = navigator()
        c.ns.selectedRoute.stops[1].mapID = 502
        c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.state.status, 'Travel to Test Hills')
        self.assertIsNone(c.ns.navigation.state.angle)
        c.ns.routePaused = 'Waiting'
        c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.state.status, 'Waiting for party updates')
        self.assertIsNone(c.ns.navigation.state.angle)

    def test_visibility_toggle_clear_and_polling_budget(self):
        c = navigator()
        c.lua.execute('facingReads=0; function GetPlayerFacing() facingReads=facingReads+1; return 0 end')
        c.ns.navigation.OnUpdate(c.ns.navigation, .04)
        c.ns.navigation.OnUpdate(c.ns.navigation, .04)
        self.assertEqual(c.lua.globals().facingReads, 0)
        c.ns.navigation.OnUpdate(c.ns.navigation, .02)
        self.assertEqual(c.lua.globals().facingReads, 1)
        c.ns.ToggleNavigation()
        self.assertFalse(c.ns.Option('routeArrow'))
        self.assertFalse(c.ns.navigation.IsShown(c.ns.navigation))
        c.ns.ToggleNavigation()
        self.assertTrue(c.ns.navigation.IsShown(c.ns.navigation))
        c.ns.ClearRoute()
        c.ns.UpdateNavigation()
        self.assertFalse(c.ns.navigation.IsShown(c.ns.navigation))
        self.assertEqual(c.ns.navigation.state.status, 'No route selected')

    def test_drag_position_is_saved_and_restored_but_private_values_are_not(self):
        c = navigator()
        c.lua.execute('function WowTogetherRouteArrowMockPoint() return "CENTER",UIParent,"CENTER",30,-40 end')
        c.ns.navigation.GetPoint = c.lua.globals().WowTogetherRouteArrowMockPoint
        c.ns.SaveNavigationPosition()
        self.assertEqual(c.ns.db.arrowPosition.x, 30)
        self.assertEqual(c.ns.db.arrowPosition.y, -40)
        c.ns.CreateNavigation()
        self.assertEqual(c.ns.navigation.point[1], 'CENTER')
        self.assertEqual(c.ns.navigation.point[4], 30)
        c.lua.execute('function badPoint() return "CENTER",UIParent,"CENTER",secret,0 end')
        c.ns.navigation.GetPoint = c.lua.globals().badPoint
        c.ns.SaveNavigationPosition()
        self.assertEqual(c.ns.db.arrowPosition.x, 30)

    def test_arrow_follows_live_party_route_after_acceptance_and_keeps_unfinished_peer(self):
        c = route_client()
        map_canvas(c)
        c.lua.execute('C_Map.GetMapWorldSize=function() return 1000,1000 end; function GetPlayerFacing() return 0 end')
        c.ns.ShowGuideOnMap(guide(c))
        c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.state.stop.kind, 'a')
        c.lua.execute("entries={{questID=900,title='Accepted',isHeader=false}}; C_QuestLog.GetNextWaypoint=function() return 501,.6,.4 end")
        c.ns.SyncNow(False)
        self.assertEqual(c.ns.navigation.state.stop.kind, 'q')
        c.receive('1|S|1|1|1|900')
        c.receive('1|P|12|2|501|Test Coast')
        c.receive('1|R|1|900|501|60000|40000|q')
        c.lua.execute('entries={}; finished[900]=true')
        c.ns.SyncNow(False)
        self.assertEqual(c.ns.navigation.state.stop.memberKey, 'Bob-TestRealm')
        self.assertTrue(c.ns.navigation.IsShown(c.ns.navigation))
        c.receive('1|S|3|1|1|')
        c.receive('1|C|4|1|1|900')
        self.assertTrue(c.ns.navigation.IsShown(c.ns.navigation))
        self.assertTrue(c.ns.selectedRoute.complete)

    def test_probe_reports_navigation_capabilities_without_a_waypoint_action(self):
        c = navigator()
        c.lua.execute('C_Map.SetUserWaypoint=function() error("probe changed waypoint") end')
        c.ns.Diagnostics()
        text = c.ns.diagnosticsText.text
        self.assertIn('GetPlayerFacing: present', text)
        self.assertIn('Arrow distance: 100 yards', text)
        self.assertIn('minimap button opens the addon', text)


if __name__ == '__main__':
    unittest.main()
