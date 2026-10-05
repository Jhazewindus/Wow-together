"""Independent travel search, arrow ownership and reported guide-switch failure."""
import unittest

from test_addon import Client
from test_navigation import navigator
from test_063 import guide_client, zone, order
from test_061 import run_plan, world_quest
from test_068 import maps
from test_routes import catalogue, guide, map_canvas
from test_060 import flight_client
from test_057 import plain


def point(c, map_id=501, x=.21, y=.37):
    return c.lua.table_from({'mapID': map_id, 'x': x, 'y': y})


def network_client(edges=None, nodes=None):
    c = guide_client(2); maps(c)
    nodes = nodes or {'A': {'mapID': 501, 'x': .9, 'y': .37, 'name': 'East gate'},
                      'B': {'mapID': 502, 'x': .1, 'y': .37, 'name': 'West gate'}}
    c.ns.travelData = c.lua.table_from({'nodes': nodes, 'edges': edges or [
        {'from': 'A', 'to': 'B', 'seconds': 0, 'method': 'walk'}], 'factors': {}}, recursive=True)
    return c


class TravelSearchTests(unittest.TestCase):
    def test_cross_zone_walk_uses_explicit_crossing_and_never_a_direct_jump(self):
        c = network_client()
        path = c.ns.FindTravelPath(point(c), point(c, 502, .2), False)
        self.assertEqual([(s.fromID, s.toID) for s in path.legs.values()], [('START', 'A'), ('A', 'B'), ('B', 'GOAL')])
        self.assertAlmostEqual(path.seconds, (690 + 100) * 1.25 / 7)
        c.ns.travelData.edges = c.lua.table()
        self.assertIsNone(c.ns.FindTravelPath(point(c), point(c, 502, .2), False))

    def test_shortest_path_uses_time_not_fewest_links_and_handles_zero_cycles(self):
        nodes = {'A': {'mapID': 501, 'x': .21, 'y': .37},
                 'B': {'mapID': 502, 'x': .2, 'y': .37},
                 'C': {'mapID': 503, 'x': .2, 'y': .37}}
        edges = [{'from': 'A', 'to': 'B', 'seconds': 100, 'method': 'ship'},
                 {'from': 'A', 'to': 'C', 'seconds': 10, 'method': 'ship'},
                 {'from': 'C', 'to': 'A', 'seconds': 0, 'method': 'walk'},
                 {'from': 'C', 'to': 'B', 'seconds': 15, 'method': 'ship'}]
        c = network_client(edges, nodes)
        path = c.ns.FindTravelPath(point(c), point(c, 502, .2), False)
        self.assertEqual(path.seconds, 25)
        self.assertEqual([s.toID for s in path.legs.values()], ['A', 'C', 'B', 'GOAL'])

    def test_one_way_transport_and_faction_gates_do_not_create_reverse_or_hostile_links(self):
        c = network_client([{'from': 'A', 'to': 'B', 'seconds': 120, 'method': 'zeppelin', 'faction': 'Horde'}])
        c.lua.globals().differentContinents = True
        self.assertIsNotNone(c.ns.FindTravelPath(point(c), point(c, 502, .2), False))
        self.assertIsNone(c.ns.FindTravelPath(point(c, 502, .2), point(c), False))
        for faction in ('Alliance', 'Unknown'):
            c.ns.profile.faction = faction
            self.assertIsNone(c.ns.FindTravelPath(point(c), point(c, 502, .2), False))

    def test_private_positions_and_negative_costs_never_make_a_path(self):
        c = network_client([{'from': 'A', 'to': 'B', 'seconds': -1, 'method': 'ship'}])
        self.assertIsNone(c.ns.FindTravelPath(point(c), point(c, 502, .2), False))
        origin = point(c); origin.x = c.lua.globals().secret
        self.assertIsNone(c.ns.FindTravelPath(origin, point(c, 502, .2), False))
        self.assertIsNone(c.ns.WalkingDistance(501, point(c), c.lua.table_from({'mapID': 501})))
        self.assertEqual(c.ns.NormalizedDistance(point(c), c.lua.table_from({'mapID': 501})), float('inf'))

    def test_flight_links_are_character_owned_and_can_form_multiple_legs(self):
        c = flight_client(); c.ns.ReadFlightMap()
        c.ns.travelData = c.lua.table_from({'nodes': {}, 'edges': {}, 'factors': {}}, recursive=True)
        state = c.ns.db.flights[c.ns.self]
        c.lua.execute('C_Map.GetPlayerMapPosition=function() return CreateVector2D(.02,.4) end')
        middle = {'id': 33, 'name': 'Middle', 'point': {'mapID': 501, 'x': .5, 'y': .4}, 'known': True}
        state.nodes[33] = c.lua.table_from(middle, recursive=True)
        state.edges['11:22'] = None
        state.edges['11:33'] = c.lua.table_from({'source': 11, 'destination': 33})
        state.edges['33:22'] = c.lua.table_from({'source': 33, 'destination': 22})
        for key in ('11:33', '33:22'):
            state.timings[key] = c.lua.table_from({'mean': 15, 'samples': 1})
        goal = c.ns.selectedRoute.stops[1]
        path = c.ns.FindTravelPath(point(c, 501, .02, .4), goal, True)
        self.assertEqual([s.toID for s in path.legs.values() if s.method == 'taxi'], ['TAXI_33', 'TAXI_22'])
        state.nodes[33].known = False
        path = c.ns.FindTravelPath(point(c, 501, .02, .4), goal, True)
        self.assertFalse(any(s.method == 'taxi' for s in path.legs.values()))

    def test_navigation_advances_travel_points_without_changing_quest_step_or_credit(self):
        c = network_client()
        goal = {'id': 900, 'kind': 'a', 'title': 'Remote quest', 'mapID': 502, 'x': .2, 'y': .37, 'label': 'Pickup'}
        c.ns.ActivateRoute(guide(c, (900,)), c.lua.table_from({'mapID': 502, 'stops': [goal]}, recursive=True))
        c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.state.stop.kind, 'travel')
        self.assertEqual(c.ns.navigation.state.stop.x, .9)
        c.lua.execute('playerX=.9'); c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.state.stop.mapID, 502)
        c.lua.execute('playerMap=502;playerX=.1'); c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.state.stop.kind, 'a')
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 900)
        self.assertFalse(c.ns.Completed(900))
        c.ns.ClearRoute()
        self.assertIsNone(c.ns.travelPath)

    def test_boarding_arrival_waits_for_transport_destination_and_lines_have_a_gap(self):
        c = network_client([{'from': 'A', 'to': 'B', 'seconds': 120, 'method': 'ship'}])
        c.lua.globals().differentContinents = True
        stop = {'id': 900, 'kind': 'a', 'title': 'Remote quest', 'mapID': 502, 'x': .2, 'y': .37, 'label': 'Pickup'}
        c.ns.ActivateRoute(guide(c, (900,)), c.lua.table_from({'mapID': 502, 'stops': [stop]}, recursive=True))
        c.lua.execute('playerX=.9'); c.ns.UpdateNavigation()
        state = c.ns.navigation.state
        self.assertTrue(state.arrived)
        self.assertIn('Take the ship', state.status)
        self.assertEqual(c.ns.travelPath.cursor, 2)
        line_points = c.ns.TravelLinePoints(point(c, 501, .9), c.ns.selectedRoute.stops[1])
        self.assertIn(False, list(line_points.values()))
        c.ns.UpdateNavigation()
        self.assertEqual(c.ns.travelPath.cursor, 2)
        c.lua.execute('playerMap=502;playerX=.1'); c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.state.stop.kind, 'a')

    def test_missing_world_projection_can_use_local_scale_and_unavailable_data_retries(self):
        c = network_client()
        c.lua.execute('C_Map.GetWorldPosFromMapPos=nil; clock=1; function GetTime() return clock end')
        self.assertIsNotNone(c.ns.FindTravelPath(point(c), point(c, 502, .2), False))
        c.lua.execute('oldScale=C_Map.GetMapWorldSize; C_Map.GetMapWorldSize=function() return secret,secret end')
        stop = point(c, 502, .2); stop.id, stop.kind, stop.title = 900, 'a', 'Remote'
        self.assertIsNone(c.ns.TravelNetworkDestination(stop))
        c.lua.execute('C_Map.GetMapWorldSize=oldScale;clock=3')
        self.assertIsNotNone(c.ns.TravelNetworkDestination(stop))

    def test_toggle_uses_original_direction_and_does_not_change_fixed_plan(self):
        c = network_client(); g = zone(c)
        c.ns.GenerateFixedGuide(g, False); before = order(g)
        goal = point(c, 502, .2); goal.id, goal.kind, goal.title = 900, 'a', 'Remote'
        self.assertIsNotNone(c.ns.TravelNetworkDestination(goal))
        c.ns.SetOption('travelNetwork', False)
        self.assertIsNone(c.ns.TravelNetworkDestination(goal))
        self.assertEqual(order(g), before)

    def test_new_zone_and_large_detour_recompute_travel_only(self):
        c = network_client(); c.lua.execute('clock=1;function GetTime() return clock end')
        stop = point(c, 502, .2); stop.id, stop.kind, stop.title = 900, 'a', 'Remote'
        c.ns.TravelNetworkDestination(stop)
        c.lua.execute('playerX=.7;clock=4')
        c.ns.TravelNetworkDestination(stop)
        self.assertEqual(c.ns.travelPath.origin.x, .7)
        c.lua.execute('playerMap=502;playerX=.15;clock=5')
        self.assertIsNone(c.ns.TravelNetworkDestination(stop))
        self.assertEqual(c.ns.travelPath.origin.mapID, 502)

    def test_owned_flight_point_projected_onto_outer_zone_does_not_bypass_city_gate(self):
        c = network_client(nodes={'TAXI_23': {'mapID': 503, 'x': .5, 'y': .5, 'name': 'City flight', 'faction': 'Horde'}})
        c.ns.db.flights[c.ns.self].nodes[23] = c.lua.table_from({'id': 23, 'name': 'Owned', 'known': True,
            'point': {'mapID': 501, 'x': .21, 'y': .37}}, recursive=True)
        self.assertIsNone(c.ns.FindTravelPath(point(c), point(c, 503, .6), True))

    def test_shipped_data_has_forever_crossings_gates_and_transports_without_unconfirmed_flights(self):
        c = Client(quests=())
        self.assertEqual(len(list(c.ns.travelData.nodes.keys())), 256)
        methods = {edge.method for edge in c.ns.travelData.edges.values()}
        self.assertEqual(methods, {'walk', 'ship', 'zeppelin', 'tram', 'transition'})
        self.assertEqual(c.ns.travelData.nodes['DOCK_VALANAAR'].mapID, 2521)
        self.assertEqual(c.ns.travelData.nodes['ENTRANCE_C1411_455_119'].faction, 'Horde')
        self.assertTrue(any(s['from'] == 'BORDER_DUROTAR_TO_THE_BARRENS' and s.to == 'BORDER_THE_BARRENS_TO_DUROTAR' for s in c.ns.travelData.edges.values()))

    def test_missing_taxi_map_id_uses_published_point_but_still_requires_a_reachable_observation(self):
        c = flight_client()
        c.lua.execute("GetTaxiMapID=nil; FlightMapFrame=CreateFrame('Frame');FlightMapFrame:Show();function FlightMapFrame:GetMapID() return 501 end;taxiNodes={{nodeID=23,name='Orgrimmar',state=60,slotIndex=1},{nodeID=25,name='Crossroads',state=70,slotIndex=2}}")
        c.ns.ReadFlightMap()
        state = c.ns.db.flights[c.ns.self]
        self.assertEqual(state.nodes[25].point.mapID, 1413)
        self.assertTrue(state.nodes[25].known)
        self.assertIsNotNone(state.edges['23:25'])


class StandaloneTests(unittest.TestCase):
    def test_independent_visibility_and_facing_updates_without_the_large_panel(self):
        c = navigator(); c.ns.SetOption('standaloneArrow', True); c.ns.SetOption('routeArrow', False)
        self.assertFalse(c.ns.navigation.IsShown(c.ns.navigation))
        small = c.ns.standaloneNavigation
        self.assertTrue(small.IsShown(small))
        self.assertEqual(small.distance.text, c.ns.FormatDistance(c.ns.navigation.state.distance))
        before = small.state.angle
        c.lua.execute('facing=1')
        small.OnUpdate(small, .1)
        self.assertAlmostEqual(small.state.angle, before - 1)
        c.ns.ClearRoute(); c.ns.UpdateNavigation()
        self.assertFalse(small.IsShown(small))

    def test_shared_state_has_one_poll_when_both_arrows_are_shown(self):
        c = navigator(); c.ns.SetOption('standaloneArrow', True)
        c.lua.execute('reads=0; function GetPlayerFacing() reads=reads+1;return 0 end')
        c.ns.navigation.OnUpdate(c.ns.navigation, .1)
        c.ns.standaloneNavigation.OnUpdate(c.ns.standaloneNavigation, .1)
        self.assertEqual(c.lua.globals().reads, 1)

    def test_small_arrow_position_is_separate_and_persists_after_reload(self):
        c = navigator(); c.ns.SetOption('standaloneArrow', True)
        c.lua.execute('function smallPoint() return "CENTER",UIParent,"CENTER",45,-70 end')
        frame = c.ns.standaloneNavigation; frame.GetPoint = c.lua.globals().smallPoint; frame.OnDragStop(frame)
        self.assertEqual(c.ns.db.standaloneArrowPosition.x, 45)
        self.assertIsNone(c.ns.db.arrowPosition)
        other = Client(quests=(), saved_variables=plain(c.ns.db))
        self.assertTrue(other.ns.Option('standaloneArrow'))
        self.assertEqual(other.ns.standaloneNavigation.point[4], 45)


class GuideSwitchTests(unittest.TestCase):
    def test_missing_turnin_before_mapped_followup_does_not_crash_compiler(self):
        c = guide_client(2)
        first = world_quest('Parent'); first['ends'] = []
        second = world_quest('Child', previousQuest=900)
        catalogue(c, {900: first, 901: second})
        g = zone(c); c.ns.ShowGuideOnMap(g); run_plan(c)
        self.assertIsNone(c.ns.routePlanningError)
        self.assertEqual(c.ns.routeSelection.key, g.key)
        self.assertTrue(any(s.unknownLocation for s in g.fixedPlan.values()))

    def test_retired_placeholders_are_excluded_from_new_and_retained_guides(self):
        c = guide_client(4)
        catalogue(c, {899: world_quest('<UNUSED>', level=0), 900: world_quest('Real first'),
                      901: world_quest('Real second'), 902: world_quest('zzOLD UNUSED placeholder')})
        g = zone(c)
        self.assertEqual({r.id for r in g.records.values()}, {900, 901})
        c.ns.GenerateFixedGuide(g, False)
        g.fixedPlan[1].id, g.fixedPlan[1].title = 899, '<UNUSED>'
        route = c.ns.BuildFixedGuideRoute(g, False)
        self.assertNotEqual(route.pendingStop and route.pendingStop.title, '<UNUSED>')
        self.assertFalse(c.ns.LevelingQuestEnabled(899))

    def test_shipped_mulgore_durotar_mulgore_switch_works_at_level_twelve(self):
        c = Client(quests=(), use_catalogue=True); c.guide_environment(level=12); map_canvas(c)
        c.lua.globals().grouped = False
        c.unit_names({'player': ('Alice', 'Test Realm')})
        c.ns.profile.classID, c.ns.profile.raceID = 8, 8
        choices = {g.zone: g for g in c.ns.LevelingGuideChoices().values()}
        for name in ('Mulgore', 'Durotar', 'Mulgore', 'Durotar'):
            c.ns.ShowGuideOnMap(choices[name]); run_plan(c, maximum=5000)
            self.assertIsNone(c.ns.routePlanningErrorDetail)
            self.assertEqual(c.ns.routeSelection.zone, name)
            self.assertFalse(any(c.ns.IsRetiredQuest(s.id) for s in c.ns.routeSelection.fixedPlan.values()))

    def test_friends_shipped_durotar_guide_starts_for_level_five_horde_warrior(self):
        c = Client(quests=(), use_catalogue=True); c.guide_environment(level=5); map_canvas(c)
        c.lua.globals().grouped = False; c.unit_names({'player': ('Gladiator', 'Eliaapje')})
        c.ns.profile.classID, c.ns.profile.raceID = 1, 2
        g = next(g for g in c.ns.LevelingGuideChoices().values() if g.zone == 'Durotar')
        c.ns.ShowGuideOnMap(g); run_plan(c, maximum=5000)
        self.assertIsNone(c.ns.routePlanningErrorDetail)
        self.assertEqual(c.ns.routeSelection.zone, 'Durotar')


if __name__ == '__main__':
    unittest.main()
