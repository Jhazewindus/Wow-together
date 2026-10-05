"""Player-report regressions; synthetic APIs do not establish beta compatibility."""
import unittest

from test_addon import Client
from test_routes import catalogue, guide, map_canvas, quest
from test_050 import solo, nearby
from test_053 import party_client
from test_056 import current_client, preview_client
from test_057 import plain


class ProgressionTests(unittest.TestCase):
    def test_level_25_discards_low_level_junk_but_explains_a_useful_chain(self):
        c = solo()
        c.ns.profile.level = 25
        catalogue(c, {900: nearby('Old junk', level=10),
                      901: nearby('Useful prerequisite', level=10),
                      902: nearby('Relevant followup', level=24, previousQuest=901)})
        self.assertFalse(c.ns.LevelingQuestEnabled(900))
        allowed, reason = c.ns.LevelingValue(901)
        self.assertTrue(allowed)
        self.assertIn('Relevant followup', reason)
        stop = c.lua.table_from({'id': 901, 'kind': 'a', 'mapID': 501})
        self.assertIn('Unlocks Relevant followup', c.ns.RouteContext(stop, 501))

    def test_remote_future_dungeon_or_wrong_faction_does_not_justify_old_junk(self):
        c = solo(); c.ns.profile.level = 25
        catalogue(c, {900: nearby(level=5),
                      901: nearby('Distant dungeon', level=60, minLevel=55, previousQuest=900, questType='Dungeon'),
                      902: nearby('Alliance followup', level=24, side='Alliance', previousQuest=900)})
        self.assertFalse(c.ns.LevelingValue(900)[0])

    def test_completed_followup_on_ahead_player_does_not_exclude_friends_catchup(self):
        c = party_client(ids=(901,))
        c.ns.profile.level = 25
        c.ns.members['Bob-TestRealm'].profile.level = 25
        catalogue(c, {900: nearby('Useful intro', level=10),
                      901: nearby('Worthwhile followup', level=24, previousQuest=900)})
        c.lua.globals().finished[901] = True
        c.receive('1|C|2|1|1|')
        c.receive('1|K|2|1|1|900,901')
        self.assertTrue(c.ns.LevelingValue(900)[0])

    def test_useful_dungeon_prerequisite_is_disclosed(self):
        c = solo(); c.ns.profile.level = 25
        catalogue(c, {900: nearby(level=10),
                      901: nearby('Dungeon pickup', level=26, minLevel=20, previousQuest=900, questType='Dungeon')})
        self.assertIn('dungeon quest', c.ns.LevelingValue(900)[1])

    def test_elites_are_labeled_and_automatic_solo_discovery_excludes_them(self):
        c = solo()
        catalogue(c, {900: nearby(questType='Elite')})
        self.assertFalse(c.ns.LevelingQuestEnabled(900))
        self.assertEqual(c.ns.QuestDifficultyLabel(900), 'Group / elite')
        c.lua.globals().grouped = True
        c.unit_names({'player': ['Alice', 'TestRealm'], 'party1': ['Bob', 'TestRealm']})
        self.assertTrue(c.ns.LevelingQuestEnabled(900))

    def test_party_starts_with_the_member_behind_in_the_chain(self):
        c = party_client(ids=(901,))
        catalogue(c, {900: quest('Earlier'), 901: quest('Later', previousQuest=900)})
        c.lua.globals().finished[900] = True
        c.receive('1|C|2|1|1|')
        c.receive('1|K|2|1|1|900,901')
        selected = guide(c, (901, 900), key='series:900')
        self.assertEqual(c.ns.GuideFocus(selected.records), 'Bob-TestRealm')
        selected.focusKey = c.ns.GuideFocus(selected.records)
        route = c.ns.BuildGuideRoute(selected, False)
        self.assertEqual(route.stops[1].id, 900)
        self.assertEqual(route.stops[1].memberKey, 'Bob-TestRealm')
        self.assertFalse(any(s.id == 901 for s in route.stops.values()))
        c.receive('1|S|3|1|1|')
        c.receive('1|C|4|1|1|900')
        c.receive('1|K|4|1|1|900,901')
        route = c.ns.BuildGuideRoute(selected, False)
        self.assertEqual(route.stops[1].id, 901)
        self.assertEqual(route.stops[1].kind, 'a')

    def test_zone_change_and_new_active_quest_keep_the_explicit_guide(self):
        c = current_client({900: quest('Travel quest', map_id=502), 901: nearby('Local quest')})
        chosen = guide(c, (900,), key='zone-route:502')
        map_canvas(c); c.ns.ShowGuideOnMap(chosen)
        c.ns.profile.mapID = 502
        c.ns.Refresh()
        self.assertEqual(c.ns.routeSelection.key, chosen.key)
        self.assertEqual({r.id for r in c.ns.routeSelection.records.values()}, {900})
        self.assertEqual(c.ns.selectedRoute.stops[1].mapID, 502)


class PickupEvidenceTests(unittest.TestCase):
    def client(self):
        c = solo()
        start = [{'mapID': 501, 'x': .21, 'y': .37, 'name': 'Giver', 'npc': True, 'entityID': 123}]
        catalogue(c, {900: quest('Unknown unlock', starts=start),
                      901: quest('Intro', starts=[dict(point) for point in start])})
        c.lua.execute("function UnitGUID() return 'Creature-0-1-2-3-123-ABC' end")
        return c

    def test_real_npc_absence_blocks_pickup_until_progress_changes(self):
        c = self.client()
        c.ns.RecordNPCOfferAvailability(c.lua.table_from([{'questID': 901}], recursive=True))
        self.assertFalse(c.ns.CatalogueAllowed(900, c.ns.profile, c.ns.self)[0])
        c.ns.active[901] = 'Intro'
        self.assertIsNone(c.ns.ObservedPickupAvailable(900))
        c.ns.RecordNPCOfferAvailability(c.lua.table_from([{'questID': 900}], recursive=True))
        self.assertTrue(c.ns.CatalogueAllowed(900, c.ns.profile, c.ns.self))

    def test_restricted_offer_cannot_establish_unavailability(self):
        c = self.client()
        c.ns.RecordNPCOfferAvailability(c.lua.table_from([{'questID': c.lua.globals().secret}], recursive=True))
        self.assertIsNone(c.ns.ObservedPickupAvailable(900))

    def test_single_quest_dialog_is_positive_evidence_without_negative_inference(self):
        c = self.client()
        c.ns.RecordNPCOfferAvailability(c.lua.table_from([{'questID': 901}], recursive=True), False)
        self.assertTrue(c.ns.ObservedPickupAvailable(901))
        self.assertIsNone(c.ns.ObservedPickupAvailable(900))
        c.ns.handlers.QUEST_TURNED_IN()
        self.assertIsNone(c.ns.ObservedPickupAvailable(901))

    def test_dialog_selection_uses_exact_guide_id_once_and_defers_in_combat(self):
        c = self.client()
        c.ns.db.config.autoSelectQuests = True
        c.ns.selectedRoute = c.lua.table_from({'stops': [{'id': 900, 'kind': 'a'}]}, recursive=True)
        c.lua.execute('C_GossipInfo={SelectAvailableQuest=function(id) selectedQuest=id; picks=(picks or 0)+1 end}')
        c.ns.offered[900], c.ns.offered[901] = True, True
        c.lua.globals().combat = True; c.ns.AutoSelectGuideQuest()
        self.assertIsNone(c.lua.globals().selectedQuest)
        c.lua.globals().combat = False; c.ns.AutoSelectGuideQuest(); c.ns.AutoSelectGuideQuest()
        self.assertEqual(c.lua.globals().selectedQuest, 900)
        self.assertEqual(c.lua.globals().picks, 1)


class GuideControlTests(unittest.TestCase):
    def test_library_render_does_not_recompute_discovery_for_a_selected_route(self):
        c = current_client({900: nearby('Already accepted')})
        map_canvas(c); c.ns.ShowGuideOnMap(c.ns.GuideChoices()[1])
        chosen = c.ns.routeSelection.key
        c.ns.GuideChoices = c.lua.eval("function() error('unnecessary discovery calculation') end")
        c.ns.filter = 'library'; c.ns.Render()
        self.assertEqual(c.ns.routeSelection.key, chosen)

    def test_party_quests_keeps_a_quest_log_route_selectable(self):
        c = current_client({900: nearby('Already accepted')})
        c.ns.filter = 'all'; c.ns.Render()
        self.assertTrue(any(card.guide and card.guide.mode in ('current', 'bundle')
                            for card in c.ns.ui.cards.values()))

    def test_already_accepted_quest_has_a_read_only_pickup_preview(self):
        c = current_client({900: nearby('Already accepted')})
        map_canvas(c); c.ns.ShowGuideOnMap(c.ns.GuideChoices()[1])
        self.assertEqual(c.ns.selectedRoute.stops[1].kind, 'q')
        c.ns.PreviewGuideStep(-1)
        self.assertEqual(c.ns.navigation.state.stop.kind, 'a')
        self.assertIn('History preview', c.ns.navigation.step.text)
        self.assertTrue(c.ns.active[900])
        self.assertFalse(c.ns.Completed(900))
        c.ns.SkipGuide('quest')
        self.assertFalse(c.ns.GuideQuestSkipped(900))

    def test_scan_rebuilds_quest_log_selection_without_popup(self):
        c = current_client({900: nearby('Done now'), 901: nearby('Still active')})
        map_canvas(c); c.ns.ShowGuideOnMap(c.ns.GuideChoices()[1])
        c.lua.execute("entries={{questID=901,title='Still active',isHeader=false}}; finished[900]=true")
        c.ns.navigation.scan.OnClick(); c.drain()
        self.assertEqual({r.id for r in c.ns.routeSelection.records.values()}, {901})
        self.assertIsNone(c.ns.guideScanWindow)
        self.assertIsNone(c.ns.navigation.notice)

    def test_all_skipped_guide_can_scan_again_and_reconsider_only_when_enabled(self):
        c = preview_client()
        c.ns.SkipGuide('quest')
        self.assertTrue(c.ns.GuideQuestSkipped(900))
        self.assertIsNotNone(c.ns.routeSelection)
        c.ns.ScanGuideProgress(); c.drain()
        self.assertTrue(c.ns.GuideQuestSkipped(900))
        self.assertEqual(len(c.ns.selectedRoute.stops), 0)
        c.ns.SetOption('scanSkipped', True); c.ns.ScanGuideProgress(); c.drain()
        self.assertFalse(c.ns.GuideQuestSkipped(900))
        self.assertGreater(len(c.ns.selectedRoute.stops), 0)
        self.assertTrue(c.ns.active[900])
        self.assertFalse(c.ns.Completed(900))

    def test_previous_and_next_are_previews_and_scan_returns_to_current_step(self):
        c = current_client({900: nearby('First'), 901: nearby('Second')})
        map_canvas(c); c.ns.ShowGuideOnMap(c.ns.GuideChoices()[1])
        c.lua.execute("entries={{questID=901,title='Second',isHeader=false}}; finished[900]=true")
        c.ns.SyncNow(False)
        c.ns.PreviewGuideStep(-1)
        self.assertEqual(c.ns.navigation.state.stop.id, 900)
        self.assertFalse(c.ns.active[900])
        self.assertTrue(c.ns.Completed(900))
        c.ns.PreviewGuideStep(1)
        c.ns.PreviewGuideStep(1)
        self.assertEqual(c.ns.navigation.state.stop.kind, 't')
        c.ns.ScanGuideProgress(); c.drain()
        self.assertIsNone(c.ns.navigationPreview)
        self.assertEqual(c.ns.navigation.state.stop.id, 901)

    def test_start_popup_preserves_selection_until_a_route_choice(self):
        c = current_client({900: nearby('Current quest')})
        c.ns.catalogue.quests[901] = c.lua.table_from(nearby('Chosen guide'), recursive=True)
        map_canvas(c)
        chosen = guide(c, (901,), key='quest:901')
        c.ns.RequestStartRoute(chosen)
        self.assertIsNone(c.ns.routeSelection)
        self.assertIn('unusual routes', c.ns.startGuidePrompt.text.text)
        c.ns.startGuidePrompt.current.OnClick()
        self.assertEqual({r.id for r in c.ns.routeSelection.records.values()}, {900, 901})
        self.assertEqual(c.ns.routeSelection.baseGuide.key, chosen.key)

    def test_distance_units_and_meaningful_settings_dropdowns(self):
        c = solo()
        self.assertEqual(c.ns.FormatDistance(100), '100 yd')
        c.ns.settings.dropdowns.distanceUnits.options['metres'].OnClick()
        self.assertEqual(c.ns.FormatDistance(100), '91 m')
        c.ns.settings.section.options['navigation'].OnClick()
        self.assertTrue(c.ns.settings.pages.navigation.IsShown(c.ns.settings.pages.navigation))
        self.assertFalse(c.ns.settings.pages.guides.IsShown(c.ns.settings.pages.guides))
        c.ns.ui.viewChoice.options['library'].OnClick()
        self.assertEqual(c.ns.ui.viewChoice.caption.text, 'All quests  ▾')
        c.ns.ui.viewChoice.options['all'].OnClick()
        self.assertEqual(c.ns.ui.viewChoice.caption.text, 'Party quests  ▾')

    def test_tracker_auto_join_solo_and_raid_behavior(self):
        c = solo(); c.ns.RenderTracker()
        self.assertFalse(c.ns.tracker.IsShown(c.ns.tracker))
        c.lua.globals().grouped = True; c.ns.handlers.GROUP_ROSTER_UPDATE()
        self.assertTrue(c.ns.tracker.IsShown(c.ns.tracker))
        c.ns.ToggleTracker(); c.ns.Refresh()
        self.assertFalse(c.ns.tracker.IsShown(c.ns.tracker))
        c.lua.globals().raid = True; c.ns.handlers.GROUP_ROSTER_UPDATE()
        self.assertFalse(c.ns.tracker.IsShown(c.ns.tracker))
        c.lua.globals().raid = False; c.ns.handlers.GROUP_ROSTER_UPDATE()
        self.assertTrue(c.ns.tracker.IsShown(c.ns.tracker))

    def test_kill_collection_and_dialogue_have_distinct_instructions(self):
        c = solo()
        for action, expected in [('kill', 'Kill Boar'), ('collect', 'Pick up Apple'), ('talk', 'Talk to Giver')]:
            name = 'Apple' if action == 'collect' else 'Boar'
            stop = c.lua.table_from({'id': 900, 'kind': 'q', 'action': action, 'targetName': name, 'npcName': 'Giver'})
            self.assertEqual(c.ns.StopInstruction(stop), expected)


def flight_client(include_geography=False):
    c = current_client({900: quest('Far goal', objectives=[{'mapID': 501, 'x': .95, 'y': .4, 'name': 'Target'}])})
    map_canvas(c); c.ns.ShowGuideOnMap(c.ns.GuideChoices()[1])
    c.lua.execute("""
    clock=100; flying=false
    function GetTime() return clock end
    function GetUnitSpeed() return 7,7 end
    function UnitOnTaxi() return flying end
    function CreateVector2D(x,y) return {GetXY=function() return x,y end} end
    C_Map.GetPlayerMapPosition=function() return CreateVector2D(.02,.4) end
    C_Map.GetWorldPosFromMapPos=function(map,p) local x,y=p:GetXY(); return 1,CreateVector2D(x*10000,y*10000) end
    C_Map.GetMapWorldSize=function() return 10000,10000 end
    Enum.FlightPathState={Current=60,Reachable=70,Unreachable=80}
    taxiNodes={{nodeID=11,name='Start',position=CreateVector2D(.02,.4),state=60,slotIndex=40},
               {nodeID=22,name='End',position=CreateVector2D(.9,.4),state=70,slotIndex=54}}
    function GetTaxiMapID() return 501 end
    C_TaxiMap={GetAllTaxiNodes=function(map)
      assert(map==501,'A valid taxi map ID is required');return taxiNodes
    end}
    function TakeTaxiNode(slot) taken=slot; takeCalls=(takeCalls or 0)+1 end
    """)
    # Synthetic IDs 11/22 must not collide with shipped real flight-node geography.
    if not include_geography:
        c.ns.travelData = c.lua.table_from({'nodes': {}, 'edges': {}, 'factors': {}}, recursive=True)
    return c


class TravelTests(unittest.TestCase):
    def test_malformed_saved_travel_data_is_discarded(self):
        c = flight_client()
        state = c.ns.db.flights[c.ns.self]
        state.nodes[12] = 7
        state.edges['bad'] = c.lua.table_from({'source': 'bad', 'destination': 12})
        state.timings['bad'] = c.lua.table_from({'mean': 'bad', 'samples': 1})
        state.corpse = c.lua.table_from({'mapID': 501, 'x': 7, 'y': .5})
        c.ns.InitializeTravel()
        self.assertIsNone(state.nodes[12])
        self.assertIsNone(state.edges['bad'])
        self.assertIsNone(state.timings['bad'])
        self.assertIsNone(state.corpse)

    def test_unknown_taxi_state_does_not_record_a_finished_ride(self):
        c = flight_client(); c.ns.ReadFlightMap()
        c.ns.NoteFlightSelection(54)
        c.lua.execute('flying=true; clock=100')
        c.ns.FlightState()
        c.lua.execute('clock=200; UnitOnTaxi=function() return secret end')
        c.ns.FinishFlight()
        self.assertIsNotNone(c.ns.pendingFlight)
        self.assertIsNone(c.ns.db.flights[c.ns.self].timings['11:22'])

    def test_flight_recommendation_requires_observed_network_and_labels_estimate(self):
        c = flight_client()
        self.assertIsNone(c.ns.FindFlightPlan(c.ns.selectedRoute.stops[1]))
        c.ns.ReadFlightMap()
        plan = c.ns.FindFlightPlan(c.ns.selectedRoute.stops[1])
        self.assertEqual(plan.destination.name, 'End')
        self.assertLess(plan.seconds, plan.walkingSeconds)
        self.assertFalse(plan.measured)
        self.assertIn('Estimated flight', c.ns.navigation.context.text)
        self.assertEqual(c.ns.RouteForDisplay().stops[1].kind, 'f')
        self.assertIsNone(c.lua.globals().taken)

    def test_opt_in_auto_flight_uses_native_slot_not_node_id_once(self):
        c = flight_client(); c.ns.db.config.autoFly = True
        c.ns.ReadFlightMap(); c.ns.TrySuggestedFlight()
        self.assertEqual(c.lua.globals().taken, 54)
        self.assertEqual(c.lua.globals().takeCalls, 1)

    def test_skipped_flight_step_keeps_the_flight_manual(self):
        c = flight_client(); c.ns.ReadFlightMap()
        c.ns.SkipGuide('step')
        c.ns.db.config.autoFly = True
        c.ns.TrySuggestedFlight()
        self.assertIsNone(c.lua.globals().taken)

    def test_combat_or_restricted_flight_map_never_calls_taxi_action(self):
        c = flight_client(); c.ns.db.config.autoFly = True
        c.lua.globals().combat = True; c.ns.ReadFlightMap()
        self.assertIsNone(c.lua.globals().taken)
        c.lua.execute('combat=false; C_TaxiMap.GetAllTaxiNodes=function() return secret end')
        c.ns.ReadFlightMap(); c.ns.TrySuggestedFlight()
        self.assertIsNone(c.ns.visibleFlights)
        self.assertIsNone(c.lua.globals().taken)

    def test_flying_shows_estimated_then_measured_remaining_time(self):
        c = flight_client(); c.ns.ReadFlightMap(); c.ns.NoteFlightSelection(54)
        c.lua.globals().flying = True; c.ns.UpdateNavigation()
        c.lua.globals().clock = 112; c.ns.UpdateNavigation()
        self.assertIn('Estimated', c.ns.navigation.distance.text)
        self.assertFalse(c.ns.navigation.symbol.IsShown(c.ns.navigation.symbol))
        c.lua.globals().flying = False; c.ns.FinishFlight()
        self.assertEqual(c.ns.db.flights[c.ns.self].timings['11:22'].mean, 12)
        c.ns.NoteFlightSelection(54); c.lua.globals().flying = True; c.ns.UpdateNavigation()
        self.assertIn('remaining', c.ns.navigation.distance.text)

    def test_flight_progress_and_character_network_are_not_shared(self):
        c = flight_client(); c.ns.ReadFlightMap()
        saved = plain(c.ns.db)
        other = Client(name='Different', quests=(), saved_variables=saved)
        self.assertEqual(len(other.ns.db.flights[other.ns.self].nodes), 0)
        same = Client(quests=(), saved_variables=saved)
        self.assertEqual(same.ns.db.flights[same.ns.self].nodes[22].name, 'End')

    def test_missing_flight_apis_leave_regular_navigation_working(self):
        c = preview_client(); c.ns.ReadFlightMap(); c.ns.UpdateNavigation()
        self.assertIn('unavailable', c.ns.travelStatus)
        self.assertEqual(c.ns.navigation.state.stop.kind, 'q')

    def test_corpse_directions_keep_the_guide_and_original_death_zone(self):
        c = preview_client()
        key = c.ns.routeSelection.key
        c.ns.handlers.PLAYER_DEAD()
        c.lua.execute("""
        ghost=true; function UnitIsGhost() return ghost end
        C_Map.GetBestMapForUnit=function() return 502 end
        C_DeathInfo={GetCorpseMapPosition=function(map)
            assert(map==501); return {GetXY=function() return .3,.4 end} end}
        """)
        c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.state.stop.kind, 'corpse')
        self.assertEqual(c.ns.navigation.state.stop.mapID, 501)
        c.ns.SkipGuide('quest')
        self.assertFalse(c.ns.GuideQuestSkipped(900))
        c.lua.globals().ghost = False; c.ns.handlers.PLAYER_UNGHOST()
        self.assertEqual(c.ns.routeSelection.key, key)
        self.assertEqual(c.ns.navigation.state.stop.kind, 'q')

    def test_restricted_corpse_position_shows_unknown_without_quest_direction(self):
        c = preview_client()
        c.lua.execute('function UnitIsGhost() return true end; C_DeathInfo={GetCorpseMapPosition=function() return secret end}')
        c.ns.UpdateNavigation()
        self.assertIn('Corpse position unavailable', c.ns.navigation.state.status)
        self.assertIsNone(c.ns.navigation.state.angle)


class ItemHintTests(unittest.TestCase):
    def test_item_tooltip_cross_disappears_when_the_objective_is_finished(self):
        c = current_client({900: nearby('Apples', requiredItems=[{'itemID': 42, 'name': 'Apple', 'quantity': 6}])})
        c.lua.execute("tooltip={AddLine=function(_,text) hint=text end}")
        data = c.lua.table_from({'id': 42})
        c.ns.QuestItemTooltip(c.lua.globals().tooltip, data)
        self.assertIn('× Needed for', c.lua.globals().hint)
        c.ns.localProgress[900] = c.lua.table_from({'objectives': [{'text': 'Apple: 6/6', 'have': 6, 'need': 6, 'finished': True}]}, recursive=True)
        c.lua.globals().hint = None
        c.ns.QuestItemTooltip(c.lua.globals().tooltip, data)
        self.assertIsNone(c.lua.globals().hint)
        c.ns.localProgress[900].objectives[1].finished = False
        c.lua.globals().combat = True
        c.ns.QuestItemTooltip(c.lua.globals().tooltip, data)
        self.assertIsNone(c.lua.globals().hint)


if __name__ == '__main__':
    unittest.main()
