"""Optional guide service tips: physical range, useful hubs and character state."""
import json
import unittest

from test_addon import Client, ROOT
from test_navigation import navigator


def tip_client(inn=True, flight=False):
    c = navigator()
    c.lua.execute('clock=1; function GetTime() return clock end; function GetBindLocation() return "Old home" end')
    c.ns.guideServiceData = c.lua.table_from({'inns': [{
        'id': 'INN_500', 'npcID': 500, 'name': 'Test hub', 'faction': 'Horde',
        'mapID': 501, 'x': .23, 'y': .37}] if inn else [],
        'taxis': {9000: {'name': 'Test flight', 'faction': 'Horde'}} if flight else {}}, recursive=True)
    c.ns.travelData = c.lua.table_from({'nodes': {'TAXI_9000': {
        'mapID': 501, 'x': .24, 'y': .37}}, 'edges': [], 'factors': {}}, recursive=True)
    steps = [dict(id=900, kind='q', title='Work away', mapID=501, x=.9, y=.37),
             dict(id=900, kind='t', title='Return one', mapID=501, x=.23, y=.37),
             dict(id=901, kind='t', title='Return two', mapID=501, x=.24, y=.37)]
    c.ns.selectedRoute.stops = c.lua.table_from(steps, recursive=True)
    return c


class GuideServiceTipTests(unittest.TestCase):
    def test_flight_range_uses_150_metres_on_small_and_large_maps(self):
        for width in (1000, 10000):
            c = tip_client(inn=False, flight=True)
            c.lua.globals().mapWidth = width
            c.lua.execute('C_Map.GetMapWorldSize=function() return mapWidth,1000 end')
            point = c.ns.travelData.nodes['TAXI_9000']
            point.x = .21 + 149.9 / .9144 / width
            self.assertIsNotNone(c.ns.CurrentGuideTip())
            point.x = .21 + 150.1 / .9144 / width
            c.lua.globals().clock = 3
            self.assertIsNone(c.ns.CurrentGuideTip())

    def test_flight_unlocks_are_character_specific_and_unknown_is_not_locked(self):
        c = tip_client(inn=False, flight=True)
        self.assertIn('Check flight path', c.ns.CurrentGuideTip().text)
        state = c.ns.db.flights[c.ns.self]
        state.nodes[9000] = c.lua.table_from({'id': 9000, 'name': 'Test flight', 'known': False,
            'unlockConfirmed': True, 'point': {'mapID': 501, 'x': .24, 'y': .37}}, recursive=True)
        c.lua.globals().clock = 3
        self.assertIn('Get flight path', c.ns.CurrentGuideTip().text)
        state.nodes[9000].known = True
        c.lua.globals().clock = 5
        self.assertIsNone(c.ns.CurrentGuideTip())
        state.nodes[9000] = None
        c.ns.db.flights['Other-TestRealm'] = c.lua.table_from({'nodes': {9000: {'known': True}}}, recursive=True)
        c.lua.globals().clock = 7
        self.assertIsNotNone(c.ns.CurrentGuideTip())

    def test_faction_and_public_positions_filter_tips(self):
        c = tip_client(inn=False, flight=True)
        metadata = c.ns.guideServiceData.taxis[9000]
        for owner in ('Alliance', None):
            metadata.faction = owner
            c.lua.globals().clock += 2
            self.assertIsNone(c.ns.CurrentGuideTip())
        metadata.faction = 'Both'; c.lua.globals().clock += 2
        self.assertIsNotNone(c.ns.CurrentGuideTip())
        c.lua.execute('C_Map.GetPlayerMapPosition=function() return secret end; clock=20')
        self.assertIsNone(c.ns.CurrentGuideTip())

    def test_native_owner_flags_override_settlement_assumptions(self):
        c = tip_client(inn=False, flight=True)
        metadata = c.ns.guideServiceData.taxis[9000]
        metadata.faction = None
        self.assertIsNone(c.ns.CurrentGuideTip())
        node = c.lua.table_from({'id': 9000, 'name': 'Native master', 'known': False,
            'unlockConfirmed': True, 'faction': 'Horde',
            'point': {'mapID': 501, 'x': .24, 'y': .37}}, recursive=True)
        c.ns.db.flights[c.ns.self].nodes[9000] = node
        c.lua.globals().clock = 3
        self.assertEqual(c.ns.CurrentGuideTip().kind, 'flight')
        metadata.faction = 'Horde'; node.faction = 'Alliance'
        c.lua.globals().clock = 5
        self.assertIsNone(c.ns.CurrentGuideTip())

    def test_hearth_option_and_missing_scale_disable_only_optional_advice(self):
        c = tip_client()
        c.ns.db.config.hearthstoneTips = False
        self.assertIsNone(c.ns.CurrentGuideTip())
        c.ns.db.config.hearthstoneTips = True
        c.lua.execute('C_Map.GetMapWorldSize=function() return secret,secret end; clock=3')
        self.assertIsNone(c.ns.CurrentGuideTip())
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 900)

    def test_hearth_requires_multiple_returns_after_work_away_from_the_hub(self):
        c = tip_client()
        value = c.ns.CurrentGuideTip()
        self.assertEqual(value.kind, 'hearth')
        self.assertIn('2 quest turn-ins', value.detail)
        # Two nearby errands with no circuit away are not a hearth suggestion.
        c.ns.selectedRoute.stops[1].x = .25; c.lua.globals().clock = 3
        self.assertIsNone(c.ns.CurrentGuideTip())
        c.ns.selectedRoute.stops[1].x = .9
        c.ns.selectedRoute.stops[3].id = 900; c.lua.globals().clock = 5
        self.assertIsNone(c.ns.CurrentGuideTip())

    def test_bound_home_and_actual_binding_hide_redundant_hearth_tips(self):
        c = tip_client()
        c.lua.execute('function GetBindLocation() return "Test hub" end')
        self.assertIsNone(c.ns.CurrentGuideTip())
        c.lua.execute('function GetBindLocation() return secret end; clock=3; function UnitGUID() return "Creature-0-1-2-3-500-ABC" end')
        self.assertIsNotNone(c.ns.CurrentGuideTip())
        c.ns.handlers.CONFIRM_BINDER()
        self.assertIsNone(c.ns.db.guideServices[c.ns.self].boundInnID)
        c.ns.handlers.HEARTHSTONE_BOUND()
        self.assertEqual(c.ns.db.guideServices[c.ns.self].boundInnID, 'INN_500')
        self.assertIsNone(c.ns.CurrentGuideTip())

    def test_new_inns_can_be_observed_without_requiring_a_zone_specific_rule(self):
        c = tip_client(inn=False)
        c.lua.execute('function UnitGUID() return "Creature-0-1-2-3-700-ABC" end; function GetSubZoneText() return "New hub" end')
        c.ns.handlers.CONFIRM_BINDER()
        inn = c.ns.db.guideServices[c.ns.self].inns['observed:501:700']
        self.assertEqual(inn.name, 'New hub')
        self.assertEqual(c.ns.CurrentGuideTip().kind, 'hearth')

    def test_dismissal_is_saved_without_skipping_a_quest_or_changing_the_plan(self):
        c = tip_client(inn=False, flight=True)
        c.ns.db.config.travelNetwork = False
        route, guide = c.ns.selectedRoute, c.ns.routeSelection
        before = [(s.id, s.kind, s.x, s.y) for s in route.stops.values()]
        c.ns.UpdateNavigation()
        self.assertTrue(c.ns.navigation.tip.IsShown(c.ns.navigation.tip))
        self.assertEqual(c.ns.navigation.state.stop.kind, 'q')
        c.ns.navigation.tip.close.OnClick()
        self.assertFalse(c.ns.navigation.tip.IsShown(c.ns.navigation.tip))
        self.assertFalse(c.ns.GuideQuestSkipped(900))
        self.assertEqual(before, [(s.id, s.kind, s.x, s.y) for s in route.stops.values()])
        self.assertEqual(c.ns.routeSelection.key, guide.key)
        c.ns.InitializeGuideTips()
        self.assertIsNone(c.ns.CurrentGuideTip())

    def test_options_and_busy_travel_combat_preview_states_hide_advice(self):
        c = tip_client(inn=False, flight=True)
        self.assertIsNotNone(c.ns.CurrentGuideTip())
        c.ns.db.config.nearbyFlights = False
        self.assertIsNone(c.ns.CurrentGuideTip())
        c.ns.db.config.nearbyFlights = True
        for key, value in (('navigationPreview', {}), ('routePaused', 'Waiting'),
                           ('guideScanning', {}), ('routePlanning', {})):
            c.ns[key] = c.lua.table_from(value) if isinstance(value, dict) else value
            self.assertIsNone(c.ns.CurrentGuideTip())
            c.ns[key] = None
        c.lua.execute('combat=true')
        self.assertIsNone(c.ns.CurrentGuideTip())
        c.lua.execute('combat=false; function UnitOnTaxi() return true end')
        self.assertIsNone(c.ns.CurrentGuideTip())
        c.lua.execute('function UnitOnTaxi() return false end; function UnitIsGhost() return true end')
        self.assertIsNone(c.ns.CurrentGuideTip())
        c.lua.execute('function UnitIsGhost() return false end')
        c.ns.routeSelection.mode = 'travel'
        self.assertIsNone(c.ns.CurrentGuideTip())
        c.ns.routeSelection.mode = 'zone'
        self.assertIsNotNone(c.ns.CurrentGuideTip())

    def test_tip_calculation_is_cached_between_position_samples(self):
        c = tip_client()
        c.lua.execute('distanceCalls=0; oldDistance=...', c.ns.TravelPointDistance)
        c.ns.TravelPointDistance = c.lua.eval('function(...) distanceCalls=distanceCalls+1; return oldDistance(...) end')
        c.ns.CurrentGuideTip()
        count = c.lua.globals().distanceCalls
        for _ in range(10):
            c.ns.CurrentGuideTip()
        self.assertEqual(c.lua.globals().distanceCalls, count)
        c.lua.globals().clock = 3; c.ns.CurrentGuideTip()
        self.assertGreater(c.lua.globals().distanceCalls, count)

    def test_shipped_inns_cover_both_continents_and_zephras_with_provenance(self):
        c = Client()
        inns = list(c.ns.guideServiceData.inns.values())
        metadata = json.loads((ROOT / 'WowTogether/GuideServiceData.json').read_text())
        self.assertEqual(len(inns), metadata['inns'])
        self.assertEqual(len(inns), 49)
        self.assertTrue({1411, 1412, 1420, 1429, 1413, 1440, 2521}.issubset({i.mapID for i in inns}))
        self.assertEqual({i.faction for i in inns}, {'Horde', 'Alliance', 'Both'})
        for inn in inns:
            self.assertTrue(c.ns.ValidTravelPoint(inn))
        # Gadgetzan's neutral town does not prove that its Alliance taxi is
        # usable by Horde. Native flight-owner flags must settle this.
        self.assertIsNone(c.ns.guideServiceData.taxis[39].faction)
        self.assertEqual(c.ns.guideServiceData.taxis[25].faction, 'Horde')


if __name__ == '__main__':
    unittest.main()
