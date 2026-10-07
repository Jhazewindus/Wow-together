"""Nearby flight discovery is advice, not an unlock or a quest replan.

Real published Sun Rock coordinates plus synthetic physical scales reproduce
the screenshot position. These checks do not prove current beta geography/API
delivery, terrain access or native rendering.
"""
import unittest

from test_087 import tip_client
from test_068 import maps
from test_addon import Client
from test_060 import flight_client


class FlightDiscoveryTests(unittest.TestCase):
    def test_sun_rock_screenshot_position_gets_advice_with_known_barrens_flight(self):
        c = tip_client(inn=False, flight=True)
        published = Client().ns.travelData.nodes['TAXI_29']
        c.ns.travelData.nodes = c.lua.table_from({'TAXI_29': dict(published)}, recursive=True)
        # No settlement-label entry: the whole native-ID catalogue is used.
        c.ns.guideServiceData.taxis = c.lua.table()
        c.lua.execute('''
          C_Map.GetBestMapForUnit=function() return 1442 end
          C_Map.GetPlayerMapPosition=function() return {GetXY=function() return .496,.610 end} end
          C_Map.GetMapWorldSize=function() return 5000,3333 end
        ''')
        flights = c.ns.db.flights[c.ns.self]
        flights.nodes[25] = c.lua.table_from({'name': 'Crossroads', 'known': True})
        flights.nodes[29] = c.lua.table_from({'name': 'Sun Rock Retreat', 'known': False,
            'unlockConfirmed': True, 'faction': 'Horde'})
        before = [(s.id, s.kind, s.x, s.y) for s in c.ns.selectedRoute.stops.values()]
        value = c.ns.CurrentGuideTip()
        self.assertEqual(value.taxiID, 29)
        self.assertIn('Get flight path — Sun Rock Retreat', value.text)
        self.assertIn('future trips', value.text)
        self.assertGreater(value.distance * .9144, 150)
        self.assertLess(value.distance * .9144, 350)
        self.assertEqual(before, [(s.id, s.kind, s.x, s.y) for s in c.ns.selectedRoute.stops.values()])
        self.assertEqual(len(flights.edges), 0)

    def test_short_onward_detour_is_allowed_but_backtracking_and_far_masters_are_not(self):
        c = tip_client(inn=False, flight=True)
        c.lua.execute('C_Map.GetMapWorldSize=function() return 10000,10000 end')
        p = c.ns.travelData.nodes['TAXI_9000']
        p.x, p.y = .27, .37  # 549 m away, on the current leg.
        self.assertIsNotNone(c.ns.CurrentGuideTip())
        self.assertEqual(c.ns.CurrentGuideTip().extraWalking, 0)
        self.assertIn('Short detour', c.ns.CurrentGuideTip().text)
        c.ns.selectedRoute.stops[1].x = .21  # Would mean a long round trip.
        self.assertIsNone(c.ns.CurrentGuideTip())  # Goal change invalidates cache.
        c.ns.selectedRoute.stops[1].x = .9
        p.x = .3  # On the way, but beyond the 750 m horizon.
        c.lua.globals().clock = 3
        self.assertIsNone(c.ns.CurrentGuideTip())

    def test_onward_detour_is_bounded_in_physical_units(self):
        c = tip_client(inn=False, flight=True)
        c.lua.execute('C_Map.GetMapWorldSize=function() return 10000,10000 end')
        p = c.ns.travelData.nodes['TAXI_9000']
        p.x, p.y = .25, .40
        self.assertIsNotNone(c.ns.CurrentGuideTip())
        p.y = .43; c.lua.globals().clock = 3
        self.assertIsNone(c.ns.CurrentGuideTip())

    def test_native_only_continent_position_is_projected_into_current_zone(self):
        c = tip_client(inn=False)
        maps(c)
        c.ns.db.flights[c.ns.self].nodes[9009] = c.lua.table_from({
            'name': 'New beta flight master', 'faction': 'Horde', 'known': False,
            'unlockConfirmed': True, 'point': {'mapID': 10, 'x': .25/3, 'y': .37}}, recursive=True)
        value = c.ns.CurrentGuideTip()
        self.assertEqual(value.taxiID, 9009)
        self.assertEqual(value.place.mapID, 501)
        self.assertAlmostEqual(value.place.x, .25)
        self.assertAlmostEqual(value.distance, 40)
        self.assertEqual(len(c.ns.db.flights[c.ns.self].edges), 0)

    def test_unknown_ownership_restricted_flags_and_enemy_flags_do_not_invent_unlocks(self):
        c = tip_client(inn=False, flight=True)
        c.ns.guideServiceData.taxis[9000].faction = None
        self.assertIsNone(c.ns.CurrentGuideTip())
        c.ns.guideServiceData.taxis[9000].faction = 'Horde'
        node = c.lua.table_from({'name': 'Flight master', 'faction': 'Horde'})
        node.known, node.unlockConfirmed = c.lua.globals().secret, c.lua.globals().secret
        c.ns.db.flights[c.ns.self].nodes[9000] = node
        c.lua.globals().clock = 3
        self.assertEqual(c.ns.CurrentGuideTip().kind, 'flight-check')
        node.faction = 'Alliance'; c.lua.globals().clock = 5
        self.assertIsNone(c.ns.CurrentGuideTip())

    def test_hostile_settlement_crossing_prevents_an_optional_detour(self):
        c = tip_client(inn=False, flight=True)
        c.ns.travelData.settlements = c.lua.table_from([{
            'name': 'Enemy town', 'faction': 'Alliance', 'mapID': 501,
            'minX': .22, 'maxX': .23, 'minY': .3, 'maxY': .4}], recursive=True)
        self.assertIsNone(c.ns.CurrentGuideTip())
        self.assertIn('crossing blocked', c.ns.nearbyFlightStatus)

    def test_standalone_tip_is_visible_and_dismissible_without_quest_skips(self):
        c = tip_client(inn=False, flight=True)
        c.ns.SetOption('standaloneArrow', True)
        c.ns.SetOption('routeArrow', False)
        arrow = c.ns.standaloneNavigation
        self.assertTrue(arrow.tip.IsShown(arrow.tip))
        self.assertIn('Test flight', arrow.tip.text.text)
        self.assertIn('future trips', arrow.tip.text.text)
        # The standalone-only layout also reserves the shared quest reason.
        self.assertTrue(arrow.reason.IsShown(arrow.reason))
        self.assertEqual(arrow.height, 102 + arrow.reason.height + 4 + 56)
        arrow.tip.close.OnClick()
        self.assertFalse(arrow.tip.IsShown(arrow.tip))
        self.assertFalse(c.ns.GuideQuestSkipped(900))
        self.assertEqual(arrow.height, 102 + arrow.reason.height + 4)

    def test_one_banner_and_automatic_removal_after_confirmed_unlock(self):
        c = tip_client(inn=False, flight=True)
        c.ns.SetOption('standaloneArrow', True)
        c.ns.UpdateNavigation()
        self.assertTrue(c.ns.navigation.tip.IsShown(c.ns.navigation.tip))
        self.assertFalse(c.ns.standaloneNavigation.tip.IsShown(c.ns.standaloneNavigation.tip))
        c.ns.db.flights[c.ns.self].nodes[9000] = c.lua.table_from({'name': 'Flight master', 'known': True})
        c.ns.travelRevision = (c.ns.travelRevision or 0) + 1
        c.ns.UpdateNavigation()
        self.assertFalse(c.ns.navigation.tip.IsShown(c.ns.navigation.tip))
        self.assertIsNone(c.ns.CurrentGuideTip())

    def test_flight_map_confirms_current_master_without_unlocking_other_points(self):
        c = flight_client()
        c.ns.ReadFlightMap()
        self.assertTrue(c.ns.db.flights[c.ns.self].nodes[11].known)
        self.assertTrue(c.ns.checkedFlightNodes[11])
        self.assertEqual(set(c.ns.db.flights[c.ns.self].edges), {'11:22'})

    def test_metrics_and_diagnostics_do_not_claim_every_beta_flight_master_is_mapped(self):
        c = tip_client(inn=False, flight=True)
        c.ns.UpdateNavigation()
        lines = []
        c.ns.GuideTipDiagnostics(lines.append)
        self.assertTrue(any('350 metres' in s and '200 metres' in s for s in lines))
        self.assertTrue(any('1 bundled taxi locations' in s for s in lines))
        self.assertTrue(any('Test flight' in s for s in lines))


if __name__ == '__main__':
    unittest.main()
