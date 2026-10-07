"""Immediate skip geometry, consistent leveling bands and a personal city guide."""
import unittest

from test_addon import Client
from test_routes import catalogue, map_canvas, guide
from test_061 import world_quest, run_plan
from test_063 import guide_client, zone, order, primitive
from test_056 import current_client
from test_068 import maps


def leveling_client():
    c = guide_client(2)
    c.ns.profile.level = 23
    catalogue(c, {855: world_quest('Centaur Bracers', level=14),
                  901: world_quest('Current work', level=23, minLevel=20)})
    return c


def travel_client():
    c = guide_client(2)
    maps(c)
    c.lua.execute('''
    C_Map.GetWorldPosFromMapPos=function(map,p)
        local x,y=p:GetXY(); return 1,CreateVector2D(x*1000,y*1000)
    end
    ''')
    c.ns.travelData = c.lua.table_from({'nodes': {
        'START_GATE': {'mapID': 501, 'x': .9, 'y': .37, 'name': 'East gate'},
        'BACK_START': {'mapID': 501, 'x': .3, 'y': .37, 'name': 'Back crossing'},
        'ENTRANCE_C1454_517_858': {'mapID': 1454, 'x': .517, 'y': .858, 'name': 'Orgrimmar gate'},
        'ENTRANCE_C1454_115_669': {'mapID': 1454, 'x': .115, 'y': .6686, 'name': 'Back gate'}},
        'edges': [
            {'from': 'START_GATE', 'to': 'ENTRANCE_C1454_517_858', 'seconds': 0, 'method': 'walk'},
            {'from': 'BACK_START', 'to': 'ENTRANCE_C1454_115_669', 'seconds': 0, 'method': 'walk'}],
        'factors': {}}, recursive=True)
    return c


class LevelBandTests(unittest.TestCase):
    def test_real_bracers_data_has_no_known_worthwhile_followup_at_twenty_three(self):
        c = Client(quests=(), use_catalogue=True)
        c.guide_environment(level=23)
        c.lua.globals().grouped = False
        c.unit_names({'player': ['Alice', 'TestRealm']})
        self.assertEqual(c.ns.CatalogueQuest(855).level, 14)
        value, reason = c.ns.LevelingValue(855)
        self.assertFalse(value)
        self.assertIn('20–26', reason)
        c.ns.ShowQuestDetails(855)
        self.assertIn('20–26', c.ns.questDetails.body.text)
        self.assertIn('actual reward varies', c.ns.questDetails.body.text)

    def test_fixed_adaptive_and_current_routes_all_filter_accepted_low_work(self):
        c = leveling_client()
        c.ns.active[855], c.ns.active[901] = 'Centaur Bracers', 'Current work'
        g = c.ns.ZoneGuideForMap(501, True)  # Retained full-zone scope spans both brackets.
        included = c.ns.MergeCurrentQuests(g)
        before = order(g) if g.fixedPlan else None
        for route in (c.ns.BuildFixedGuideRoute(g, False),
                      c.ns.BuildFixedGuideRoute(included, False),
                      c.ns.BuildLevelingRoute(included, False, False),
                      c.ns.BuildCurrentQuestRoute(included, False)):
            self.assertFalse(any(s.id == 855 for s in route.stops.values()))
            self.assertFalse(any(s.id == 855 for s in (route.previewStops or c.lua.table()).values()))
        for choice in c.ns.CurrentQuestChoices().values():
            self.assertNotIn(855, {r.id for r in choice.records.values()})
        self.assertFalse(c.ns.GuideQuestSkipped(855))
        self.assertFalse(c.ns.Completed(855))
        self.assertEqual(c.ns.active[855], 'Centaur Bracers')
        if before: self.assertEqual(order(g), before)

    def test_unaccepted_low_pickup_is_filtered_in_every_leveling_route_mode(self):
        c = leveling_client(); g = c.ns.ZoneGuideForMap(501, True)
        retained = guide(c, (855, 901), key='saved-normal-guide')
        retained.mapID = 501
        circuit = guide(c, (855, 901), key='saved-circuit')
        circuit.mode, circuit.mapID = 'circuit', 501
        routes = [c.ns.BuildFixedGuideRoute(g, False), c.ns.BuildLevelingRoute(g, False, False),
                  c.ns.BuildGuideRoute(retained, False), c.ns.BuildCircuitRoute(circuit, False)]
        for route in routes:
            self.assertNotIn(855, {s.id for s in route.stops.values()})
            self.assertIsNone(c.ns.active[855])
        retained.personal = True
        self.assertNotIn(855, {s.id for s in c.ns.BuildGuideRoute(retained, False).stops.values()})
        self.assertFalse(any(r.id == 855 for g in c.ns.GuideChoices(True).values() for r in g.records.values()))

    def test_ready_old_handins_remain_without_old_objective_steps(self):
        c = leveling_client()
        c.ns.active[855], c.ns.readyToTurnIn[855] = 'Centaur Bracers', True
        g = c.ns.MergeCurrentQuests(c.ns.ZoneGuideForMap(501, True))
        for route in (c.ns.BuildFixedGuideRoute(g, False),
                      c.ns.BuildLevelingRoute(g, False, False),
                      c.ns.BuildCurrentQuestRoute(g, False)):
            stops = route.previewStops or route.stops
            old = [s.kind for s in stops.values() if s.id == 855]
            self.assertEqual(old, ['t'])

    def test_known_useful_chain_is_kept_with_a_reason_but_unrelated_old_work_is_not(self):
        c = leveling_client()
        c.ns.catalogue.quests[901].previousQuest = 855
        value, reason = c.ns.LevelingValue(855)
        self.assertTrue(value)
        self.assertIn('Unlocks Current work', reason)
        g = zone(c)
        self.assertIn(855, {s.id for s in c.ns.BuildFixedGuideRoute(g, False).stops.values()})
        self.assertFalse(c.ns.Completed(855))

    def test_band_is_close_at_high_levels_and_uses_lowest_synced_level(self):
        c = leveling_client(); c.ns.profile.level = 60
        self.assertEqual(c.ns.PreferredQuestLevels(), (57, 63))
        for level, expected in ((56, False), (57, True), (60, True), (63, True), (64, False)):
            c.ns.catalogue.quests[901].level = level
            result = c.ns.LevelingValue(901)
            self.assertEqual(result[0] if isinstance(result, tuple) else result, expected)
        c.ns.profile.level = 23
        c.lua.globals().grouped = True
        c.unit_names({'player': ['Alice', 'TestRealm'], 'party1': ['Bob', 'TestRealm']})
        c.ns.members['Bob-TestRealm'] = c.lua.table()
        peer = c.ns.members['Bob-TestRealm']
        peer.active = c.lua.table()
        peer.profile = c.lua.table_from({'level': 14, 'faction': 'Horde', 'mapID': 501})
        self.assertEqual(c.ns.PreferredQuestLevels(), (11, 17))
        self.assertTrue(c.ns.LevelingValue(855))
        peer.syncPending = True
        self.assertEqual(c.ns.PreferredQuestLevels(), (20, 26))


class ImmediateSkipTests(unittest.TestCase):
    def test_skip_quest_redraws_hidden_resizing_dashboard_and_clears_travel_target(self):
        c = guide_client(3); g = zone(c)
        c.ns.ShowGuideOnMap(g); run_plan(c)
        before = order(g); skipped = c.ns.selectedRoute.stops[1].id
        c.ns.window.Hide(c.ns.window); c.ns.ui.resizing = True
        c.ns.travelPath = c.lua.table_from({'old': True})
        c.ns.navigation.skipQuest.OnClick()
        self.assertNotIn(skipped, {s.id for s in c.ns.selectedRoute.stops.values()})
        self.assertNotEqual(c.ns.navigation.state.stop.id, skipped)
        shown = [p for p in c.ns.routeProvider.pins.values() if p.IsShown(p)]
        self.assertTrue(shown)
        self.assertFalse(any(s.id == skipped for p in shown for s in p.group.stops.values()))
        self.assertFalse(c.ns.Completed(skipped)); self.assertEqual(order(g), before)
        self.assertTrue(c.ns.ui.resizeDirty)

    def test_skip_step_in_combat_updates_owned_geometry_without_waiting_for_regen(self):
        c = guide_client(3); c.ns.ShowGuideOnMap(zone(c)); run_plan(c)
        c.ns.ui.resizing = True; c.lua.globals().combat = True
        old = c.ns.selectedRoute.stops[1]
        before = (old.id, c.ns.GuideStepKey(old))
        c.ns.SkipGuide('step')
        after = c.ns.selectedRoute.stops[1]
        self.assertNotEqual((after.id, c.ns.GuideStepKey(after)), before)
        shown = [p for p in c.ns.routeProvider.pins.values() if p.IsShown(p)]
        self.assertFalse(any((s.id, c.ns.GuideStepKey(s)) == before for p in shown for s in p.group.stops.values()))

    def test_current_route_skip_is_immediate_and_does_not_reintroduce_the_skipped_quest(self):
        c = current_client({900: world_quest('First'), 901: world_quest('Second')})
        map_canvas(c); c.ns.ShowGuideOnMap(c.ns.CurrentQuestChoices()[1])
        skipped = c.ns.selectedRoute.stops[1].id
        c.ns.ui.resizing = True; c.ns.SkipGuide('quest')
        self.assertNotIn(skipped, {s.id for s in c.ns.selectedRoute.stops.values()})
        self.assertNotEqual(c.ns.navigation.state.stop.id, skipped)


class CityTravelGuideTests(unittest.TestCase):
    def test_published_network_connects_nearby_zones_and_the_tirisfal_zeppelin(self):
        c = guide_client(2); maps(c)
        c.lua.execute('''
        C_Map.GetWorldPosFromMapPos=function(map,p)
            local x,y=p:GetXY(); return 1,CreateVector2D(x*1000,y*1000)
        end
        ''')
        g = c.ns.OrgrimmarTravelGuide()
        for map_id in (1411, 1413, 1420):
            c.lua.globals().playerMap = map_id
            route = c.ns.BuildTravelGuideRoute(g)
            self.assertEqual(len(route.stops), 1)
            path = c.ns.FindTravelPath(c.ns.PlayerPoint(map_id), route.stops[1], False)
            self.assertIsNotNone(path)
            if map_id == 1420:
                self.assertTrue(any(leg.method == 'zeppelin' for leg in path.legs.values()))

    def test_browser_search_and_each_level_bracket_offer_a_personal_travel_guide(self):
        c = travel_client()
        for level, bracket in ((1, '1-10'), (23, '21-30'), (60, '51+')):
            c.ns.profile.level, c.ns.guideLevel = level, bracket
            travel = [g for g in c.ns.GuideBrowserChoices().values() if g.mode == 'travel']
            self.assertEqual(len(travel), 1)
            self.assertEqual((travel[0].minLevel, travel[0].maxLevel), (1, 60))
            self.assertTrue(travel[0].personal)
        c.ns.guideSearch = 'orgrimmar'
        self.assertEqual([g.key for g in c.ns.GuideBrowserChoices().values()], ['travel:orgrimmar'])
        c.ns.SetFilter('guides')
        card = c.ns.ui.cards[1]
        self.assertEqual(card.category.text, 'TRAVEL GUIDE')
        self.assertFalse(card.count.IsShown(card.count))
        self.assertFalse(card.detailsButton.IsShown(card.detailsButton))
        card.OnClick()
        self.assertEqual(c.ns.guideQuestList.guide.key, 'travel:orgrimmar')
        self.assertIsNone(c.ns.routeSelection)
        for faction in ('Alliance', 'Unknown'):
            c.ns.profile.faction = faction
            self.assertIsNone(c.ns.OrgrimmarTravelGuide())

    def test_start_chooses_quickest_known_gate_and_sends_no_party_invite(self):
        c = travel_client(); g = c.ns.OrgrimmarTravelGuide()
        self.assertTrue(c.ns.RequestStartRoute(g))
        self.assertEqual(c.ns.routeSelection.key, 'travel:orgrimmar')
        self.assertAlmostEqual(c.ns.selectedRoute.stops[1].x, .115)
        self.assertEqual(c.ns.navigation.state.stop.kind, 'travel')
        self.assertFalse(c.ns.navigation.skipQuest.enabled)
        self.assertIsNone(c.ns.startGuidePrompt)
        self.assertEqual(c.ns.TransportState().queued, 0)
        c.ns.SkipGuide('quest'); self.assertFalse(c.ns.GuideQuestSkipped(0))
        c.ns.ScanGuideProgress()
        self.assertEqual(c.ns.routeSelection.key, g.key)

    def test_arrival_completes_by_city_entry_and_can_start_while_already_inside(self):
        c = travel_client(); c.ns.RequestStartRoute(c.ns.OrgrimmarTravelGuide())
        c.lua.execute('playerMap=1454'); c.ns.UpdateNavigation()
        self.assertTrue(c.ns.selectedRoute.complete)
        self.assertEqual(len(c.ns.selectedRoute.stops), 0)
        self.assertEqual(c.ns.navigation.state.status, 'Arrived in Orgrimmar.')
        self.assertTrue(c.ns.navigation.IsShown(c.ns.navigation))
        self.assertTrue(c.ns.RequestStartRoute(c.ns.OrgrimmarTravelGuide()))
        self.assertTrue(c.ns.selectedRoute.complete)

    def test_reload_restores_travel_guide_without_fake_quests_or_credit(self):
        c = travel_client(); c.ns.RequestStartRoute(c.ns.OrgrimmarTravelGuide())
        saved = primitive(c.ns.db)
        restored = Client(quests=(), saved_variables=saved)
        restored.guide_environment(level=23)
        restored.ns.RestoreSavedGuide()
        self.assertEqual(restored.ns.routeSelection.key, 'travel:orgrimmar')
        self.assertEqual(len(restored.ns.routeSelection.records), 0)
        self.assertFalse(restored.ns.Completed(0))

    def test_disconnected_zone_retains_guide_with_an_explanation_without_invented_lines(self):
        c = travel_client(); c.ns.travelData.edges = c.lua.table()
        self.assertTrue(c.ns.RequestStartRoute(c.ns.OrgrimmarTravelGuide()))
        self.assertEqual(len(c.ns.selectedRoute.stops), 0)
        self.assertIn('No known travel connection', c.ns.navigation.state.status)
        self.assertEqual(c.ns.routeStats.lines, 0)


if __name__ == '__main__': unittest.main()
