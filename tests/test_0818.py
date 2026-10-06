"""Romits' flight/map/item reports; synthetic APIs cannot certify beta behavior."""
import unittest

from test_addon import Client
from test_060 import flight_client
from test_063 import guide_client, zone, order
from test_068 import maps
from test_070 import point, network_client
from test_085 import step
from test_089 import identity
from test_routes import guide, map_canvas


class FlightReportTests(unittest.TestCase):
    def test_remote_continent_node_joins_its_zone_and_known_flight_beats_walking(self):
        c = flight_client(); maps(c)
        c.ns.travelData = c.lua.table_from({'nodes': {'TAXI_22': {
            'name': 'Crossroads', 'mapID': 502, 'x': .4, 'y': .37}},
            'edges': [], 'factors': {}}, recursive=True)
        stop = c.ns.selectedRoute.stops[1]
        stop.mapID, stop.x, stop.y = 502, .8, .37
        c.lua.execute('''
        function GetTaxiMapID() return 10 end
        taxiNodes[1].position=CreateVector2D(.07,.37)
        taxiNodes[2].position=CreateVector2D(1.4/3,.37)
        C_TaxiMap.GetAllTaxiNodes=function(map) assert(map==10);return taxiNodes end
        ''')
        c.ns.ReadFlightMap()
        state = c.ns.db.flights[c.ns.self]
        self.assertEqual(state.nodes[22].point.mapID, 502)
        self.assertAlmostEqual(state.nodes[22].point.x, .4)
        path = c.ns.FindTravelPath(point(c), stop, True)
        self.assertTrue(any(leg.method == 'taxi' for leg in path.legs.values()))
        self.assertLess(path.seconds, c.ns.TravelPointDistance(point(c), stop) / 7)
        # Unlock flags alone must not invent a reachable flight connection.
        state.edges['11:22'] = None
        self.assertIsNone(c.ns.FindTravelPath(point(c), stop, True))

    def test_saved_continent_geography_is_repaired_without_inventing_unlocks(self):
        c = flight_client(); maps(c)
        c.ns.travelData = c.lua.table_from({'nodes': {'TAXI_22': {
            'name': 'Crossroads', 'mapID': 502, 'x': .4, 'y': .37}}, 'edges': [], 'factors': {}}, recursive=True)
        state = c.ns.db.flights[c.ns.self]
        state.nodes[22] = c.lua.table_from({'name': 'Crossroads', 'known': False,
            'point': {'mapID': 10, 'x': 1.4 / 3, 'y': .37}}, recursive=True)
        c.ns.InitializeTravel()
        self.assertEqual(state.nodes[22].point.mapID, 502)
        self.assertFalse(state.nodes[22].known)
        self.assertEqual(len(state.edges), 0)

    def test_measured_ride_countdown_is_shared_and_not_whole_journey_time(self):
        c = flight_client(); c.ns.ReadFlightMap()
        c.ns.db.flights[c.ns.self].timings['11:22'] = c.lua.table_from({'mean': 90, 'samples': 1})
        c.ns.ResetTravelPath(); c.ns.SetOption('standaloneArrow', True)
        c.ns.NoteFlightSelection(54)
        c.lua.execute('flying=true; clock=100'); c.ns.handlers.PLAYER_CONTROL_LOST()
        c.lua.execute('clock=140'); c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.state.flight.remaining, 50)
        self.assertIn('0m 50s', c.ns.standaloneNavigation.timer.text)
        self.assertEqual(c.ns.navigation.distance.text, c.ns.standaloneNavigation.timer.text)
        self.assertNotIn('Est.', c.ns.standaloneNavigation.timer.text)
        c.lua.execute('flying=false; clock=190'); c.ns.handlers.PLAYER_CONTROL_GAINED()
        self.assertEqual(c.ns.db.flights[c.ns.self].timings['11:22'].mean, 90)
        self.assertNotIn('left', c.ns.standaloneNavigation.timer.text)

    def test_untimed_or_overdue_flight_never_displays_a_fake_exact_countdown(self):
        c = flight_client(); c.ns.ReadFlightMap(); c.ns.SetOption('standaloneArrow', True)
        c.ns.NoteFlightSelection(54)
        c.lua.execute('flying=true'); c.ns.UpdateNavigation()
        self.assertIn('Est. flight', c.ns.standaloneNavigation.timer.text)
        c.lua.execute('clock=5000'); c.ns.UpdateNavigation()
        self.assertIn('flying', c.ns.standaloneNavigation.timer.text)
        self.assertNotIn('left', c.ns.standaloneNavigation.timer.text)

    def test_flight_summary_distinguishes_ride_from_journey(self):
        c = flight_client(); c.ns.ReadFlightMap()
        stop = c.ns.TravelDestination(c.ns.selectedRoute.stops[1])
        summary = c.ns.RouteContext(stop, 501)
        self.assertIn('Estimated flight: ' + c.ns.FormatTravelDuration(stop.flightPlan.flightSeconds), summary)
        self.assertIn('journey ~' + c.ns.FormatTravelDuration(stop.flightPlan.seconds), summary)
        self.assertGreater(stop.flightPlan.seconds, stop.flightPlan.flightSeconds)

    def test_flying_retains_all_quest_markers_and_full_preview_without_ground_lines(self):
        c = flight_client(); c.ns.ReadFlightMap()
        original = c.ns.selectedRoute
        original.stops[2] = c.lua.table_from({'id': 901, 'kind': 'q', 'mapID': 501,
            'x': .6, 'y': .6, 'title': 'Another objective', 'label': 'Another objective'})
        c.ns.SetOption('fullRoute', True)
        c.lua.execute('flying=true'); c.ns.handlers.PLAYER_CONTROL_LOST()
        display = c.ns.RouteForDisplay()
        self.assertTrue(display.flying)
        self.assertEqual([s.id for s in display.stops.values()], [900, 901])
        self.assertEqual(c.ns.routeStats.lines, 0)
        self.assertEqual({p.stop.id for p in c.ns.routeProvider.pins.values() if p.IsShown(p)}, {900, 901})
        c.lua.execute('flying=false'); c.ns.handlers.PLAYER_CONTROL_GAINED()
        self.assertFalse(c.ns.RouteForDisplay().flying)
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 900)

    def test_transport_names_the_actual_boarding_point_and_coordinates(self):
        c = network_client([{'from': 'A', 'to': 'B', 'seconds': 250, 'method': 'zeppelin', 'faction': 'Horde'}])
        stop = c.lua.table_from({'id': 900, 'kind': 'q', 'title': 'Remote work', 'mapID': 502, 'x': .2, 'y': .37})
        c.ns.ActivateRoute(guide(c, (900,)), c.lua.table_from({'mapID': 502, 'stops': [stop]}, recursive=True))
        c.lua.execute('playerX=.9'); c.ns.ResetTravelPath(); c.ns.UpdateNavigation()
        state = c.ns.navigation.state
        self.assertEqual(state.stop.travelLeg.method, 'zeppelin')
        self.assertAlmostEqual(state.stop.x, .9)
        self.assertIn('Board at East gate', c.ns.navigation.context.text)
        self.assertIn('90.0, 37.0', c.ns.navigation.context.text)
        self.assertIn('waiting time varies', c.ns.navigation.context.text.lower())


class ArrowAndSettingsTests(unittest.TestCase):
    def test_class_default_is_on_but_explicit_opt_out_survives_initialization(self):
        c = Client()
        self.assertTrue(c.ns.Option('classQuests'))
        c.ns.SetOption('classQuests', False); c.ns.InitializeConfig()
        self.assertFalse(c.ns.Option('classQuests'))
        c.ns.db.config.classQuests = None; c.ns.InitializeConfig()
        self.assertTrue(c.ns.Option('classQuests'))

    def test_default_includes_the_actual_players_class_and_keeps_other_classes_out(self):
        c = Client(quests=(), use_catalogue=True); c.guide_environment(level=3); identity(c)
        self.assertTrue(c.ns.ClassQuestEnabled(3089))  # Orc Shaman's parchment.
        other = next(id for id, q in c.ns.catalogue.quests.items() if q.classMask == 128)
        profile = c.lua.table_from(dict(c.ns.profile.items()))
        side = c.ns.CatalogueQuest(other).side
        if side in ('Horde', 'Alliance'):
            profile.faction = side
        allowed, reason = c.ns.CatalogueIdentityAllowed(other, profile)
        self.assertFalse(allowed)
        self.assertIn('class requirement', reason)

    def test_separate_arrow_hides_duplicate_geometry_and_keeps_guide_controls(self):
        c = flight_client(); c.lua.execute('function GetPlayerFacing() return 0 end'); c.ns.UpdateNavigation()
        c.ns.SetOption('standaloneArrow', True)
        self.assertTrue(c.ns.standaloneNavigation.IsShown(c.ns.standaloneNavigation))
        self.assertFalse(c.ns.navigation.icon.IsShown(c.ns.navigation.icon))
        self.assertTrue(c.ns.navigation.IsShown(c.ns.navigation))
        self.assertTrue(c.ns.navigation.scan.enabled)
        self.assertTrue(all(not line.IsShown(line) for line in c.ns.navigation.icon.lines.values()))
        c.ns.SetOption('standaloneArrow', False)
        self.assertTrue(c.ns.navigation.icon.IsShown(c.ns.navigation.icon))
        self.assertTrue(any(line.IsShown(line) for line in c.ns.navigation.icon.lines.values()))

    def test_walk_eta_uses_mount_speed_and_reconsiders_cached_travel_costs(self):
        c = flight_client(); c.ns.SetOption('standaloneArrow', True)
        c.ns.UpdateNavigation(); before = c.ns.navigation.state.walkSeconds
        c.lua.execute('function GetUnitSpeed() return 14,14 end'); c.ns.UpdateNavigation()
        self.assertAlmostEqual(c.ns.navigation.state.walkSeconds, before / 2)
        self.assertIn('travel', c.ns.standaloneNavigation.timer.text)
        self.assertAlmostEqual(c.ns.travelPath.seconds, before * 1.25 / 2)
        c.lua.execute('function GetUnitSpeed() return secret,secret end'); c.ns.UpdateNavigation()
        self.assertAlmostEqual(c.ns.navigation.state.walkSeconds, before)


class CollectionProgressTests(unittest.TestCase):
    def test_shipped_ishamuhale_collection_advances_to_fang_on_bag_event(self):
        c = Client(quests=(882,), use_catalogue=True); c.guide_environment(level=19); map_canvas(c)
        c.lua.execute('grouped=false; bags={}; C_Item={GetItemCount=function(id) return bags[id] or 0 end}')
        c.unit_names({'player': ['Alice', 'TestRealm']})
        g = guide(c, (882,)); g.fixedRoute = True
        c.ns.GenerateFixedGuide(g, False)
        compiled = order(g)
        c.ns.ActivateRoute(g, c.ns.BuildFixedGuideRoute(g, True))
        self.assertEqual(c.ns.selectedRoute.stops[1].itemID, 10338)
        c.lua.execute('bags[10338]=1'); c.ns.handlers.BAG_UPDATE_DELAYED(); c.drain()
        self.assertEqual(c.ns.selectedRoute.stops[1].itemID, 5101)
        self.assertFalse(c.ns.Completed(882))
        self.assertEqual(order(c.ns.routeSelection), compiled)
        self.assertFalse(c.ns.GuideQuestSkipped(882))

    def test_adaptive_stages_also_advance_a_collected_item_without_claiming_turn_in(self):
        c = Client(quests=(882,), use_catalogue=True); c.guide_environment(level=19)
        c.lua.execute('grouped=false; C_Item={GetItemCount=function(id) return id==10338 and 1 or 0 end}')
        c.unit_names({'player': ['Alice', 'TestRealm']})
        stages = c.ns.RouteStages(c.ns.CatalogueRecord(882), c.ns.self)
        self.assertEqual(stages[1].itemID, 5101)
        self.assertEqual(stages[1].kind, 'q')
        self.assertFalse(c.ns.GuideStepNeeded(c.ns.PublishedGuideStop(
            c.ns.CatalogueRecord(882), c.ns.CatalogueQuest(882).objectives[1], 'q')))
        self.assertFalse(c.ns.Completed(882))

    def test_collection_checks_count_without_completing_use_kill_or_peer_steps(self):
        c = guide_client(2)
        c.ns.active[900] = 'Supplies'
        c.lua.execute('C_Item={GetItemCount=function() return 8 end}')
        stop = step(c, itemID=123)
        facts = c.ns.GuideStepFacts(stop)
        self.assertTrue(facts.finished); self.assertEqual(facts.progress, '8/8')
        for action in ('kill', 'use', 'heal', 'interact'):
            stop.action = action
            self.assertIsNone(c.ns.GuideStepFacts(stop).inventory)
        stop.action = 'loot'; stop.memberKey = 'Friend'
        self.assertIsNone(c.ns.GuideStepFacts(stop).inventory)
        stop.memberKey = c.ns.self
        c.ns.active[900] = None
        self.assertIsNone(c.ns.GuideStepFacts(stop).inventory)

    def test_restricted_count_and_missing_quantity_cannot_grant_progress(self):
        c = guide_client(2); c.ns.active[900] = 'Supplies'
        c.lua.execute('C_Item={GetItemCount=function() return secret end}')
        stop = step(c, itemID=123)
        self.assertIsNone(c.ns.GuideStepFacts(stop).inventory)
        c.lua.execute('C_Item.GetItemCount=function() return 99 end')
        stop.quantityUnknown = True
        self.assertIsNone(c.ns.GuideStepFacts(stop).finished)

    def test_native_required_count_overrides_old_quantity_in_bag_check(self):
        c = guide_client(2); c.ns.active[900] = 'Supplies'
        c.lua.execute('C_Item={GetItemCount=function() return 8 end}')
        c.ns.localProgress[900] = c.lua.table_from({'objectives': [
            {'text': 'Boar Flank: 3/12', 'kind': 'item', 'have': 3, 'need': 12, 'finished': False}]}, recursive=True)
        facts = c.ns.GuideStepFacts(step(c, itemID=123))
        self.assertEqual(facts.progress, '8/12')
        self.assertFalse(facts.finished)


if __name__ == '__main__':
    unittest.main()
