"""Catalogue-wide guide, cooperative planning and greeting-offer regressions.

Synthetic API fixtures exercise Lua 5.1 logic, not live Forever API compatibility.
"""
import unittest

from test_addon import Client
from test_routes import catalogue, guide, map_canvas, quest
from test_050 import solo as base_solo, nearby, world_positions
import test_060 as previous
from test_importers import detail
from import_wowhead import detail_facts


def solo():
    # These regressions retain the adaptive planner; fixed-guide behavior has
    # separate tests, and is the default for player-selected zone guides.
    c = base_solo()
    c.ns.db.config.fixedZoneGuides = False
    return c


def world_quest(title='World quest', zone='Test Coast', map_id=501, level=12, **extra):
    result = quest(title, map_id=map_id, level=level, zone=zone,
                   categoryPath='kalimdor/' + zone.lower().replace(' ', '-'))
    result.update(extra)
    return result


def selected(c, ids=(900, 901)):
    result = guide(c, ids, key='level-zone:kalimdor/test-coast')
    result.fullGuide, result.mode, result.zone, result.mapID = True, 'zone', 'Test Coast', 501
    return result


def run_plan(c, maximum=200):
    count = 0
    while c.ns.routePlanning is not None:
        if not len(c.lua.globals().timers):
            raise AssertionError('planning lost its scheduled continuation')
        callback = c.lua.eval('table.remove')(c.lua.globals().timers, 1)
        callback()
        count += 1
        if count > maximum:
            raise AssertionError('planner failed to finish')
    return count


class GuideBrowserTests(unittest.TestCase):
    def test_all_level_bracket_zones_are_browsable_but_local_zone_ranks_first(self):
        c = solo(); c.ns.profile.level = 25
        data = {}
        for index, (zone, map_id) in enumerate([('Test Coast', 501), ('Remote Zone', 9001), ('Another Zone', 9002)]):
            for step in range(2):
                data[900 + index * 10 + step] = world_quest(zone + str(step), zone, map_id, 25)
        data[999] = world_quest('Single unrelated quest', 'Single Zone', 9003, 25)
        catalogue(c, data)
        choices = c.ns.LevelingGuideChoices()
        self.assertEqual({g.zone for g in choices.values()}, {'Test Coast', 'Remote Zone', 'Another Zone'})
        self.assertEqual(choices[1].zone, 'Test Coast')
        self.assertEqual(c.ns.GuideLevelRange(), (21, 30))
        self.assertTrue(all(g.fullGuide and len(g.records) == 2 for g in choices.values()))

    def test_search_and_bracket_dropdowns_debounce_and_hide_on_other_views(self):
        c = solo()
        catalogue(c, {900: world_quest('First'), 901: world_quest('Second'),
                      902: world_quest('High First', 'Remote Zone', 9001, 25),
                      903: world_quest('High Second', 'Remote Zone', 9001, 25)})
        c.ns.SetFilter('guides')
        search = c.ns.ui.guideSearch
        search.SetText(search, 'Remote'); search.OnTextChanged(search)
        self.assertEqual(c.ns.guideSearch, '')
        c.drain()
        self.assertEqual(c.ns.guideSearch, 'Remote')
        self.assertEqual(c.ns.ui.visibleCards, 0)
        c.ns.ui.guideLevel.options['21-30'].OnClick()
        self.assertEqual(c.ns.ui.visibleCards, 0)  # A future filter does not bypass actual character level.
        c.lua.globals().playerLevel = 25; c.ns.ReadProfile(); c.ns.Refresh()
        self.assertEqual(c.ns.ui.visibleCards, 1)
        self.assertEqual(c.ns.ui.cards[1].guide.zone, 'Remote Zone')
        search.SetText(search, 'High'); search.OnTextChanged(search); search.OnEnterPressed(search)
        self.assertEqual(c.ns.guideSearch, 'High')
        c.ns.SetFilter('all')
        self.assertTrue(all(not control.IsShown(control) for control in c.ns.ui.guideControls.values()))

    def test_pagination_does_not_silently_hide_guides_beyond_first_nine(self):
        c = solo()
        data = {}
        for index in range(14):
            for step in range(2):
                data[900 + index * 10 + step] = world_quest(str(index) + str(step), 'Zone ' + str(index), 7000 + index)
        catalogue(c, data); c.ns.SetFilter('guides')
        self.assertEqual(c.ns.ui.visibleCards, 12)
        self.assertIn('15 guides', c.ns.ui.guideCount.text)  # 14 zones plus the personal city journey.
        c.ns.ui.guideNext.OnClick()
        self.assertEqual(c.ns.guidePage, 2)
        self.assertEqual(c.ns.ui.visibleCards, 3)
        self.assertEqual(c.ns.ui.cards[3].guide.key, 'travel:orgrimmar')

    def test_identity_profession_dungeon_repeatable_and_single_quest_filters(self):
        c = solo(); c.ns.profile.classID = 8
        catalogue(c, {900: world_quest('Valid'), 901: world_quest('Valid two'),
                      902: world_quest('Alliance', side='Alliance'),
                      903: world_quest('Mage', categoryPath='classes/mage'),
                      904: world_quest('Cooking', categoryPath='professions/cooking'),
                      905: world_quest('Dungeon', categoryPath='dungeons/test'),
                      906: world_quest('Repeat', repeatable=True),
                      907: world_quest('Far higher', level=30)})
        choices = c.ns.LevelingGuideChoices()
        self.assertEqual(len(choices), 1)
        self.assertEqual({r.id for r in choices[1].records.values()}, {900, 901, 907})
        self.assertNotIn(907, {s.id for s in c.ns.BuildGuideRoute(choices[1], False).stops.values()})

    def test_missing_points_do_not_disable_selection_or_invent_coordinates(self):
        c = solo()
        catalogue(c, {900: world_quest('Unknown one', starts=[], objectives=[], ends=[]),
                      901: world_quest('Unknown two', starts=[], objectives=[], ends=[])})
        c.ns.SetFilter('guides')
        card = c.ns.ui.cards[1]
        self.assertFalse(card.guide.hasPoint)
        self.assertIn('unknown', card.reason.text)
        card.mapButton.OnClick()
        self.assertIn('Loading', c.ns.guideQuestList.summary.text)
        self.assertIsNone(c.ns.routeSelection)
        c.drain()
        self.assertEqual(len(c.ns.guideQuestList.plan), 6)
        # The list is read-only; Start route still permits an unmapped guide.
        card.detailsButton.OnClick()
        self.assertEqual(c.ns.navigation.state.status, 'Loading route…')
        run_plan(c)
        self.assertIsNotNone(c.ns.routeSelection)
        self.assertEqual(len(c.ns.selectedRoute.stops), 0)
        self.assertIn('location', c.ns.navigation.state.status)
        self.assertIsNone(c.lua.globals().waypoint)

    def test_start_unknown_location_guide_is_enabled_and_keeps_all_records(self):
        c = solo()
        catalogue(c, {900: world_quest(starts=[]), 901: world_quest('Other', starts=[])})
        c.ns.SetFilter('guides'); card = c.ns.ui.cards[1]
        card.detailsButton.OnClick(); run_plan(c)
        self.assertIn('started for you', c.ns.partyRouteStatus)
        self.assertEqual(len(c.ns.routeSelection.records), 2)

    def test_known_prerequisite_is_included_but_does_not_unlock_from_skip(self):
        c = solo()
        catalogue(c, {900: world_quest('Earlier useful', level=5),
                      901: world_quest('Followup', previousQuest=900), 902: world_quest('Another')})
        g = c.ns.LevelingGuideChoices()[1]
        self.assertEqual({r.id for r in g.records.values()}, {900, 901, 902})
        c.ns.db.guideSkips[c.ns.self].quests[900] = True
        plan = c.ns.BuildGuideRoute(g, False)
        self.assertNotIn(901, {s.id for s in plan.stops.values()})
        c.lua.globals().finished[900] = True
        g.batchIDs = None  # An explicit rescan chooses a new trip.
        plan = c.ns.BuildGuideRoute(g, False)
        self.assertIn(901, {s.id for s in plan.stops.values()})


class CooperativePlannerTests(unittest.TestCase):
    def client(self, count=6):
        c = solo(); map_canvas(c)
        catalogue(c, {900 + i: world_quest(str(i)) for i in range(count)})
        return c

    def test_loading_yields_then_routes_with_pickup_objective_return_dependencies(self):
        c = self.client()
        g = selected(c, range(900, 906))
        self.assertTrue(c.ns.ShowGuideOnMap(g))
        self.assertEqual(c.ns.navigation.state.status, 'Loading route…')
        self.assertGreater(run_plan(c), 2)
        route = c.ns.selectedRoute
        self.assertTrue(route.optimized)
        self.assertEqual(route.guideQuests, 6)
        self.assertEqual(route.tripQuests, 6)
        self.assertEqual(len(route.stops), 18)
        for id in range(900, 906):
            self.assertEqual([s.kind for s in route.stops.values() if s.id == id], ['a', 'q', 't'])
        self.assertIsNone(c.ns.navigation.notice)
        self.assertGreater(c.ns.routeStats.lines, 0)

    def test_acceptance_retains_trip_and_completion_advances_full_guide(self):
        c = self.client(count=9)
        g = selected(c, range(900, 909))
        c.ns.ShowGuideOnMap(g); run_plan(c)
        first_ids = set(c.ns.routeSelection.batchIDs.values())
        self.assertEqual(len(first_ids), 6)
        c.lua.execute("entries={{questID=900,title='Accepted',isHeader=false}}")
        c.ns.SyncNow(False)
        self.assertEqual(set(c.ns.routeSelection.batchIDs.values()), first_ids)
        self.assertEqual(len(c.ns.routeSelection.records), 9)
        c.lua.globals().entries = c.lua.table()
        for id in first_ids: c.lua.globals().finished[id] = True
        c.ns.SyncNow(False)
        self.assertEqual(set(c.ns.routeSelection.batchIDs.values()), set(range(900, 909)) - first_ids)
        self.assertEqual(len(c.ns.selectedRoute.stops), 9)

    def test_new_progress_while_planning_restarts_before_committing(self):
        c = self.client()
        c.ns.ShowGuideOnMap(selected(c, range(900, 906)))
        c.lua.globals().finished[900] = True
        run_plan(c)
        self.assertNotIn(900, {s.id for s in c.ns.selectedRoute.stops.values()})

    def test_clear_cancels_pending_generation(self):
        c = self.client()
        c.ns.ShowGuideOnMap(selected(c, range(900, 906)))
        c.ns.ClearRoute(); c.drain()
        self.assertIsNone(c.ns.routeSelection)
        self.assertIsNone(c.ns.selectedRoute)
        self.assertIsNone(c.ns.routePlanning)

    def test_completed_guide_start_and_missing_scheduler_fail_explicitly(self):
        c = self.client(count=2)
        c.lua.globals().finished[900], c.lua.globals().finished[901] = True, True
        c.ns.StartPartyRoute(c.ns.LevelingGuideChoices()[1]); run_plan(c)
        self.assertIsNotNone(c.ns.routeSelection)
        self.assertTrue(c.ns.selectedRoute.complete)
        self.assertIn('already completed', c.ns.partyRouteStatus)
        c.lua.globals().finished[900], c.lua.globals().finished[901] = False, False
        c.lua.globals().C_Timer = None
        self.assertFalse(c.ns.ShowGuideOnMap(c.ns.LevelingGuideChoices()[1]))
        self.assertIn('scheduler unavailable', c.ns.guideAction)
        self.assertIsNone(c.ns.routePlanning)

    def test_missing_shared_identity_never_falls_back_to_different_zone(self):
        c = self.client(count=2)
        invite = c.lua.table_from({'sender': 'Bob-TestRealm', 'mode': 'zone', 'target': 900,
            'guideKey': 'level-zone:kalimdor/missing-zone', 'rangeLow': 11, 'rangeHigh': 20,
            'ids': [900, 901], 'mapID': 501}, recursive=True)
        result, reason = c.ns.BuildInvitedGuide(invite)
        self.assertIsNone(result)
        self.assertIn('missing', reason)

    def test_full_guide_invitation_sends_identity_and_validates_after_reassembly(self):
        c = self.client(count=26)
        c.lua.globals().grouped = True
        c.unit_names({'player': ['Alice', 'TestRealm'], 'party1': ['Bob', 'TestRealm']})
        ids = ','.join(str(id) for id in range(900, 926))
        c.receive('1|P|12|2|501|Test Coast')
        c.receive('1|S|1|1|1|')
        c.receive('1|C|2|1|1|')
        c.receive('1|K|2|1|1|' + ids)
        g = c.ns.LevelingGuideChoices()[1]
        c.ns.StartPartyRoute(g); run_plan(c)
        packets = [message for _, message, _ in c.drain() if message.startswith('1|V|')]
        self.assertEqual(len(packets), 3)
        self.assertTrue(all(message.endswith('|level-zone:kalimdor/test-coast|11|20') and len(message) <= 255 for message in packets))
        for message in reversed(packets): c.receive(message)
        self.assertEqual(c.ns.partyRoutePrompt.invite.guideKey, g.key)
        received = c.ns.BuildInvitedGuide(c.ns.partyRoutePrompt.invite)
        self.assertEqual(len(received.records), 26)

    def test_dependency_ready_search_shortens_a_loop_compared_with_greedy_order(self):
        c = self.client(count=4)
        points = [(.3184, .5241), (.48, .5897), (.2906, .3422), (.2759, .3401)]
        for index, (x, y) in enumerate(points):
            c.ns.catalogue.quests[900 + index].objectives[1].x = x
            c.ns.catalogue.quests[900 + index].objectives[1].y = y
        greedy = c.ns.BuildGuideRoute(guide(c, range(900, 904)), True)
        planned = c.ns.BuildGuideRoute(selected(c, range(900, 904)), True)
        def length(route):
            previous, total = c.ns.PlayerPoint(501), 0
            for point in route.stops.values():
                total += c.ns.NormalizedDistance(previous, point)
                previous = point
            return total
        self.assertLess(length(planned), length(greedy) * .9)
        for id in range(900, 904):
            self.assertEqual([s.kind for s in planned.stops.values() if s.id == id], ['a', 'q', 't'])

    def test_negative_npc_offer_removes_bad_pickup_marker_but_retains_guide(self):
        c = self.client(count=2)
        for id in (900, 901):
            c.ns.catalogue.quests[id].starts[1].entityID = 123
        c.lua.execute("function UnitGUID() return 'Creature-0-1-2-3-123-ABC' end")
        c.ns.ShowGuideOnMap(selected(c)); run_plan(c)
        self.assertGreater(len(c.ns.selectedRoute.stops), 0)
        c.ns.RecordNPCOfferAvailability(c.lua.table())
        c.ns.Refresh()
        self.assertIsNotNone(c.ns.routeSelection)
        self.assertEqual(len(c.ns.selectedRoute.stops), 0)
        self.assertEqual(c.ns.routeStats.pins, 0)
        self.assertIn('did not offer', c.ns.navigation.state.status)

    def test_native_waypoint_apis_are_unused_and_manual_pin_is_preserved(self):
        c = self.client(count=2)
        c.lua.execute("waypoint={map=999,x=.5,y=.5}; C_Map.SetUserWaypoint=function() error('unexpected native waypoint mutation') end; C_Map.CanSetUserWaypointOnMap=nil; UiMapPoint=nil")
        c.ns.ShowGuideOnMap(selected(c)); run_plan(c)
        self.assertEqual(c.lua.globals().waypoint.map, 999)
        self.assertGreater(c.ns.routeStats.pins, 0)
        c.ns.active[900] = 'Accepted'; c.ns.ReadRouteLocations(); c.ns.Refresh()
        c.ns.ClearRoute()
        self.assertEqual(c.lua.globals().waypoint.map, 999)

    def test_shared_zone_identity_reconstructs_more_than_twenty_quests(self):
        c = self.client(count=26)
        invite = c.lua.table_from({'sender': 'Bob-TestRealm', 'mode': 'zone', 'target': 900,
                                  'ids': list(range(900, 920)), 'mapID': 501}, recursive=True)
        g = c.ns.BuildInvitedGuide(invite)
        self.assertTrue(g.fullGuide)
        self.assertEqual(len(g.records), 26)
        self.assertEqual(g.key, 'level-zone:kalimdor/test-coast')

    def test_shared_identity_selects_correct_zone_even_with_foreign_prerequisite(self):
        c = self.client(count=2)
        c.ns.catalogue.quests[899] = c.lua.table_from(world_quest('Foreign intro', 'Remote Zone', 502), recursive=True)
        c.ns.catalogue.quests[900].previousQuest = 899
        invite = c.lua.table_from({'sender': 'Bob-TestRealm', 'mode': 'zone', 'target': 899,
            'guideKey': 'level-zone:kalimdor/test-coast', 'rangeLow': 11, 'rangeHigh': 20,
            'ids': [899, 900, 901], 'mapID': 501}, recursive=True)
        g = c.ns.BuildInvitedGuide(invite)
        self.assertEqual(g.key, invite.guideKey)
        self.assertEqual({r.id for r in g.records.values()}, {899, 900, 901})

    def test_full_guide_packet_validation_and_invite_keep_choice(self):
        c = self.client(count=26)
        c.lua.globals().grouped = True
        c.unit_names({'player': ['Alice', 'TestRealm'], 'party1': ['Bob', 'TestRealm']})
        c.receive('1|V|1|1|1|zone|501|900|900,901|level-zone:kalimdor/test-coast|11|20')
        prompt = c.ns.partyRoutePrompt
        self.assertTrue(prompt.IsShown(prompt))
        self.assertEqual(prompt.invite.guideKey, 'level-zone:kalimdor/test-coast')
        prompt.keep.OnClick()
        self.assertIsNone(c.ns.routeSelection)
        self.assertFalse(c.ns.ReceivePartyRouteMessage('1|V|2|1|1|zone|501|900|900|level-zone:kalimdor/test-coast|30|10', 'Bob-TestRealm')[1])


class MultiZoneGuideTests(unittest.TestCase):
    def client(self):
        c = solo(); world_positions(c); map_canvas(c)
        catalogue(c, {900: world_quest('Home intro', level=8, series=[900, 901], seriesRoot=900),
            901: world_quest('Next zone chain', 'Test Hills', 502, 12, previousQuest=900),
            902: world_quest('Next zone work', 'Test Hills', 502, 13),
            903: world_quest('Later home work', level=18, minLevel=16)})
        c.ns.db.config.dungeonPrompts = False
        c.ns.db.config.zonePrompts = True
        return c

    def test_full_guide_keeps_future_and_cross_zone_steps_but_waits_for_unlock(self):
        c = self.client(); c.ns.profile.level = 8; c.lua.globals().playerLevel = 8
        chosen = next(g for g in c.ns.LevelingGuideChoices().values() if g.mode == 'zone' and g.homeMapID == 501)
        self.assertEqual({r.id for r in chosen.records.values()}, {900, 901, 903})
        route = c.ns.BuildGuideRoute(chosen, False)
        self.assertEqual({s.id for s in route.stops.values()}, {900})
        c.lua.globals().finished[900] = True
        c.ns.profile.level = 12; c.lua.globals().playerLevel = 12
        chosen.batchIDs = None
        route = c.ns.BuildGuideRoute(chosen, False)
        self.assertEqual(route.mapID, 502)
        self.assertEqual({s.id for s in route.stops.values()}, {901})
        self.assertEqual({r.id for r in chosen.records.values()}, {900, 901, 903})

    def test_zone_transition_popup_requires_suitable_work_and_keep_does_not_switch(self):
        c = self.client(); c.ns.profile.level = 8; c.lua.globals().playerLevel = 8
        chosen = next(g for g in c.ns.LevelingGuideChoices().values() if g.mode == 'zone' and g.homeMapID == 501)
        # Select while the home zone has useful work, then progress into its
        # linked next zone. A finished/low-only home zone need not be offered anew.
        c.lua.globals().finished[900] = True
        c.ns.profile.level = 12; c.lua.globals().playerLevel = 12
        c.ns.ShowGuideOnMap(chosen); run_plan(c); c.drain()
        prompt = c.ns.activityPrompt
        self.assertTrue(prompt.IsShown(prompt))
        self.assertIn('Start Test Hills guide?', prompt.title.text)
        self.assertEqual(prompt.later.caption.text, 'Keep my guide')
        prompt.later.OnClick()
        self.assertEqual(c.ns.routeSelection.key, chosen.key)
        c.ns.profile.level = 2
        self.assertIsNone(c.ns.LevelingZoneTransition())

    def test_accepting_zone_prompt_starts_full_next_guide_without_silent_switch(self):
        c = self.client(); c.ns.profile.level = 8; c.lua.globals().playerLevel = 8
        chosen = next(g for g in c.ns.LevelingGuideChoices().values() if g.mode == 'zone' and g.homeMapID == 501)
        c.lua.globals().finished[900] = True
        c.ns.profile.level = 12; c.lua.globals().playerLevel = 12
        c.ns.ShowGuideOnMap(chosen); run_plan(c); c.drain()
        self.assertEqual(c.ns.routeSelection.key, chosen.key)
        c.ns.activityPrompt.accept.OnClick()
        self.assertEqual(c.ns.navigation.state.status, 'Loading route…')
        run_plan(c)
        self.assertEqual(c.ns.routeSelection.key, 'level-zone:kalimdor/test-hills')
        self.assertGreaterEqual(len(c.ns.routeSelection.records), 3)


class MapEvidenceTests(unittest.TestCase):
    def test_unknown_area_points_resolve_only_by_unambiguous_native_zone_name(self):
        c = solo()
        facts = detail_facts(detail([{'point': 'start', 'id': 7, 'type': 1, 'name': 'NPC', 'coord': [55.2, 75.4]}]), {'id': 42}, {})
        self.assertNotIn('starts', facts)
        self.assertEqual(facts['unmappedLocations'][0]['sourceAreaID'], 14)
        facts.update(side='Horde', level=12, zone='Durotar')
        catalogue(c, {42: facts})
        c.lua.execute("C_Map.GetMapInfo=function(id) if id==1411 then return {name='Durotar'} end end")
        c.ns.ResolveCatalogueMaps()
        point = c.ns.CatalogueQuest(42).starts[1]
        self.assertEqual(point.mapID, 1411)
        self.assertNotEqual(point.mapID, 14)
        self.assertAlmostEqual(point.x, .552)
        c.ns.ResolveCatalogueMaps()
        self.assertEqual(len(c.ns.CatalogueQuest(42).starts), 1)

    def test_secret_or_ambiguous_native_names_do_not_resolve_points(self):
        c = solo()
        facts = detail_facts(detail([{'point': 'start', 'id': 7, 'name': 'NPC', 'coord': [55, 75]}]), {'id': 42}, {})
        catalogue(c, {42: facts})
        c.lua.execute("C_Map.GetMapInfo=function() return {name='Durotar'} end")
        c.ns.ResolveCatalogueMaps()
        self.assertIsNone(c.ns.CatalogueQuest(42).starts)
        c.ns.catalogue = c.lua.table_from({'quests': {42: facts}}, recursive=True)
        c.lua.execute('C_Map.GetMapInfo=function() return {name=secret} end')
        c.ns.ResolveCatalogueMaps()
        self.assertIsNone(c.ns.CatalogueQuest(42).starts)


class GreetingTests(unittest.TestCase):
    def client(self):
        c = previous.PickupEvidenceTests().client()
        c.lua.execute("""
        greetingIDs={901}
        function GetNumAvailableQuests() return greetingCount or #greetingIDs end
        function GetAvailableQuestInfo(index) return false,0,false,false,greetingIDs[index] end
        function GetAvailableTitle(index) return 'Greeting quest' end
        function SelectAvailableQuest(index) selectedSlot=index; picks=(picks or 0)+1 end
        """)
        c.ns.InitializeOffers()
        return c

    def test_greeting_absence_blocks_wrong_pickup_and_later_positive_offer_wins(self):
        c = self.client(); c.ns.handlers.QUEST_GREETING()
        self.assertTrue(c.ns.offered[901])
        self.assertFalse(c.ns.ObservedPickupAvailable(900))
        self.assertFalse(c.ns.CatalogueAllowed(900, c.ns.profile, c.ns.self)[0])
        c.ns.active[901] = 'Intro'
        self.assertIsNone(c.ns.ObservedPickupAvailable(900))
        c.lua.globals().greetingIDs[1] = 900
        c.ns.handlers.QUEST_GREETING()
        self.assertTrue(c.ns.ObservedPickupAvailable(900))

    def test_restricted_count_or_id_does_not_assert_npc_absence(self):
        c = self.client()
        c.lua.globals().greetingCount = c.lua.globals().secret
        c.ns.handlers.QUEST_GREETING()
        self.assertIsNone(c.ns.ObservedPickupAvailable(900))
        c.lua.globals().greetingCount = 1
        c.lua.globals().greetingIDs[1] = c.lua.globals().secret
        c.ns.handlers.QUEST_GREETING()
        self.assertIsNone(c.ns.ObservedPickupAvailable(900))
        self.assertIn('no absence inferred', c.ns.greetingReadStatus)

    def test_opt_in_selection_uses_native_index_once_and_waits_for_combat(self):
        c = self.client(); c.lua.globals().greetingIDs[2] = 900
        c.ns.db.config.autoSelectQuests = True
        c.ns.selectedRoute = c.lua.table_from({'stops': [{'id': 900, 'kind': 'a'}]}, recursive=True)
        c.lua.globals().combat = True; c.ns.ReadGreetingOffers()
        self.assertIsNone(c.lua.globals().selectedSlot)
        c.lua.globals().combat = False; c.ns.ReadGreetingOffers(); c.ns.ReadGreetingOffers()
        self.assertEqual(c.lua.globals().selectedSlot, 2)
        self.assertEqual(c.lua.globals().picks, 1)


if __name__ == '__main__':
    unittest.main()
