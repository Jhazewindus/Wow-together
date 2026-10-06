"""Romits' inconsistent flight-time report: capture, routes and safe measurements."""
import unittest

from test_060 import flight_client
from test_057 import plain


def connecting_route(c):
    c.lua.execute('''taxiNodes[3]={nodeID=99,name='Connecting stop',position=CreateVector2D(.4,.8),state=70,slotIndex=61}
        function GetNumRoutes(slot) return slot==54 and 2 or 1 end
        function TaxiGetNodeSlot(slot,index,source)
            if slot==61 then return source and 40 or 61 end
            if index==1 then return source and 40 or 61 end
            return source and 61 or 54
        end''')
    c.ns.ReadFlightMap()


class FlightTimingTests(unittest.TestCase):
    def test_native_connecting_stops_improve_untimed_estimate_in_both_planners(self):
        c = flight_client(); connecting_route(c)
        edge = c.ns.db.flights[c.ns.self].edges['11:22']
        self.assertEqual(list(edge.route.values()), [11, 99, 22])
        seconds, measured, basis = c.ns.FlightDuration(11, 22, 8800)
        self.assertGreater(seconds, 8800/32*1.35)
        self.assertFalse(measured); self.assertEqual(basis, 'Connecting-stop estimate')
        plan = c.ns.FindFlightPlan(c.ns.selectedRoute.stops[1])
        self.assertEqual(plan.flightSeconds, seconds)
        self.assertEqual(plan.timingBasis, basis)
        c.ns.NoteFlightSelection(54)
        self.assertEqual(c.ns.pendingFlight.expected, seconds)
        self.assertTrue(c.ns.pendingFlight.estimated)

    def test_missing_restricted_or_disconnected_native_routes_use_distance_estimate(self):
        for setup in ('GetNumRoutes=nil', 'function GetNumRoutes()return secret end',
                      'function TaxiGetNodeSlot()return secret end',
                      'function TaxiGetNodeSlot()return 61 end',
                      'function GetNumRoutes()return 1000 end'):
            c = flight_client(); connecting_route(c); c.lua.execute(setup); c.ns.ReadFlightMap()
            self.assertIsNone(c.ns.db.flights[c.ns.self].edges['11:22'].route)
            duration, measured, basis = c.ns.FlightDuration(11, 22, 8800)
            self.assertAlmostEqual(duration, 8800/32*1.35)
            self.assertFalse(measured); self.assertEqual(basis, 'Distance estimate')

    def test_departure_event_before_taxi_state_is_captured_with_panels_disabled(self):
        c = flight_client(); c.ns.ReadFlightMap(); c.ns.NoteFlightSelection(54)
        c.ns.db.config.routeArrow = False; c.ns.db.config.standaloneArrow = False
        c.ns.handlers.PLAYER_CONTROL_LOST()
        self.assertIsNone(c.ns.flightStarted)
        c.lua.execute('flying=true;clock=100.1'); c.drain()
        self.assertAlmostEqual(c.ns.flightStarted, 100.1)
        c.lua.execute('flying=false;clock=180.1'); c.ns.handlers.PLAYER_CONTROL_GAINED()
        self.assertAlmostEqual(c.ns.db.flights[c.ns.self].timings['11:22'].mean, 80)

    def test_native_close_before_selection_hook_still_identifies_manual_flight(self):
        c = flight_client(); c.ns.ReadFlightMap()
        c.ns.handlers.TAXIMAP_CLOSED()
        self.assertIsNone(c.ns.flightMapSource)
        c.ns.NoteFlightSelection(54)
        self.assertEqual(c.ns.pendingFlight.source, 11)
        self.assertEqual(c.ns.pendingFlight.destination, 22)
        # Also handle the departure event arriving before that hook.
        c.ns.db.config.routeArrow = False; c.ns.db.config.standaloneArrow = False
        c.lua.execute('flying=true;clock=100.1'); c.drain()
        self.assertAlmostEqual(c.ns.flightStarted, 100.1)

    def test_expired_closed_map_is_not_used_for_another_selection(self):
        c = flight_client(); c.ns.ReadFlightMap(); c.ns.handlers.TAXIMAP_CLOSED()
        c.lua.execute('clock=102'); c.ns.NoteFlightSelection(54)
        self.assertIsNone(c.ns.pendingFlight)

    def test_new_ride_after_missed_landing_does_not_include_previous_trip_time(self):
        c = flight_client(); c.ns.ReadFlightMap(); c.ns.NoteFlightSelection(54)
        c.lua.execute('flying=true'); c.ns.FlightState()
        c.ns.db.config.routeArrow = False; c.ns.db.config.standaloneArrow = False
        c.lua.execute('''flying=false;clock=180
            taxiNodes[1].state=70;taxiNodes[2].state=60''')
        c.ns.ReadFlightMap(); c.ns.NoteFlightSelection(40)
        self.assertIsNone(c.ns.flightStarted)
        c.lua.execute('flying=true'); c.drain()
        self.assertEqual(c.ns.flightStarted, 180)
        c.lua.execute('''flying=false;clock=260
            C_Map.GetPlayerMapPosition=function()return CreateVector2D(.02,.4)end''')
        c.ns.FinishFlight()
        self.assertEqual(c.ns.db.flights[c.ns.self].timings['22:11'].mean, 80)
        self.assertIsNone(c.ns.db.flights[c.ns.self].timings['11:22'])

    def test_landing_event_before_taxi_state_saves_after_short_retry(self):
        c = flight_client(); c.ns.ReadFlightMap(); c.ns.NoteFlightSelection(54)
        c.lua.execute('flying=true'); c.ns.handlers.PLAYER_CONTROL_LOST()
        c.lua.execute('clock=180'); c.ns.handlers.PLAYER_CONTROL_GAINED()
        self.assertIsNotNone(c.ns.pendingFlight)
        c.lua.execute('flying=false;clock=180.1'); c.drain()
        self.assertAlmostEqual(c.ns.db.flights[c.ns.self].timings['11:22'].mean, 80.1)
        self.assertIsNone(c.ns.pendingFlight)

    def test_missed_landing_event_is_completed_by_existing_navigation_update(self):
        c = flight_client(); c.ns.ReadFlightMap(); c.ns.NoteFlightSelection(54)
        c.lua.execute('flying=true'); c.ns.UpdateNavigation()
        c.lua.execute('flying=false;clock=180'); c.ns.UpdateNavigation()
        self.assertEqual(c.ns.db.flights[c.ns.self].timings['11:22'].mean, 80)
        self.assertIsNone(c.ns.flightStarted)
        before = c.ns.travelRevision
        c.ns.UpdateNavigation()
        self.assertEqual(c.ns.travelRevision, before)

    def test_interrupted_or_unconfirmed_arrival_never_poison_future_countdowns(self):
        for position in ("CreateVector2D(.4,.4)", 'nil', 'secret'):
            c = flight_client(); c.ns.ReadFlightMap(); c.ns.NoteFlightSelection(54)
            c.lua.execute('flying=true'); c.ns.FlightState()
            c.lua.execute(f'''flying=false;clock=180
                C_Map.GetPlayerMapPosition=function()return {position} end''')
            c.ns.FinishFlight()
            self.assertIsNone(c.ns.db.flights[c.ns.self].timings['11:22'])
            self.assertIn('arrival', c.ns.flightTimingStatus.lower())

    def test_delayed_landing_position_keeps_original_duration_without_postflight_walking(self):
        c = flight_client(); c.ns.ReadFlightMap(); c.ns.NoteFlightSelection(54)
        c.lua.execute('flying=true'); c.ns.FlightState()
        c.lua.execute('''flying=false;clock=180
            C_Map.GetPlayerMapPosition=function()return nil end''')
        c.ns.FinishFlight()
        self.assertIsNone(c.ns.db.flights[c.ns.self].timings['11:22'])
        c.lua.execute('clock=180.5;C_Map.GetPlayerMapPosition=function()return CreateVector2D(.9,.4)end')
        c.drain()
        self.assertEqual(c.ns.db.flights[c.ns.self].timings['11:22'].mean, 80)

    def test_new_flight_selection_cancels_previous_pending_arrival_check(self):
        c = flight_client(); c.ns.ReadFlightMap(); c.ns.NoteFlightSelection(54)
        c.lua.execute('flying=true'); c.ns.FlightState()
        c.lua.execute('''flying=false;clock=180
            C_Map.GetPlayerMapPosition=function()return nil end''')
        c.ns.FinishFlight()
        c.ns.NoteFlightSelection(54)
        c.lua.execute('C_Map.GetPlayerMapPosition=function()return CreateVector2D(.9,.4)end')
        c.drain()
        self.assertIsNone(c.ns.db.flights[c.ns.self].timings['11:22'])

    def test_confirmed_ride_is_shared_by_both_timer_panels_and_future_route_estimates(self):
        c = flight_client(); c.ns.ReadFlightMap(); c.ns.NoteFlightSelection(54)
        before = plain(c.ns.selectedRoute)
        c.lua.execute('flying=true'); c.ns.FlightState()
        c.lua.execute('flying=false;clock=180'); c.ns.FinishFlight()
        sample = c.ns.db.flights[c.ns.self].timings['11:22']
        self.assertTrue(sample.validated); self.assertEqual(sample.build, c.ns.flightTimingBuild)
        self.assertEqual(c.ns.FlightDuration(11, 22, 8800), (80, True, 'Timed flight'))
        c.ns.NoteFlightSelection(54); c.ns.SetOption('standaloneArrow', True)
        c.lua.execute('flying=true'); c.ns.FlightState()
        c.lua.execute('clock=190'); c.ns.UpdateNavigation()
        self.assertIn('1m 10s', c.ns.standaloneNavigation.timer.text)
        self.assertEqual(c.ns.navigation.distance.text, c.ns.standaloneNavigation.timer.text)
        self.assertEqual(plain(c.ns.selectedRoute), before)
        self.assertFalse(c.ns.Completed(900)); self.assertFalse(c.ns.GuideQuestSkipped(900))

    def test_native_route_change_or_new_build_does_not_reuse_another_trip_duration(self):
        c = flight_client(); connecting_route(c); c.ns.NoteFlightSelection(54)
        c.lua.execute('flying=true'); c.ns.FlightState()
        c.lua.execute('flying=false;clock=180'); c.ns.FinishFlight()
        self.assertTrue(c.ns.FlightDuration(11, 22, 8800)[1])
        c.ns.db.flights[c.ns.self].edges['11:22'].route = c.lua.table_from([11, 22])
        self.assertFalse(c.ns.FlightDuration(11, 22, 8800)[1])
        connecting_route(c); c.ns.flightTimingBuild = 'new build'
        self.assertFalse(c.ns.FlightDuration(11, 22, 8800)[1])

    def test_old_unverified_measurement_is_retained_but_replaced_after_a_valid_ride(self):
        c = flight_client(); c.ns.ReadFlightMap()
        state = c.ns.db.flights[c.ns.self]
        state.timings['11:22'] = c.lua.table_from({'mean': 700, 'samples': 10})
        self.assertFalse(c.ns.FlightDuration(11, 22, 8800)[1])
        self.assertEqual(state.timings['11:22'].mean, 700)
        c.ns.NoteFlightSelection(54); c.lua.execute('flying=true'); c.ns.FlightState()
        c.lua.execute('flying=false;clock=180'); c.ns.FinishFlight()
        self.assertEqual(state.timings['11:22'].mean, 80)
        self.assertEqual(state.timings['11:22'].samples, 1)

    def test_stale_failed_selection_is_not_assigned_to_an_unrelated_later_flight(self):
        c = flight_client(); c.ns.ReadFlightMap(); c.ns.NoteFlightSelection(54)
        c.lua.execute('flying=true;clock=150'); current = c.ns.FlightState()
        self.assertIsNone(c.ns.pendingFlight)
        self.assertIsNone(current.remaining)
        c.lua.execute('flying=false;clock=180'); c.ns.FinishFlight()
        self.assertIsNone(c.ns.db.flights[c.ns.self].timings['11:22'])

    def test_unknown_flight_state_never_finalizes_a_ride_and_retries_are_bounded(self):
        c = flight_client(); c.ns.ReadFlightMap(); c.ns.NoteFlightSelection(54)
        c.lua.execute('flying=true'); c.ns.FlightState()
        c.lua.execute('clock=180;UnitOnTaxi=function()return secret end')
        c.ns.handlers.PLAYER_CONTROL_GAINED(); c.drain()
        self.assertIsNotNone(c.ns.pendingFlight)
        self.assertIsNone(c.ns.db.flights[c.ns.self].timings['11:22'])


if __name__ == '__main__':
    unittest.main()
