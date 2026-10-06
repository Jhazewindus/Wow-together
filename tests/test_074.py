"""Shared travel decisions and asynchronous guide scans, under Lua 5.1.

Synthetic flights and drawing mocks do not certify the live Forever client.
"""
import unittest

from test_060 import flight_client
from test_063 import guide_client, zone, order
from test_073 import travel_client
from test_routes import guide


def tick(c):
    timers = c.lua.globals().timers
    callback = timers[1]
    c.lua.eval('table.remove')(timers, 1)
    callback()


def scanning_client(count=2):
    c = guide_client(count)
    c.lua.execute('function GetPlayerFacing() return 0 end; C_Map.GetMapWorldSize=function() return 1000,1000 end')
    g = zone(c)
    c.ns.GenerateFixedGuide(g, False)
    c.ns.ActivateRoute(g, c.ns.BuildFixedGuideRoute(g, True))
    c.ns.UpdateNavigation(); c.drain()
    return c, g


class SharedTravelTests(unittest.TestCase):
    def test_native_flight_refreshes_arrow_map_and_action_together(self):
        c = flight_client()
        c.ns.UpdateNavigation(); c.ns.DrawRoute()
        self.assertEqual(c.ns.RouteForDisplay().stops[1].kind, 'q')
        c.ns.db.config.autoFly = True
        c.ns.ReadFlightMap()
        self.assertEqual(c.ns.navigation.state.stop.flightPlan.destination.id, 22)
        self.assertEqual(c.ns.routeProvider.pins[1].stop.kind, 'f')
        self.assertEqual(c.lua.globals().taken, 54)
        self.assertIn('fly to End', c.ns.travelNetworkStatus)

    def test_walking_approach_names_the_upcoming_flight(self):
        c = flight_client()
        c.lua.execute("taxiNodes[1].position=CreateVector2D(.12,.4)")
        c.ns.ReadFlightMap()
        # Current-master position is grounded at the player; move away afterwards.
        c.lua.execute('C_Map.GetPlayerMapPosition=function() return CreateVector2D(.001,.4) end')
        c.ns.ResetTravelPath(); c.ns.UpdateNavigation()
        stop = c.ns.navigation.state.stop
        self.assertEqual(stop.travelLeg.method, 'walk')
        self.assertIn('flight master', stop.label)
        self.assertIn('then fly to End', c.ns.navigation.context.text)
        self.assertEqual(c.ns.selectedRoute.stops[1].kind, 'q')

    def test_terminal_graph_walk_cannot_be_overridden_by_legacy_flight(self):
        c = flight_client()
        c.ns.ReadFlightMap()
        c.ns.FindTravelPath = c.lua.eval('function(origin,goal) return {goal=goal,origin=origin,cursor=1,seconds=1,legs={{from=origin,to=goal,toID="GOAL",method="walk"}}} end')
        c.ns.ResetTravelPath()
        c.ns.db.config.autoFly = True
        c.ns.TrySuggestedFlight()
        self.assertIsNone(c.lua.globals().taken)
        self.assertEqual(c.ns.TravelDestination(c.ns.selectedRoute.stops[1]).kind, 'q')
        self.assertIsNotNone(c.ns.FindFlightPlan(c.ns.selectedRoute.stops[1]))

    def test_graph_disabled_keeps_legacy_flight_available(self):
        c = flight_client(); c.ns.ReadFlightMap()
        c.ns.SetOption('travelNetwork', False)
        c.ns.db.config.autoFly = True; c.ns.TrySuggestedFlight()
        self.assertEqual(c.lua.globals().taken, 54)

    def test_recent_fallback_cache_cannot_override_a_newly_connected_graph(self):
        c = flight_client(); c.ns.ReadFlightMap()
        c.ns.FindTravelPath = c.lua.eval('function() return nil end')
        c.ns.ResetTravelPath()
        self.assertEqual(c.ns.TravelDestination(c.ns.selectedRoute.stops[1]).kind, 'f')
        c.ns.FindTravelPath = c.lua.eval('function(origin,goal) return {goal=goal,origin=origin,cursor=1,seconds=100,legs={{from=origin,to=goal,toID="GOAL",method="walk"}}} end')
        c.ns.ResetTravelPath()
        # The fallback cache is deliberately kept within its one-second lifetime.
        self.assertEqual(c.ns.TravelDestination(c.ns.selectedRoute.stops[1]).kind, 'q')

    def test_actual_flight_hides_ground_lines_then_restores_after_landing(self):
        c = flight_client(); c.ns.db.config.autoFly = True; c.ns.ReadFlightMap()
        c.lua.execute('flying=true')
        c.ns.handlers.PLAYER_CONTROL_LOST()
        self.assertTrue(c.ns.RouteForDisplay().flying)
        self.assertEqual(c.ns.RouteForDisplay().stops[1].x, .95)
        self.assertEqual(c.ns.RouteForDisplay().stops[1].id, 900)
        self.assertEqual(c.ns.routeStats.lines, 0)
        self.assertIn('Flying', c.ns.navigation.status.text)
        c.lua.execute('flying=false; C_Map.GetPlayerMapPosition=function() return CreateVector2D(.9,.4) end')
        c.ns.handlers.PLAYER_CONTROL_GAINED()
        self.assertFalse(c.ns.RouteForDisplay().flying)
        self.assertGreater(c.ns.routeStats.lines, 0)
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 900)

    def test_city_gate_reconsiders_new_flight_before_navigation_and_action(self):
        c = travel_client()
        c.ns.ShowGuideOnMap(c.ns.OrgrimmarTravelGuide())
        self.assertAlmostEqual(c.ns.selectedRoute.stops[1].x, .115)
        c.lua.execute('''
        C_Map.GetMapWorldSize=function() return 10000,10000 end
        C_Map.GetWorldPosFromMapPos=function(map,p) local x,y=p:GetXY(); return 1,CreateVector2D(x*10000,y*10000) end
        function GetTaxiMapID() return 501 end
        Enum.FlightPathState={Current=60,Reachable=70,Unreachable=80}
        C_TaxiMap={GetAllTaxiNodes=function() return {
          {nodeID=11,name='Start',state=60,position=CreateVector2D(.21,.37),slotIndex=1},
          {nodeID=22,name='Orgrimmar flight',state=70,position=CreateVector2D(.517,.858),slotIndex=2}}
        end}
        function TakeTaxiNode(slot) taken=slot end
        ''')
        c.ns.travelData.nodes.TAXI_22 = c.lua.table_from({'mapID':1454,'x':.517,'y':.858,'name':'Orgrimmar flight'})
        c.ns.db.config.autoFly = True
        c.ns.db.flights[c.ns.self].timings['11:22'] = c.lua.table_from({'mean': 15, 'samples': 1})
        c.ns.ReadFlightMap()
        self.assertAlmostEqual(c.ns.selectedRoute.stops[1].x, .517)
        self.assertEqual(c.ns.navigation.state.stop.flightPlan.destination.id, 22)
        self.assertEqual(c.lua.globals().taken, 2)


class GuideSpinnerTests(unittest.TestCase):
    def test_scan_immediately_shows_loop_then_restores_arrow_and_fixed_order(self):
        c, g = scanning_client()
        before = order(g)
        c.ns.SetOption('standaloneArrow', True)
        c.ns.navigation.scan.OnClick()
        self.assertEqual(c.ns.navigation.state.status, 'Scanning guide…')
        self.assertFalse(c.ns.navigation.scan.enabled)
        for frame in (c.ns.standaloneNavigation,):
            self.assertTrue(all(line.IsShown(line) for line in frame.icon.spinnerLines.values()))
            self.assertTrue(all(not line.IsShown(line) for line in frame.icon.lines.values()))
            self.assertFalse(frame.symbol.IsShown(frame.symbol))
        self.assertFalse(c.ns.navigation.icon.IsShown(c.ns.navigation.icon))
        first = tuple(c.ns.standaloneNavigation.icon.spinnerLines[1].startPoint.values())
        c.ns.navigation.OnUpdate(c.ns.navigation, .1)
        self.assertNotEqual(first, tuple(c.ns.standaloneNavigation.icon.spinnerLines[1].startPoint.values()))
        c.drain()
        self.assertIsNone(c.ns.guideScanning)
        self.assertEqual(order(g), before)
        for frame in (c.ns.standaloneNavigation,):
            self.assertTrue(all(not line.IsShown(line) for line in frame.icon.spinnerLines.values()))
            self.assertTrue(any(line.IsShown(line) for line in frame.icon.lines.values()))

    def test_large_scan_yields_between_history_batches_and_coalesces_clicks(self):
        c, g = scanning_client(85)
        c.ns.ScanGuideProgress()
        busy = c.ns.guideScanning
        c.ns.ScanGuideProgress()
        self.assertEqual(c.lua.eval('function(a,b) return a==b end')(busy, c.ns.guideScanning), True)
        tick(c)
        self.assertIsNotNone(c.ns.guideScanning)
        self.assertEqual(c.ns.navigation.state.status, 'Scanning guide…')
        c.drain()
        self.assertIn('85/85 checked', c.ns.guideScanStatus)
        self.assertIsNone(c.ns.guideScanning)

    def test_clear_or_new_selection_cancels_old_scan_callbacks(self):
        for clear in (True, False):
            c, g = scanning_client(85)
            c.ns.ScanGuideProgress(); tick(c)
            if clear: c.ns.ClearRoute()
            else:
                c.ns.ActivateRoute(guide(c, (901,), key='replacement'))
            c.drain(); c.ns.UpdateNavigation()
            self.assertIsNone(c.ns.guideScanning)
            self.assertEqual(c.ns.routeSelection.key if c.ns.routeSelection else None,
                             None if clear else 'replacement')

    def test_error_clears_spinner_and_retains_the_selected_guide(self):
        c, g = scanning_client()
        c.ns.ReadGuide = c.lua.eval('function() error("test read failed") end')
        c.ns.ScanGuideProgress(); c.drain()
        self.assertIsNone(c.ns.guideScanning)
        self.assertEqual(c.ns.routeSelection.key, g.key)
        self.assertIn('failed', c.ns.guideScanStatus)
        self.assertIn('test read failed', c.ns.guideScanError)
        self.assertTrue(all(not l.IsShown(l) for l in c.ns.navigation.icon.spinnerLines.values()))

    def test_missing_timer_and_internal_reads_never_leave_spinner_stuck(self):
        c, g = scanning_client()
        c.ns.ScanGuideProgress(g, False)
        self.assertIsNone(c.ns.guideScanning)
        c.lua.execute('C_Timer.After=nil')
        c.ns.ScanGuideProgress()
        self.assertIsNone(c.ns.guideScanning)
        self.assertIn('timer API missing', c.ns.guideScanStatus)

    def test_hidden_main_panel_keeps_standalone_loop_moving(self):
        c, g = scanning_client()
        c.ns.SetOption('standaloneArrow', True); c.ns.SetOption('routeArrow', False)
        c.ns.ScanGuideProgress()
        small = c.ns.standaloneNavigation
        first = tuple(small.icon.spinnerLines[1].startPoint.values())
        small.OnUpdate(small, .1)
        self.assertNotEqual(first, tuple(small.icon.spinnerLines[1].startPoint.values()))
        c.drain()
        self.assertTrue(small.IsShown(small))
        self.assertFalse(c.ns.navigation.IsShown(c.ns.navigation))

    def test_adaptive_scan_hands_spinner_to_cooperative_route_generation(self):
        c, g = scanning_client()
        c.ns.SetOption('fixedZoneGuides', False); c.drain()
        g.fixedRoute, g.fixedPlan = False, None
        c.ns.ScanGuideProgress()
        tick(c)
        self.assertIsNone(c.ns.guideScanning)
        self.assertIsNotNone(c.ns.routePlanning)
        self.assertEqual(c.ns.navigation.state.status, 'Loading route…')
        c.drain()
        self.assertIsNone(c.ns.routePlanning)
        self.assertFalse(c.ns.navigation.state.busy)

    def test_missing_drawing_api_still_finishes_scan_without_geometry_errors(self):
        c, g = scanning_client()
        c.ns.navigation.icon.CreateLine = False
        c.ns.ScanGuideProgress()
        self.assertTrue(c.ns.navigation.symbol.IsShown(c.ns.navigation.symbol))
        c.drain()
        self.assertIsNone(c.ns.guideScanning)


if __name__ == '__main__':
    unittest.main()
