"""Terrain geometry, live waypoint ownership and map drawing under Lua 5.1.

The geometry checks validate the implementation, not actual terrain/elevation.
"""
import unittest

from test_070 import network_client, point
from test_routes import guide, map_canvas


def terrain_client(obstacles=None):
    c = network_client()
    c.ns.travelData = c.lua.table_from({'nodes': {}, 'edges': [], 'factors': {}}, recursive=True)
    c.ns.travelTerrainData = c.lua.table_from({'maps': {501: {'padding': .005, 'obstacles': obstacles or [
        {'name': 'the ridge', 'polygon': [[.4, .25], [.6, .25], [.6, .5], [.4, .5]]}
    ]}}}, recursive=True)
    c.ns.SetOption('suggestFlights', False)
    c.lua.execute('playerX=.1;clock=1;function GetTime() return clock end')
    return c


def destination(c, x=.9, y=.37, map_id=501):
    p = point(c, map_id, x, y)
    p.id, p.kind, p.title, p.label = 900, 'a', 'Remote pickup', 'Talk to the quest giver'
    return p


class TerrainRoutingTests(unittest.TestCase):
    def assert_clear(self, c, path):
        self.assertIsNotNone(path)
        for leg in path.legs.values():
            if leg.method == 'walk':
                self.assertIsNone(c.ns.TerrainWalkCrossing(leg['from'], leg.to), leg.toID)

    def test_direct_chord_is_replaced_by_shortest_visible_corner_route(self):
        c = terrain_client()
        origin, goal = point(c, 501, .1), destination(c)
        self.assertIsNotNone(c.ns.TerrainWalkCrossing(origin, goal))
        path = c.ns.FindTravelPath(origin, goal, False)
        self.assert_clear(c, path)
        self.assertTrue(path.hasTerrain)
        self.assertEqual(len(path.legs), 3)
        self.assertGreater(path.seconds, .8 * 1000 * 1.25 / 7)
        self.assertTrue(all(s.to.y < .25 for s in list(path.legs.values())[:-1]))
        repeat = c.ns.FindTravelPath(origin, goal, False)
        self.assertEqual([s.toID for s in path.legs.values()], [s.toID for s in repeat.legs.values()])

    def test_published_node_and_edge_cannot_bypass_barrier(self):
        c = terrain_client()
        c.ns.travelData.nodes['FAR'] = point(c, 501, .89)
        c.ns.travelData.nodes['NEAR'] = point(c, 501, .11)
        c.ns.travelData.edges[1] = c.lua.table_from({'from': 'NEAR', 'to': 'FAR', 'seconds': 0, 'method': 'walk'})
        path = c.ns.FindTravelPath(point(c, 501, .1), destination(c), False)
        self.assert_clear(c, path)
        self.assertTrue(path.hasTerrain)
        self.assertFalse(any(s.fromID == 'NEAR' and s.toID == 'FAR' for s in path.legs.values()))

    def test_waypoint_stays_stable_while_player_follows_segment_then_advances(self):
        c = terrain_client(); goal = destination(c)
        first = c.ns.TravelNetworkDestination(goal)
        self.assertIsNotNone(first.travelLeg.to.terrain)
        x = .1 + (first.x - .1) * .8
        y = .37 + (first.y - .37) * .8
        c.lua.globals().playerX, c.lua.globals().playerY, c.lua.globals().clock = x, y, 4
        second = c.ns.TravelNetworkDestination(goal)
        self.assertEqual((second.x, second.y), (first.x, first.y))
        self.assertEqual(c.ns.travelPath.origin.x, .1)
        c.lua.globals().playerX, c.lua.globals().playerY = first.x, first.y
        following = c.ns.TravelNetworkDestination(goal)
        self.assertNotEqual((following.x, following.y), (first.x, first.y))
        self.assertEqual(c.ns.travelPath.cursor, 2)
        self.assertIsNone(c.ns.TerrainWalkCrossing(point(c, 501, first.x, first.y), following))

    def test_arrival_radius_cannot_cut_the_corner_through_ridge(self):
        c = terrain_client(); goal = destination(c)
        first = c.ns.TravelNetworkDestination(goal)
        c.lua.globals().playerX, c.lua.globals().playerY = first.x - .008, first.y + .012
        next_stop = c.ns.TravelNetworkDestination(goal)
        self.assertEqual(c.ns.travelPath.cursor, 1)
        self.assertEqual((next_stop.x, next_stop.y), (first.x, first.y))

    def test_passing_a_corner_cannot_cut_through_a_hostile_settlement(self):
        c = terrain_client()
        c.ns.travelData.settlements = c.lua.table_from([{'name': 'Enemy village', 'faction': 'Alliance',
            'mapID': 501, 'minX': .52, 'maxX': .54, 'minY': .13, 'maxY': .145}], recursive=True)
        goal = destination(c); first = c.ns.TravelNetworkDestination(goal)
        c.lua.globals().playerX, c.lua.globals().playerY = first.x - .006, first.y - .012
        c.ns.TravelNetworkDestination(goal)
        self.assertEqual(c.ns.travelPath.cursor, 1)

    def test_real_detour_replans_travel_without_advancing_quest(self):
        c = terrain_client(); goal = destination(c)
        route = c.lua.table_from({'mapID': 501, 'stops': [goal]}, recursive=True)
        c.ns.ActivateRoute(guide(c), route)
        c.ns.UpdateNavigation()
        c.lua.globals().playerY, c.lua.globals().clock = .9, 4
        c.ns.UpdateNavigation()
        self.assertEqual(c.ns.travelPath.origin.y, .9)
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 900)
        self.assertFalse(c.ns.Completed(900))

    def test_open_ground_and_unmapped_zones_keep_direct_local_travel(self):
        c = terrain_client()
        for origin, goal in ((point(c, 501, .1, .1), point(c, 501, .9, .1)),
                             (point(c, 502, .1), point(c, 502, .9))):
            path = c.ns.FindTravelPath(origin, goal, False)
            self.assertEqual(len(path.legs), 1)
            self.assertFalse(path.hasTerrain)

    def test_inside_mesa_needs_an_approach_but_local_work_atop_it_still_works(self):
        c = terrain_client([{'name': 'the mesa', 'elevated': True,
                            'polygon': [[.4, .25], [.6, .25], [.6, .5], [.4, .5]]}])
        goal = destination(c, .5)
        self.assertIsNone(c.ns.FindTravelPath(point(c, 501, .1), goal, False))
        warning = c.ns.TravelDestination(goal)
        self.assertIsNotNone(warning.unsafeTerrain)
        c.ns.ActivateRoute(guide(c), c.lua.table_from({'mapID': 501, 'stops': [goal]}, recursive=True))
        c.ns.UpdateNavigation()
        state = c.ns.navigation.state
        self.assertIsNone(state.angle)
        self.assertIn('lift or ramp', state.status)
        self.assertEqual(warning.goal.id, goal.id)
        path = c.ns.FindTravelPath(point(c, 501, .45), destination(c, .55), False)
        self.assertEqual(len(path.legs), 1)

    def test_toggle_restores_direct_direction_without_changing_quest(self):
        c = terrain_client(); goal = destination(c)
        self.assertIsNotNone(c.ns.TravelDestination(goal).travelLeg)
        c.ns.SetOption('travelNetwork', False)
        direct = c.ns.TravelDestination(goal)
        self.assertEqual(direct.kind, 'a')
        self.assertIsNone(direct.travelLeg)

    def test_public_positions_only_and_projected_outside_map_segments_are_checked(self):
        c = terrain_client(); a, b = point(c, 501, .1), point(c, 501, 1.2)
        self.assertIsNotNone(c.ns.TerrainWalkCrossing(a, b))
        a.x = c.lua.globals().secret
        self.assertIsNone(c.ns.TerrainWalkCrossing(a, b))
        self.assertIsNone(c.ns.FindTravelPath(a, b, False))
        c.lua.execute('C_Map.GetMapWorldSize=function() return secret,secret end; C_Map.GetWorldPosFromMapPos=nil')
        self.assertIsNone(c.ns.FindTravelPath(point(c, 501, .1), destination(c), False))

    def test_ship_still_uses_one_way_link_and_line_gap(self):
        c = terrain_client()
        c.ns.travelData = c.lua.table_from({'nodes': {
            'A': {'mapID': 501, 'x': .2, 'y': .37}, 'B': {'mapID': 502, 'x': .1, 'y': .37}},
            'edges': [{'from': 'A', 'to': 'B', 'seconds': 120, 'method': 'ship'}], 'factors': {}}, recursive=True)
        goal = destination(c, .2, map_id=502)
        path = c.ns.FindTravelPath(point(c, 501, .1), goal, False)
        self.assert_clear(c, path)
        self.assertEqual([s.method for s in path.legs.values()], ['walk', 'ship', 'walk'])
        c.ns.TravelNetworkDestination(goal)
        self.assertIn(False, list(c.ns.TravelLinePoints(point(c, 501, .1), goal).values()))
        self.assertIsNone(c.ns.FindTravelPath(point(c, 502, .2), point(c, 501, .1), False))

    def test_confirmed_flight_crosses_barrier_in_air_without_a_ground_chord(self):
        c = terrain_client(); state = c.ns.db.flights[c.ns.self]
        for ident, x in ((9033, .15), (9034, .85)):
            state.nodes[ident] = c.lua.table_from({'id': ident, 'name': 'Flight master', 'known': True,
                'point': {'mapID': 501, 'x': x, 'y': .37}}, recursive=True)
        state.edges['9033:9034'] = c.lua.table_from({'source': 9033, 'destination': 9034})
        state.timings['9033:9034'] = c.lua.table_from({'mean': 5, 'samples': 1, 'validated': True,
            'build': c.ns.flightTimingBuild})
        goal = destination(c)
        path = c.ns.FindTravelPath(point(c, 501, .1), goal, True)
        self.assert_clear(c, path)
        self.assertEqual([s.method for s in path.legs.values()], ['walk', 'taxi', 'walk'])
        state.nodes[9034].known = False
        walk = c.ns.FindTravelPath(point(c, 501, .1), goal, True)
        self.assertTrue(walk.hasTerrain)
        self.assertFalse(any(s.method == 'taxi' for s in walk.legs.values()))

    def test_map_bounds_are_not_mixed_when_checking_a_cross_zone_ground_segment(self):
        c = terrain_client()
        c.lua.execute('bounds[502].x=500')
        self.assertIsNotNone(c.ns.TerrainWalkCrossing(point(c, 501, .1), point(c, 502, .4)))
        c.lua.execute('differentContinents=true')
        self.assertIsNone(c.ns.TerrainWalkCrossing(point(c, 501, .1), point(c, 502, .4)))

    def test_legacy_flight_fallback_cannot_send_player_through_a_mesa(self):
        c = terrain_client(); c.ns.SetOption('suggestFlights', True)
        state = c.ns.db.flights[c.ns.self]
        for ident, x in ((9033, .45), (9034, .99)):
            state.nodes[ident] = c.lua.table_from({'id': ident, 'name': 'Flight master', 'known': True,
                'point': {'mapID': 501, 'x': x, 'y': .37},
                'world': {'continent': 1, 'x': x * 1000, 'y': 370}}, recursive=True)
        state.edges['9033:9034'] = c.lua.table_from({'source': 9033, 'destination': 9034})
        state.timings['9033:9034'] = c.lua.table_from({'mean': 1, 'samples': 1, 'validated': True,
            'build': c.ns.flightTimingBuild})
        goal = destination(c, .999)
        c.ns.SetOption('travelNetwork', False)
        self.assertIsNotNone(c.ns.FindFlightPlan(goal))
        c.ns.SetOption('travelNetwork', True)
        self.assertIsNone(c.ns.FindFlightPlan(goal))

    def test_static_visibility_is_reused_but_public_position_reads_stay_fresh(self):
        c = terrain_client()
        a, b = c.ns.TravelTerrainContext(), c.ns.TravelTerrainContext()
        self.assertTrue(c.lua.eval('function(a,b)return rawequal(a.maps,b.maps)end')(a, b))
        self.assertFalse(c.lua.eval('function(a,b)return rawequal(a.projection,b.projection)end')(a, b))
        goal = destination(c); c.ns.TravelNetworkDestination(goal)
        c.lua.execute('C_Map.GetPlayerMapPosition=function() return secret end;clock=4')
        self.assertIsNone(c.ns.TravelNetworkDestination(goal))
        self.assertIsNone(c.ns.travelPath)

    def test_every_shipped_outline_compiles_and_example_avoids_actual_mapped_pinnacle(self):
        c = network_client(); c.lua.execute('bounds[1441]={x=0,width=4399}')
        context = c.ns.TravelTerrainContext()
        self.assertEqual(len(context.maps[1441].areas), 12)
        a, b = point(c, 1441, .49, .525), point(c, 1441, .57, .525)
        path = c.ns.FindTravelPath(a, b, False)
        self.assertTrue(path.hasTerrain)
        self.assert_clear(c, path)
        self.assertIsNotNone(c.ns.TerrainWalkCrossing(a, b))
        self.assertTrue(any(s.to.y < .505 or s.to.y > .546 for s in path.legs.values() if s.toID != 'GOAL'))


class TerrainMapTests(unittest.TestCase):
    def test_live_map_draws_same_bends_and_hides_unrouted_future_chord(self):
        c = terrain_client(); map_canvas(c)
        goal, later = destination(c), destination(c, .1)
        later.kind = 'q'
        c.ns.SetOption('routeLookAhead', 2)
        route = c.lua.table_from({'mapID': 501, 'stops': [goal, later]}, recursive=True)
        c.ns.ActivateRoute(guide(c), route)
        c.lua.globals().WorldMapFrame.SetMapID(c.lua.globals().WorldMapFrame, 501)
        c.ns.UpdateNavigation(); c.ns.DrawRoute()
        self.assertGreaterEqual(c.ns.routeStats.lines, 3)
        self.assertGreater(c.ns.routeStats.terrainLines, 0)
        self.assertGreaterEqual(c.ns.routeStats.pins, 2)
        p = c.ns.routeProvider
        first_x = p.lines[1].startPoint[3]
        c.lua.globals().playerX = .15
        c.ns.DrawRoute(None, True)
        self.assertNotEqual(p.lines[1].startPoint[3], first_x)
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 900)


if __name__ == '__main__':
    unittest.main()
