"""Prospective flight checks use owned landings, time costs and bounded fallbacks.

Ratchet/Crossroads positions reproduce the screenshot with synthetic physical
map transforms. Reference links are not proven Forever menu availability.
"""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_070 import network_client
from test_routes import guide
from import_travel_network import flight_facts


def ratchet_client():
    c = network_client()
    c.lua.execute('''
      playerMap=1413; playerX=.603; playerY=.387
      bounds[1413]={x=0,width=10000}; bounds[502]={x=12000,width=10000}
      C_Map.GetMapWorldSize=function(map) return bounds[map].width,6667 end
      C_Map.GetWorldPosFromMapPos=function(map,p)
        local b=bounds[map]; if not b then return end
        local x,y=p:GetXY(); return 1,CreateVector2D(b.x+x*b.width,y*6667) end
      C_Map.GetMapPosFromWorldPos=function(_,p,map)
        local b=bounds[map]; if not b then return end
        local x,y=p:GetXY(); return map,CreateVector2D((x-b.x)/b.width,y/6667) end
      C_Map.GetMapInfo=function(map) return {name=map==1413 and 'The Barrens' or 'Test destination'} end
      function GetUnitSpeed() return 7,7 end
      now=0; function GetTime() return now end
      C_Map.SetUserWaypoint=function() error('Discovery must not set a user pin') end
    ''')
    points = {25: {'mapID': 1413, 'x': .515, 'y': .3041, 'name': 'Crossroads', 'faction': 'Horde'},
              80: {'mapID': 1413, 'x': .6312, 'y': .3711, 'name': 'Ratchet', 'faction': 'Both'},
              22: {'mapID': 502, 'x': .2, 'y': .37, 'name': 'Destination', 'faction': 'Horde'}}
    c.ns.travelData = c.lua.table_from({'nodes': {'TAXI_'+str(i): p for i, p in points.items()},
        'edges': [{'from': 'TAXI_25', 'to': 'TAXI_22', 'method': 'walk', 'distance': 9000}],
        'factors': {}, 'settlements': [], 'flightConnections': [
            {'source': 80, 'destination': 25, 'seconds': 69, 'faction': 'Horde'},
            {'source': 25, 'destination': 22, 'seconds': 100, 'faction': 'Horde'}]}, recursive=True)
    state = c.ns.db.flights[c.ns.self]
    state.nodes = c.lua.table_from({i: {'id': i, 'name': p['name'], 'point': p,
        'faction': p['faction'], 'known': i != 80} for i, p in points.items()}, recursive=True)
    state.edges = c.lua.table_from({'25:22': {'source': 25, 'destination': 22}}, recursive=True)
    state.timings = c.lua.table_from({'25:22': {'mean': 100, 'samples': 1,
        'validated': True, 'build': c.ns.flightTimingBuild}}, recursive=True)
    stop = dict(points[22], id=900, kind='a', title='Destination quest', label='Talk to the quest giver')
    # Ordinary refreshes can rebuild this synthetic guide from its catalogue.
    # Keep its real pickup at the same destination as the selected route.
    q = c.ns.CatalogueQuest(900)
    q.starts = c.lua.table_from([points[22]], recursive=True)
    q.ends = c.lua.table_from([points[22]], recursive=True)
    c.ns.ActivateRoute(guide(c, (900,)), c.lua.table_from({'mapID': 502, 'stops': [stop]}, recursive=True))
    c.ns.UpdateNavigation()
    return c


class FlightDiscoveryRoutingTests(unittest.TestCase):
    def test_ratchet_screenshot_uses_shorter_check_without_unlocking_or_reordering(self):
        c = ratchet_client()
        state = c.ns.db.flights[c.ns.self]
        current = c.ns.selectedRoute.stops[1]
        discovery = c.ns.navigation.state.stop
        self.assertEqual(discovery.flightDiscovery.source.id, 80)
        self.assertEqual(discovery.flightDiscovery.destination.id, 22)
        self.assertGreater(discovery.flightDiscovery.savedSeconds, 30)
        self.assertLessEqual(discovery.flightDiscovery.extraSeconds, 150)
        self.assertEqual((current.id, current.kind, current.mapID), (900, 'a', 502))
        self.assertFalse(c.ns.Completed(900)); self.assertFalse(c.ns.GuideQuestSkipped(900))
        self.assertFalse(state.nodes[80].known)
        self.assertEqual(set(state.edges.keys()), {'25:22'})
        self.assertIn('confirm at the flight master', c.ns.navigation.context.text)
        self.assertTrue(c.ns.navigation.context.text.startswith('Check flights at Ratchet'))
        self.assertEqual(c.ns.navigation.skipStep.caption.text, 'Keep walking')

    def test_executable_graph_still_uses_only_menu_confirmed_edges(self):
        c = ratchet_client()
        path = c.ns.FindTravelPath(c.ns.PlayerPoint(1413), c.ns.selectedRoute.stops[1], True)
        self.assertEqual([s.fromID for s in path.legs.values() if s.method == 'taxi'], ['TAXI_25'])
        self.assertFalse(any(s.flight and s.flight.unconfirmed for s in path.legs.values()))

    def test_map_line_ends_at_check_instead_of_drawing_unconfirmed_air_route(self):
        c = ratchet_client()
        lines = c.ns.TravelLinePoints(c.ns.PlayerPoint(1413), c.ns.selectedRoute.stops[1])
        self.assertEqual(len(lines), 3)
        self.assertAlmostEqual(lines[2].x, .6312)
        self.assertFalse(lines[3])

    def test_known_landings_connections_and_faction_are_required(self):
        for change in ('missing', 'reverse', 'wrong-faction', 'locked', 'blocked', 'hostile'):
            with self.subTest(change=change):
                c = ratchet_client(); state = c.ns.db.flights[c.ns.self]
                if change == 'missing': c.ns.travelData.flightConnections = c.lua.table()
                elif change == 'reverse':
                    e = c.ns.travelData.flightConnections[1]; e.source, e.destination = 25, 80
                elif change == 'wrong-faction': c.ns.travelData.flightConnections[1].faction = 'Alliance'
                elif change == 'locked': state.nodes[25].known = False
                elif change == 'blocked': state.unreachable['80:22'] = c.ns.flightTimingBuild; state.unreachable['80:25'] = c.ns.flightTimingBuild
                else: state.nodes[80].faction = 'Alliance'
                c.ns.ResetTravelPath(); c.ns.UpdateNavigation()
                self.assertIsNone(c.ns.navigation.state.stop.flightDiscovery)

    def test_slow_reference_flight_and_far_detours_do_not_qualify(self):
        for change in ('slow', 'far'):
            c = ratchet_client()
            if change == 'slow': c.ns.travelData.flightConnections[1].seconds = 600
            else: c.ns.travelData.nodes['TAXI_80'].x = .8; c.ns.db.flights[c.ns.self].nodes[80].point.x = .8
            c.ns.ResetTravelPath(); c.ns.UpdateNavigation()
            self.assertIsNone(c.ns.navigation.state.stop.flightDiscovery)

    def test_time_not_nearest_master_alone_selects_the_candidate(self):
        c = ratchet_client()
        c.ns.travelData.nodes['TAXI_9080'] = c.lua.table_from({'mapID': 1413, 'x': .635, 'y': .3711,
            'name': 'Other master', 'faction': 'Horde'})
        c.ns.travelData.flightConnections[3] = c.lua.table_from({'source': 9080, 'destination': 22,
            'seconds': 25, 'faction': 'Horde'})
        c.ns.ResetTravelPath(); c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.state.stop.flightDiscovery.source.id, 9080)

    def test_keep_walking_does_not_skip_a_quest_and_changes_arrow_and_map(self):
        c = ratchet_client()
        c.ns.navigation.skipStep.OnClick()
        self.assertIsNone(c.ns.navigation.state.stop.flightDiscovery)
        self.assertFalse(c.ns.GuideQuestSkipped(900))
        self.assertEqual(len(c.ns.db.guideSkips[c.ns.self].steps), 0)
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 900)
        lines = c.ns.TravelLinePoints(c.ns.PlayerPoint(1413), c.ns.selectedRoute.stops[1])
        self.assertGreater(len(lines), 3)

    def test_standalone_only_explains_and_dismisses_without_opening_the_browser(self):
        c = ratchet_client()
        c.ns.SetOption('routeArrow', False); c.ns.SetOption('standaloneArrow', True)
        arrow = c.ns.standaloneNavigation
        self.assertEqual(arrow.title.text, 'Visit Ratchet')
        self.assertTrue(arrow.tip.IsShown(arrow.tip))
        self.assertIn('Potential saving', arrow.tip.text.text)
        arrow.tip.close.OnClick()
        self.assertIsNone(c.ns.navigation.state.stop.flightDiscovery)
        self.assertFalse(c.ns.GuideQuestSkipped(900))

    def test_opening_nearer_menu_replaces_check_with_a_confirmed_flight(self):
        c = ratchet_client()
        c.ns.SetOption('autoFly', True)
        c.lua.execute('''
          playerX=.6312; playerY=.3711
          Enum.FlightPathState={Current=1,Reachable=2,Unreachable=3}
          function GetTaxiMapID() return 1413 end
          C_TaxiMap={GetAllTaxiNodes=function() return {
            {nodeID=80,name='Ratchet',state=1,slotIndex=1},
            {nodeID=25,name='Crossroads',state=2,slotIndex=2},
            {nodeID=22,name='Destination',state=2,slotIndex=3}} end}
          selectedSlot=nil; function TakeTaxiNode(slot) selectedSlot=slot end
        ''')
        c.ns.ReadFlightMap()
        self.assertIsNone(c.ns.navigation.state.stop.flightDiscovery)
        self.assertEqual(c.ns.navigation.state.stop.kind, 'f')
        self.assertTrue(c.ns.db.flights[c.ns.self].nodes[80].known)
        plan = c.ns.navigation.state.stop.flightPlan
        self.assertEqual(plan.source.id, 80)
        self.assertEqual(c.lua.globals().selectedSlot, c.ns.visibleFlights[plan.destination.id].slot)
        self.assertIn(plan.destination.id, (25, 22))
        self.assertFalse(bool(c.ns.navigation.state.stop.travelLeg.flight.unconfirmed))

    def test_failed_or_unreachable_menu_keeps_known_fallback_without_repeated_check(self):
        c = ratchet_client()
        c.lua.execute('''
          playerX=.6312; playerY=.3711
          Enum.FlightPathState={Current=1,Reachable=2,Unreachable=3}
          function GetTaxiMapID() return 1413 end
          C_TaxiMap={GetAllTaxiNodes=function() return {
            {nodeID=80,name='Ratchet',state=1,slotIndex=1},
            {nodeID=25,name='Crossroads',state=3,slotIndex=2},
            {nodeID=22,name='Destination',state=3,slotIndex=3}} end}
          function TakeTaxiNode() error('Cannot fly an unreachable route') end
        ''')
        c.ns.SetOption('autoFly', True); c.ns.ReadFlightMap()
        self.assertIsNone(c.ns.navigation.state.stop.flightDiscovery)
        self.assertIsNone(c.ns.db.flights[c.ns.self].edges['80:25'])
        self.assertEqual(c.ns.db.flights[c.ns.self].unreachable['80:25'], c.ns.flightTimingBuild)

    def test_navigation_refresh_reuses_calculation_but_movement_reconsiders_it(self):
        c = ratchet_client()
        c.lua.execute('''local ns=...; old=ns.FindFlightDiscoveryPlan; calculations=0
          ns.FindFlightDiscoveryPlan=function(...) calculations=calculations+1; return old(...) end''', c.ns)
        for _ in range(10): c.ns.UpdateNavigation()
        self.assertEqual(c.lua.globals().calculations, 0)
        c.lua.execute('playerX=.55; now=10'); c.ns.UpdateNavigation()
        self.assertGreater(c.lua.globals().calculations, 0)

    def test_movement_does_not_count_the_old_walk_twice_when_comparing_savings(self):
        c = ratchet_client()
        old = c.ns.travelPath
        c.lua.execute('playerX=.588; now=10')
        origin, goal = c.ns.PlayerPoint(1413), c.ns.selectedRoute.stops[1]
        self.assertIsNone(c.ns.FindFlightDiscoveryPlan(origin, goal, old))
        # Moving towards Ratchet makes the visit useful; price it from here,
        # rather than reusing the old Crossroads walking cost.
        c.lua.execute('playerX=.618')
        origin = c.ns.PlayerPoint(1413)
        fresh = c.ns.FindTravelPath(origin, goal, True)
        plan = c.ns.FindFlightDiscoveryPlan(origin, goal, old)
        self.assertIsNotNone(plan)
        self.assertAlmostEqual(plan.savedSeconds, fresh.seconds - plan.seconds)

    def test_options_combat_preview_and_private_position_do_not_create_checks(self):
        for code in ('combat=true', 'C_Map.GetPlayerMapPosition=function() return secret end'):
            c = ratchet_client(); c.lua.execute(code); c.ns.UpdateNavigation()
            self.assertIsNone(c.ns.navigation.state.stop.flightDiscovery)
        for option in ('nearbyFlights', 'suggestFlights', 'travelNetwork'):
            c = ratchet_client(); c.ns.SetOption(option, False)
            self.assertIsNone(c.ns.navigation.state.stop.flightDiscovery)


class FlightReferenceImportTests(unittest.TestCase):
    def test_reference_import_preserves_direction_faction_and_ratchet_neutral_owner(self):
        text = '''local _,ns=...; ns.Edges={
          {from="TAXI_80",to="TAXI_25",method="taxi",cost=69,requirements={faction="Horde"}},
          {from="TAXI_25",to="TAXI_23",method="taxi",cost=142,requirements={faction="Horde"}},
          {from="TAXI_80",to="TAXI_23",method="taxi",cost=10,requirements={class="Mage",faction="Horde"}}}'''
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'Flights.lua'; p.write_text(text)
            with self.assertRaises(ValueError): flight_facts(p, {})
            nodes = {'TAXI_80': {}, 'TAXI_25': {}, 'TAXI_23': {}}
            with patch('import_travel_network.FLIGHTS_SHA256', hashlib.sha256(p.read_bytes()).hexdigest()):
                rows = flight_facts(p, nodes)
            self.assertEqual([(r['source'], r['destination']) for r in rows], [(25, 23), (80, 25)])
            self.assertEqual(nodes['TAXI_80']['faction'], 'Both')
            self.assertEqual(nodes['TAXI_25']['faction'], 'Horde')


if __name__ == '__main__':
    unittest.main()
