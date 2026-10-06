"""Dungeon hand-ins, saved flight evidence and ordered transport directions.

Synthetic API returns exercise state; real beta travel still needs a ride test.
"""
import unittest

from test_addon import Client
from test_050 import solo, dungeon
from test_057 import plain
from test_060 import flight_client
from test_070 import network_client, point
from test_0830 import accept, group
from test_routes import quest, guide, map_canvas


def running_dungeon():
    c = solo(); map_canvas(c)
    g = dungeon(c)
    accept(c, 900, 901)
    c.ns.ShowDungeonQuests(g, True); c.drain()
    c.ns.DungeonEntryKey = c.lua.eval("function() return 'test-cavern' end")
    c.ns.UpdateSelectedRoute(c.lua.table())
    return c, g


class DungeonHandInTests(unittest.TestCase):
    def test_run_waits_then_routes_ready_quests_after_exit_and_completes_after_handin(self):
        c, g = running_dungeon()
        c.ns.readyToTurnIn[900] = True
        c.ns.UpdateSelectedRoute(c.lua.table())
        self.assertEqual(c.ns.routeSelection.dungeonPhase, 'run')
        self.assertEqual(len(c.ns.selectedRoute.stops), 0)
        self.assertIn('1/2 ready', c.ns.NavigationState().status)
        c.ns.DungeonEntryKey = c.lua.eval('function() return nil end')
        c.ns.UpdateSelectedRoute(c.lua.table())
        self.assertEqual(c.ns.routeSelection.dungeonPhase, 'return')
        self.assertEqual([(s.id, s.kind) for s in c.ns.selectedRoute.stops.values()], [(900, 't')])
        self.assertFalse(c.ns.Completed(900))
        c.lua.execute('finished[900]=true'); accept(c, 901)
        c.ns.UpdateSelectedRoute(c.lua.table())
        self.assertFalse(c.ns.selectedRoute.complete)
        self.assertIn('Finish 1 quest', c.ns.routePaused)
        self.assertNotIn('party', c.ns.RouteContext(c.ns.NavigationState().stop, 501))
        c.ns.readyToTurnIn[901] = True; c.ns.UpdateSelectedRoute(c.lua.table())
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 901)
        c.lua.execute('finished[901]=true'); accept(c)
        c.ns.UpdateSelectedRoute(c.lua.table())
        self.assertTrue(c.ns.selectedRoute.complete)

    def test_all_ready_inside_starts_returns_without_another_entrance_step(self):
        c, g = running_dungeon()
        for id in (900, 901): c.ns.readyToTurnIn[id] = True
        c.ns.UpdateSelectedRoute(c.lua.table())
        self.assertEqual(c.ns.routeSelection.dungeonPhase, 'return')
        self.assertEqual({s.id for s in c.ns.selectedRoute.stops.values()}, {900, 901})
        self.assertTrue(all(s.kind == 't' for s in c.ns.selectedRoute.stops.values()))
        self.assertFalse(any(s.dungeonEntrance for s in c.ns.selectedRoute.stops.values()))

    def test_starting_with_completed_objectives_goes_directly_to_handins(self):
        c = solo(); map_canvas(c); g = dungeon(c)
        accept(c, 900, 901)
        for id in (900, 901): c.ns.readyToTurnIn[id] = True
        c.ns.ActivateRoute(c.ns.DungeonGuide(g))
        self.assertEqual(c.ns.routeSelection.dungeonPhase, 'return')
        self.assertEqual({s.kind for s in c.ns.selectedRoute.stops.values()}, {'t'})

    def test_new_unrelated_pickups_do_not_expand_the_run_goal_set(self):
        c, g = running_dungeon()
        c.ns.catalogue.quests[902] = c.lua.table_from(quest('New quest', categoryPath='dungeons/test-cavern'), recursive=True)
        g.ids[3] = 902
        c.ns.readyToTurnIn[900] = True
        c.ns.DungeonEntryKey = c.lua.eval('function() return nil end')
        c.ns.UpdateSelectedRoute(c.lua.table())
        self.assertEqual(set(c.ns.routeSelection.collectionGoals.keys()), {900, 901})
        self.assertNotIn(902, {s.id for s in c.ns.selectedRoute.stops.values()})

    def test_missing_return_location_keeps_quest_pending_instead_of_complete(self):
        c = solo(); map_canvas(c)
        g = group(c, {900: quest('Missing return', ends=[])})
        accept(c, 900); c.ns.readyToTurnIn[900] = True
        c.ns.ActivateRoute(c.ns.DungeonGuide(g)); c.ns.UpdateSelectedRoute(c.lua.table())
        self.assertFalse(c.ns.selectedRoute.complete)
        self.assertEqual(c.ns.selectedRoute.missing, 1)
        self.assertIn('Missing return', c.ns.routePaused)
        self.assertFalse(c.ns.Completed(900))

    def test_scan_preserves_return_phase_and_skips(self):
        c, g = running_dungeon()
        c.ns.readyToTurnIn[900] = True; c.ns.readyToTurnIn[901] = True
        c.ns.UpdateSelectedRoute(c.lua.table())
        c.ns.db.guideSkips[c.ns.self].quests[900] = True
        c.ns.ScanGuideProgress(); c.drain()
        self.assertEqual(c.ns.routeSelection.dungeonPhase, 'return')
        self.assertTrue(c.ns.GuideQuestSkipped(900))
        self.assertFalse(any(s.id == 900 for s in c.ns.selectedRoute.stops.values()))

    def test_reload_preserves_run_and_return_goal_scope(self):
        for phase in ('run', 'return'):
            c, g = running_dungeon()
            if phase == 'return':
                c.ns.readyToTurnIn[900] = True; c.ns.readyToTurnIn[901] = True
                c.ns.UpdateSelectedRoute(c.lua.table())
            c.ns.SaveSelectedGuide()
            saved = plain(c.ns.db)
            other = Client(quests=(900, 901), saved_variables=saved)
            other.guide_environment(); other.lua.globals().grouped = False
            dungeon(other); map_canvas(other)
            other.ns.ReadProfile(); other.ns.ReadQuests()
            other.ns.RestoreSavedGuide(); other.drain()
            self.assertEqual(other.ns.routeSelection.dungeonPhase, phase)
            self.assertEqual(set(other.ns.routeSelection.collectionGoals.keys()), {900, 901})
            self.assertFalse(any(s.kind == 'a' or s.dungeonEntrance for s in other.ns.selectedRoute.stops.values()))


class FlightCacheTests(unittest.TestCase):
    def test_reported_thunder_bluff_hillsbrad_trip_uses_flight_zeppelin_flight(self):
        c = solo(); map_canvas(c)
        c.lua.execute('C_Map.GetWorldPosFromMapPos=nil;C_Map.GetMapWorldSize=function()return 10000,10000 end')
        state = c.ns.db.flights[c.ns.self]
        for id in (22, 23, 11, 13):
            p = c.ns.travelData.nodes['TAXI_' + str(id)]
            state.nodes[id] = c.lua.table_from({'id': id, 'name': p.name, 'known': True, 'faction': 'Horde',
                'point': {'mapID': p.mapID, 'x': p.x, 'y': p.y}}, recursive=True)
        for a, b in ((22, 23), (11, 13)):
            state.edges[str(a) + ':' + str(b)] = c.lua.table_from({'source': a, 'destination': b})
        path = c.ns.FindTravelPath(state.nodes[22].point, point(c, 1424, .64, .597), True)
        self.assertEqual([(s.fromID, s.toID, s.method) for s in path.legs.values() if s.method != 'walk'], [
            ('TAXI_22', 'TAXI_23', 'taxi'),
            ('ZEPPELIN_ORGRIMMAR_TIRISFAL', 'ZEPPELIN_TIRISFAL_ORGRIMMAR', 'zeppelin'),
            ('TAXI_11', 'TAXI_13', 'taxi')])

    def test_confirmed_connection_survives_conflicting_discovery_flags_and_reload(self):
        c = flight_client(); c.ns.ReadFlightMap()
        c.lua.execute('''C_TaxiMap.GetTaxiNodesForMap=function()
            return {{nodeID=11,name='Start',isUndiscovered=true},
                    {nodeID=22,name='End',isUndiscovered=true}} end
            Enum.FlightPathFaction={Horde=1,Alliance=2,Neutral=3}
            C_TaxiMap.GetTaxiNodesForMap=function()
              return {{nodeID=11,name='Start',isUndiscovered=true,faction=1},
                      {nodeID=22,name='End',isUndiscovered=true,faction=1}} end''')
        c.ns.ReadKnownFlightPaths()
        flights = c.ns.db.flights[c.ns.self]
        self.assertTrue(flights.nodes[11].known); self.assertTrue(flights.nodes[22].known)
        self.assertIsNotNone(flights.edges['11:22'])
        self.assertGreater(c.ns.flightCacheConflicts, 0)
        other = Client(quests=(), saved_variables=plain(c.ns.db))
        self.assertIsNotNone(other.ns.db.flights[other.ns.self].edges['11:22'])
        self.assertEqual(other.ns.flightCacheRestored, 1)

    def test_actual_menu_unreachable_still_removes_connection(self):
        c = flight_client(); c.ns.ReadFlightMap()
        c.lua.execute('taxiNodes[2].state=80'); c.ns.ReadFlightMap()
        self.assertIsNone(c.ns.db.flights[c.ns.self].edges['11:22'])
        self.assertTrue(c.ns.db.flights[c.ns.self].nodes[22].known)

    def test_saved_world_geometry_survives_unavailable_native_projection(self):
        c = flight_client(include_geography=True); c.ns.ReadFlightMap()
        state = c.ns.db.flights[c.ns.self]
        old_world = plain(state.nodes[11].world)
        # A saved continent point is normalized back onto its city map at login.
        state.nodes[11].point = c.lua.table_from({'mapID': 1463, 'x': .4, 'y': .3})
        c.lua.execute('C_Map.GetWorldPosFromMapPos=nil;C_Map.GetMapPosFromWorldPos=nil')
        c.ns.InitializeTravel()
        self.assertEqual(plain(state.nodes[11].world), old_world)

    def test_fallback_estimates_only_price_confirmed_flights(self):
        c = network_client(nodes={'TAXI_9011': {'mapID': 501, 'x': .21, 'y': .37},
                                  'TAXI_9022': {'mapID': 502, 'x': .2, 'y': .37}})
        c.ns.travelData.edges = c.lua.table_from([{'from': 'TAXI_9011', 'to': 'TAXI_9022',
                                                 'method': 'walk', 'distance': 10000}], recursive=True)
        state = c.ns.db.flights[c.ns.self]
        for id, map_id, x in ((9011, 501, .21), (9022, 502, .2)):
            state.nodes[id] = c.lua.table_from({'id': id, 'known': True, 'name': str(id),
                                                'point': {'mapID': map_id, 'x': x, 'y': .37}}, recursive=True)
        c.lua.execute('C_Map.GetWorldPosFromMapPos=nil')
        path = c.ns.FindTravelPath(point(c), point(c, 502, .2), True)
        self.assertFalse(any(s.method == 'taxi' for s in path.legs.values()))
        state.edges['9011:9022'] = c.lua.table_from({'source': 9011, 'destination': 9022})
        path = c.ns.FindTravelPath(point(c), point(c, 502, .2), True)
        flight = next(s for s in path.legs.values() if s.method == 'taxi')
        self.assertEqual(flight.flight.timingBasis, 'Published travel distance estimate')
        state.timings['9011:9022'] = c.lua.table_from({'mean': 100, 'samples': 1, 'validated': True,
                                                     'build': c.ns.flightTimingBuild})
        path = c.ns.FindTravelPath(point(c), point(c, 502, .2), True)
        self.assertTrue(next(s for s in path.legs.values() if s.method == 'taxi').flight.measured)

    def test_saved_position_estimate_rejects_cross_continent_and_secret_values(self):
        c = network_client()
        c.lua.execute('C_Map.GetWorldPosFromMapPos=nil')
        a = c.lua.table_from({'world': {'continent': 1, 'x': 0, 'y': 0}}, recursive=True)
        b = c.lua.table_from({'world': {'continent': 1, 'x': 300, 'y': 400}}, recursive=True)
        self.assertEqual(c.ns.FlightPointDistance(a, b)[0], 500)
        b.world.continent = 2
        self.assertIsNone(c.ns.FlightPointDistance(a, b))
        b.world.continent = 1; b.world.x = c.lua.globals().secret
        self.assertIsNone(c.ns.FlightPointDistance(a, b))


def transport_client():
    c = network_client([{'from': 'A', 'to': 'B', 'seconds': 120, 'method': 'zeppelin'}])
    c.lua.globals().differentContinents = True
    stop = {'id': 900, 'kind': 'a', 'title': 'Remote', 'mapID': 502, 'x': .2, 'y': .37, 'label': 'Pickup'}
    c.ns.ActivateRoute(guide(c, (900,)), c.lua.table_from({'mapID': 502, 'stops': [stop]}, recursive=True))
    return c


class TransportDirectionTests(unittest.TestCase):
    def test_discovery_during_boarding_does_not_reset_transport(self):
        c = transport_client(); c.lua.execute('playerX=.9'); c.ns.UpdateNavigation()
        cursor = c.ns.travelPath.cursor
        c.lua.execute('''C_TaxiMap={GetTaxiNodesForMap=function()
            return {{nodeID=9011,name='Known flight',isUndiscovered=false}} end}''')
        c.ns.ReadKnownFlightPaths()
        self.assertEqual(c.ns.travelPath.cursor, cursor)
        self.assertEqual(c.ns.travelPath.transportIndex, cursor)

    def test_future_flight_does_not_hide_required_zeppelin(self):
        c = transport_client()
        path = c.ns.FindTravelPath(point(c), point(c, 502, .2), False)
        path.legs[len(path.legs) + 1] = c.lua.table_from({'method': 'taxi', 'flight': {
            'source': {'name': 'Undercity'}, 'destination': {'name': 'Tarren Mill'}}}, recursive=True)
        c.ns.travelPath = path
        summary = c.ns.TravelPathSummary(c.ns.selectedRoute.stops[1])
        self.assertIn('zeppelin', summary)
        self.assertNotIn('Walk to Undercity', summary)

    def test_boarding_holds_route_across_movement_missing_gps_and_arrival(self):
        c = transport_client()
        c.lua.execute('playerX=.9;clock=1;GetTime=function()return clock end')
        c.ns.UpdateNavigation()
        self.assertTrue(c.ns.navigation.state.stop.transportWaiting)
        self.assertIsNone(c.ns.navigation.state.angle)
        cursor = c.ns.travelPath.cursor
        # A vehicle can move on the departure map or briefly have no public GPS.
        c.lua.execute('playerX=.4;clock=10'); c.ns.UpdateNavigation()
        self.assertEqual(c.ns.travelPath.cursor, cursor)
        c.lua.execute('playerMap=0;clock=20'); c.ns.UpdateNavigation()
        self.assertTrue(c.ns.navigation.state.stop.transportWaiting)
        self.assertEqual(c.ns.travelPath.cursor, cursor)
        c.lua.execute('playerMap=503;playerX=.1;clock=30'); c.ns.UpdateNavigation()
        self.assertEqual(c.ns.travelPath.cursor, cursor)
        c.lua.execute('playerMap=502;playerX=.1;clock=40'); c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.state.stop.kind, 'a')
        self.assertFalse(c.ns.Completed(900))

    def test_boarding_line_does_not_point_back_to_dock_and_clear_releases_hold(self):
        c = transport_client(); c.lua.execute('playerX=.9'); c.ns.UpdateNavigation()
        points = c.ns.TravelLinePoints(point(c, x=.5), c.ns.selectedRoute.stops[1])
        self.assertFalse(points[1])
        c.ns.ClearRoute()
        self.assertIsNone(c.ns.travelPath)


if __name__ == '__main__':
    unittest.main()
