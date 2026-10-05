"""Flight unlock detection and event-driven refresh under Lua 5.1.

Public API-shaped fixtures verify state logic, not actual Forever API behavior.
"""
import unittest

from test_addon import Client
from test_060 import flight_client
from test_057 import plain


def discovery_client():
    c = flight_client()
    c.lua.execute("""
    Enum.FlightPathFaction={Neutral=0,Horde=1,Alliance=2}
    mapReads={}
    mapNodes={
      {nodeID=11,name='Start',position=CreateVector2D(.02,.4),faction=1,isUndiscovered=false},
      {nodeID=22,name='End',position=CreateVector2D(.9,.4),faction=1,isUndiscovered=false},
      {nodeID=33,name='Locked',position=CreateVector2D(.6,.4),faction=1,isUndiscovered=true},
      {nodeID=44,name='Enemy master',position=CreateVector2D(.6,.4),faction=2,isUndiscovered=false},
      {nodeID=55,name='Unknown',position=CreateVector2D(.6,.4),faction=1},
      {nodeID=66,name='Private',position=secret,faction=1,isUndiscovered=secret}}
    C_Map.GetMapInfo=function(id) return {name='Test',parentMapID=id==501 and 601 or 0} end
    C_TaxiMap.GetTaxiNodesForMap=function(id)
      mapReads[#mapReads+1]=id; return id==601 and mapNodes or {}
    end
    """)
    return c


class FlightMapTests(unittest.TestCase):
    def test_global_getter_supplies_required_map_id_without_namespaced_getter(self):
        c = flight_client()
        self.assertIsNone(c.lua.globals().C_TaxiMap.GetTaxiMapID)
        c.ns.handlers.TAXIMAP_OPENED(0)  # The event argument is a taxi system, not a map.
        self.assertEqual(c.ns.flightMapSource, 11)
        self.assertTrue(c.ns.db.flights[c.ns.self].nodes[22].known)
        self.assertIsNotNone(c.ns.db.flights[c.ns.self].edges['11:22'])
        self.assertIn('GetTaxiMapID', c.ns.flightMapStatus)
        self.assertIsNotNone(c.ns.FindFlightPlan(c.ns.selectedRoute.stops[1]))

    def test_visible_frame_fallback_is_guarded_and_never_uses_event_system_as_map(self):
        c = flight_client()
        c.lua.execute("""
        GetTaxiMapID=nil;FlightMapFrame=CreateFrame('Frame');FlightMapFrame:Show()
        function FlightMapFrame:GetMapID() return 501 end
        """)
        c.ns.handlers.TAXIMAP_OPENED(2)
        self.assertIn('FlightMapFrame.GetMapID', c.ns.flightMapStatus)
        self.assertEqual(c.ns.flightMapSource, 11)
        c.lua.globals().FlightMapFrame.Hide(c.lua.globals().FlightMapFrame)
        c.ns.ReadFlightMap()
        self.assertIsNone(c.ns.visibleFlights)
        self.assertIn('No public flight map ID', c.ns.flightMapStatus)

    def test_missing_or_private_map_id_never_calls_api_with_nil_or_guesses_player_zone(self):
        c = flight_client()
        c.lua.execute("""
        function GetTaxiMapID() return secret end
        C_TaxiMap.GetAllTaxiNodes=function(id) error('Must never call with guessed map') end
        """)
        c.ns.ReadFlightMap()
        self.assertEqual(len(c.ns.db.flights[c.ns.self].nodes), 0)
        self.assertIn('No public flight map ID', c.ns.travelStatus)

    def test_late_node_data_retries_and_closing_cancels_stale_reads_and_actions(self):
        c = flight_client()
        c.lua.execute("""
        ready=false;reads=0
        C_TaxiMap.GetAllTaxiNodes=function(id)
          assert(id==501);reads=reads+1;return ready and taxiNodes or {}
        end
        """)
        c.ns.handlers.TAXIMAP_OPENED(0)
        self.assertIn('not returned any nodes', c.ns.flightMapStatus)
        c.lua.globals().ready = True; c.drain()
        self.assertEqual(c.ns.flightMapSource, 11)
        c.ns.handlers.TAXIMAP_CLOSED(); c.lua.globals().ready = False
        c.ns.handlers.TAXIMAP_OPENED(0); c.ns.handlers.TAXIMAP_CLOSED()
        before = c.lua.globals().reads
        c.ns.db.config.autoFly = True; c.lua.globals().ready = True; c.drain()
        self.assertEqual(c.lua.globals().reads, before)
        self.assertIsNone(c.lua.globals().taken)
        self.assertIsNone(c.ns.visibleFlights)

    def test_retry_budget_is_bounded_and_error_has_a_specific_reason(self):
        c = flight_client()
        c.lua.execute("reads=0;C_TaxiMap.GetAllTaxiNodes=function(id) reads=reads+1;error('beta read failed') end")
        c.ns.handlers.TAXIMAP_OPENED(0); c.drain()
        self.assertEqual(c.lua.globals().reads, 4)
        self.assertIn('failed or returned restricted', c.ns.flightMapStatus)
        self.assertEqual(len(c.ns.db.flights[c.ns.self].edges), 0)
        self.assertIsNone(c.ns.visibleFlights)

    def test_public_ownership_survives_unreachable_state_but_stale_connection_is_removed(self):
        c = flight_client(); c.ns.ReadFlightMap()
        c.lua.globals().taxiNodes[2].state = 80
        c.ns.handlers.TAXIMAP_OPENED(0)
        self.assertTrue(c.ns.db.flights[c.ns.self].nodes[22].known)
        self.assertIsNone(c.ns.db.flights[c.ns.self].edges['11:22'])
        self.assertIsNone(c.ns.FindFlightPlan(c.ns.selectedRoute.stops[1]))

    def test_secret_slot_can_recognize_public_unlock_but_never_select_a_flight(self):
        c = flight_client(); c.ns.db.config.autoFly = True
        c.lua.globals().taxiNodes[2].slotIndex = c.lua.globals().secret
        c.ns.handlers.TAXIMAP_OPENED(0)
        self.assertTrue(c.ns.db.flights[c.ns.self].nodes[22].known)
        self.assertIsNone(c.ns.visibleFlights[22].slot)
        self.assertIsNone(c.lua.globals().taken)


class UnlockTests(unittest.TestCase):
    def test_public_map_flags_recognize_unlocked_paths_but_cannot_invent_connections(self):
        c = discovery_client(); c.ns.ReadKnownFlightPaths()
        state = c.ns.db.flights[c.ns.self]
        self.assertTrue(state.nodes[11].known); self.assertTrue(state.nodes[22].known)
        self.assertFalse(state.nodes[33].known)
        for id in (44, 55, 66): self.assertIsNone(state.nodes[id])
        self.assertEqual(len(state.edges), 0)
        self.assertIsNone(c.ns.FindFlightPlan(c.ns.selectedRoute.stops[1]))
        self.assertEqual(list(c.lua.globals().mapReads.values()), [501, 601])
        c.ns.ReadFlightMap()
        self.assertIsNotNone(c.ns.FindFlightPlan(c.ns.selectedRoute.stops[1]))

    def test_discovery_events_coalesce_and_recognize_a_new_unlock_without_party_sync(self):
        c = discovery_client(); c.ns.SetOption('soloMode', True)
        c.ns.handlers.PLAYER_LOGIN(); c.drain()
        c.lua.globals().mapReads = c.lua.table()
        c.lua.globals().mapNodes[3].isUndiscovered = False
        c.ns.handlers.TAXI_NODE_STATUS_CHANGED(); c.ns.handlers.TAXI_NODE_STATUS_CHANGED()
        c.ns.handlers.ZONE_CHANGED_NEW_AREA(); c.drain()
        self.assertTrue(c.ns.db.flights[c.ns.self].nodes[33].known)
        self.assertEqual(list(c.lua.globals().mapReads.values()), [501, 601])
        self.assertEqual(c.ns.TransportState().queued, 0)
        self.assertIsNone(c.lua.globals().taken)

    def test_unknown_flags_keep_old_positive_evidence_and_explicit_locked_flag_revokes_edges(self):
        c = discovery_client(); c.ns.ReadFlightMap()
        c.lua.globals().mapNodes[2].isUndiscovered = c.lua.globals().secret
        c.ns.ReadKnownFlightPaths()
        state = c.ns.db.flights[c.ns.self]
        self.assertTrue(state.nodes[22].known)
        self.assertIsNotNone(state.edges['11:22'])
        c.lua.globals().mapNodes[2].isUndiscovered = True
        c.ns.ReadKnownFlightPaths()
        self.assertFalse(state.nodes[22].known)
        self.assertIsNone(state.edges['11:22'])

    def test_discovered_path_without_coordinates_is_known_but_not_routable(self):
        c = discovery_client()
        c.lua.globals().mapNodes[1].nodeID = 77777  # No published fallback coordinates.
        c.lua.globals().mapNodes[1].position = c.lua.globals().secret
        c.ns.ReadKnownFlightPaths()
        self.assertTrue(c.ns.db.flights[c.ns.self].nodes[77777].known)
        self.assertIsNone(c.ns.db.flights[c.ns.self].nodes[77777].point)
        self.assertEqual(len(c.ns.db.flights[c.ns.self].edges), 0)

    def test_saved_unlocks_are_personal_and_diagnostics_do_not_select_or_query_flights(self):
        c = discovery_client(); c.ns.ReadKnownFlightPaths(); saved = plain(c.ns.db)
        same = Client(quests=(), saved_variables=saved)
        other = Client(name='Different', quests=(), saved_variables=saved)
        self.assertTrue(same.ns.db.flights[same.ns.self].nodes[22].known)
        self.assertEqual(len(other.ns.db.flights[other.ns.self].nodes), 0)
        c.lua.execute("""
        function GetTaxiMapID() error('probe must not query') end
        C_TaxiMap.GetAllTaxiNodes=function() error('probe must not query') end
        """)
        c.ns.Diagnostics()
        self.assertIn('GetTaxiMapID: present', c.ns.diagnosticsText.text)
        self.assertIn('C_TaxiMap.GetTaxiNodesForMap: present', c.ns.diagnosticsText.text)
        self.assertIn('Flight paths: 2 known;', c.ns.diagnosticsText.text)
        self.assertIn('0 observed connections', c.ns.diagnosticsText.text)
        self.assertIsNone(c.lua.globals().taken)


if __name__ == '__main__': unittest.main()
