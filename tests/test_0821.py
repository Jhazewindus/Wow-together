"""Optional personal class-training stops, guide preservation and source scope."""
import json
import unittest

from test_addon import Client, ROOT
from test_navigation import navigator
from test_routes import guide, map_canvas
from test_063 import primitive


def training_client(c=None):
    if c is None:
        c = navigator()
    else:
        c.guide_environment(level=10)
        from test_routes import catalogue, quest
        catalogue(c, {900: quest()})
    c.lua.execute('''clock=1; function GetTime()return clock end
        function UnitLevel()return 10 end
        function UnitOnTaxi()return false end; function UnitIsGhost()return false end
        function GetPlayerFacing()return 0 end
        C_Map.GetMapWorldSize=function()return 1000,1000 end''')
    c.ns.profile.level, c.ns.profile.classID, c.ns.profile.faction = 10, 7, 'Horde'
    c.ns.db.config.travelNetwork = False
    c.ns.guideServiceData = c.lua.table_from({'trainers': [{
        'id': 'TRAINER_TEST:Horde', 'classID': 7, 'name': 'Shaman trainer',
        'hub': 'Test hub', 'faction': 'Horde', 'npcIDs': [500],
        'mapID': 501, 'x': .23, 'y': .37}], 'inns': [], 'taxis': {}}, recursive=True)
    c.ns.questEntities.npc[500] = c.lua.table_from({'name': 'Test trainer'})
    c.ns.routeSelection = guide(c)
    c.ns.routeSelection.mode = 'zone'
    c.ns.selectedRoute = c.lua.table_from({'mapID': 501, 'stops': [{
        'id': 900, 'mapID': 501, 'x': .21, 'y': .27,
        'kind': 'a', 'title': 'Pickup quest', 'guideStep': 7}]}, recursive=True)
    return c


class ClassTrainingTests(unittest.TestCase):
    def test_nearby_training_is_an_optional_step_without_editing_the_quest_plan(self):
        c = training_client()
        before = primitive(c.ns.selectedRoute)
        c.ns.UpdateNavigation()
        stop = c.ns.navigation.state.stop
        self.assertEqual(stop.kind, 'trainer')
        self.assertEqual(stop.npcName, 'Test trainer')
        self.assertEqual(stop.trainingLevel, 10)
        self.assertIn('Optional', c.ns.navigation.step.text)
        self.assertEqual(c.ns.navigation.skipQuest.caption.text, 'Done training')
        self.assertEqual(primitive(c.ns.selectedRoute), before)
        self.assertFalse(c.ns.Completed(900)); self.assertFalse(c.ns.GuideQuestSkipped(900))

    def test_reminder_is_due_at_even_levels_and_remains_due_at_the_next_odd_level(self):
        for level, expected in ((1, None), (2, 2), (3, 2), (10, 10), (11, 10), (12, 12)):
            c = training_client(); c.ns.profile.level = level
            c.ns.UpdateNavigation()
            stop = c.ns.navigation.state.stop
            self.assertEqual(stop.trainingLevel, expected)

    def test_done_resumes_quests_and_suppresses_the_check_until_the_next_even_level(self):
        c = training_client(); c.ns.UpdateNavigation()
        sent = len(c.lua.globals().sent)
        c.ns.navigation.skipQuest.OnClick()
        self.assertEqual(c.ns.navigation.state.stop.id, 900)
        self.assertEqual(c.ns.db.classTraining[c.ns.self].checked, 10)
        self.assertEqual(c.ns.navigation.skipQuest.caption.text, 'Skip quest')
        self.assertEqual(len(c.lua.globals().sent), sent)
        self.assertFalse(c.ns.GuideQuestSkipped(900)); self.assertFalse(c.ns.Completed(900))
        c.ns.profile.level = 11; c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.state.stop.id, 900)
        c.ns.profile.level = 12; c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.state.stop.trainingLevel, 12)

    def test_skip_is_personal_and_does_not_skip_any_quest_or_learn_a_prerequisite(self):
        c = training_client(); c.ns.UpdateNavigation()
        events = primitive(c.ns.db.questResearch) if c.ns.db.questResearch else None
        c.ns.navigation.skipStep.OnClick()
        self.assertEqual(c.ns.navigation.state.stop.id, 900)
        self.assertEqual(c.ns.db.classTraining[c.ns.self].declined, 10)
        self.assertEqual(c.ns.db.classTraining[c.ns.self].checked, 0)
        self.assertFalse(c.ns.GuideQuestSkipped(900))
        self.assertFalse(c.ns.GuideQuestSkipped(0))
        self.assertEqual(primitive(c.ns.db.questResearch) if c.ns.db.questResearch else None, events)
        c.ns.profile.level = 12; c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.state.stop.kind, 'trainer')

    def test_pending_stop_and_acknowledgement_survive_reload_without_affecting_another_character(self):
        c = training_client(); c.ns.UpdateNavigation()
        fresh = training_client(Client(quests=(), saved_variables=primitive(c.ns.db)))
        fresh.ns.UpdateNavigation()
        self.assertEqual(fresh.ns.navigation.state.stop.kind, 'trainer')
        fresh.ns.FinishClassTraining(True)
        restored = training_client(Client(quests=(), saved_variables=primitive(fresh.ns.db)))
        restored.ns.UpdateNavigation(); self.assertEqual(restored.ns.navigation.state.stop.id, 900)
        other = training_client(Client(name='Other', quests=(), saved_variables=primitive(fresh.ns.db)))
        other.ns.UpdateNavigation(); self.assertEqual(other.ns.navigation.state.stop.kind, 'trainer')

    def test_only_the_players_class_and_known_friendly_trainers_are_selected(self):
        for field, value in (('classID', 8), ('faction', 'Alliance'), ('faction', None)):
            c = training_client(); c.ns.guideServiceData.trainers[1][field] = value
            c.ns.UpdateNavigation(); self.assertEqual(c.ns.navigation.state.stop.id, 900)
        c = training_client(); c.ns.guideServiceData.trainers[1].faction = 'Both'
        c.ns.UpdateNavigation(); self.assertEqual(c.ns.navigation.state.stop.kind, 'trainer')

    def test_each_supported_class_uses_the_same_zone_independent_rules(self):
        for class_id in (1, 2, 3, 4, 5, 7, 8, 9, 11):
            c = training_client(); c.ns.profile.classID = class_id
            c.ns.guideServiceData.trainers[1].classID = class_id
            c.ns.UpdateNavigation(); self.assertEqual(c.ns.navigation.state.stop.kind, 'trainer')

    def test_out_of_range_or_excessive_side_trip_is_not_inserted(self):
        for x, y in ((.21, .55), (.21, .21)):
            c = training_client(); p = c.ns.guideServiceData.trainers[1]; p.x, p.y = x, y
            c.ns.selectedRoute.stops[1].x, c.ns.selectedRoute.stops[1].y = .37, .37
            c.ns.UpdateNavigation(); self.assertEqual(c.ns.navigation.state.stop.id, 900)

    def test_physical_range_does_not_depend_on_normalized_map_size_or_display_units(self):
        for width in (1000, 10000):
            c = training_client(); c.lua.globals().width = width
            c.lua.execute('C_Map.GetMapWorldSize=function()return width,1000 end')
            c.ns.db.config.distanceUnits = 'metres'
            c.ns.selectedRoute.stops[1].x, c.ns.selectedRoute.stops[1].y = .21 + 140 / width, .37
            c.ns.guideServiceData.trainers[1].x = .21 + 100 / width
            c.ns.UpdateNavigation(); self.assertEqual(c.ns.navigation.state.stop.kind, 'trainer')

    def test_objectives_are_not_interrupted_but_leaving_a_known_hub_can_include_training(self):
        c = training_client(); stop = c.ns.selectedRoute.stops[1]
        stop.kind, stop.x, stop.y = 'q', .22, .37
        c.ns.UpdateNavigation(); self.assertEqual(c.ns.navigation.state.stop.id, 900)
        stop.x = .9; c.lua.globals().clock = 3
        c.ns.UpdateNavigation(); self.assertEqual(c.ns.navigation.state.stop.kind, 'trainer')

    def test_incomplete_hub_data_does_not_route_a_distant_objective_to_an_unscoped_trainer(self):
        c = training_client(); c.ns.guideServiceData.trainers[1].hub = None
        stop = c.ns.selectedRoute.stops[1]; stop.kind, stop.x, stop.y = 'q', .9, .37
        c.ns.UpdateNavigation(); self.assertEqual(c.ns.navigation.state.stop.id, 900)

    def test_no_automatic_purchases_or_spell_availability_claims(self):
        c = training_client()
        c.lua.execute('function BuyTrainerService()error("unexpected purchase")end')
        c.ns.UpdateNavigation(); c.ns.FinishClassTraining(True)
        self.assertEqual(c.ns.db.classTraining[c.ns.self].checked, 10)
        self.assertIn('training check', c.ns.RouteContext(c.lua.table_from({
            'kind': 'trainer', 'trainingLevel': 10, 'mapID': 501, 'x': .23, 'y': .37})))

    def test_option_and_non_leveling_modes_do_not_change_the_quest_route(self):
        c = training_client(); c.ns.db.config.classTraining = False
        c.ns.UpdateNavigation(); self.assertEqual(c.ns.navigation.state.stop.id, 900)
        for mode in ('travel', 'dungeon', None):
            c = training_client(); c.ns.routeSelection.mode = mode
            self.assertEqual(c.ns.ClassTrainingDestination(c.ns.selectedRoute.stops[1]).id, 900)

    def test_secret_identity_positions_scale_and_travel_flags_do_not_create_stops(self):
        replacements = ('C_Map.GetPlayerMapPosition=function()return secret end',
            'C_Map.GetMapWorldSize=function()return secret,secret end',
            'function UnitOnTaxi()return secret end', 'function UnitIsGhost()return secret end')
        for replacement in replacements:
            c = training_client(); c.lua.execute(replacement)
            self.assertEqual(c.ns.ClassTrainingDestination(c.ns.selectedRoute.stops[1]).id, 900)
        for field in ('level', 'classID', 'faction'):
            c = training_client(); c.ns.profile[field] = c.lua.globals().secret
            self.assertEqual(c.ns.ClassTrainingDestination(c.ns.selectedRoute.stops[1]).id, 900)

    def test_busy_preview_combat_ghost_and_flight_states_do_not_insert_a_new_stop(self):
        for field, value in (('guideScanning', {}), ('routePlanning', {}), ('routePaused', 'Wait'), ('navigationPreview', {})):
            c = training_client(); c.ns[field] = c.lua.table_from(value) if isinstance(value, dict) else value
            self.assertEqual(c.ns.ClassTrainingDestination(c.ns.selectedRoute.stops[1]).id, 900)
        for statement in ('combat=true', 'function UnitIsGhost()return true end', 'function UnitOnTaxi()return true end'):
            c = training_client(); c.lua.execute(statement)
            self.assertEqual(c.ns.ClassTrainingDestination(c.ns.selectedRoute.stops[1]).id, 900)

    def test_route_change_does_not_drag_the_old_trainers_stop_into_another_guide(self):
        c = training_client(); c.ns.UpdateNavigation()
        c.ns.routeSelection.key = 'different-zone'
        c.ns.db.config.classTraining = False
        c.ns.UpdateNavigation(); self.assertEqual(c.ns.navigation.state.stop.id, 900)
        self.assertFalse(c.ns.FinishClassTraining(True))

    def test_scanning_keeps_the_pending_service_separate_from_quest_skips(self):
        c = training_client(); c.ns.UpdateNavigation()
        c.ns.ResetGuideSkips()
        self.assertIsNotNone(c.ns.db.classTraining[c.ns.self].pending)
        self.assertFalse(c.ns.GuideQuestSkipped(900))

    def test_map_prepend_keeps_full_quest_previews_and_marks_training_with_T(self):
        c = training_client(); map_canvas(c); c.ns.UpdateNavigation()
        c.ns.selectedRoute.previewStops = c.ns.selectedRoute.stops
        before = primitive(c.ns.selectedRoute)
        display = c.ns.RouteForDisplay()
        self.assertEqual(display.stops[1].kind, 'trainer')
        self.assertEqual(display.stops[2].id, 900)
        self.assertEqual(display.previewStops[2].guideStep, 7)
        self.assertEqual(c.ns.StopSymbol(display.stops[1]), 'T')
        self.assertEqual(primitive(c.ns.selectedRoute), before)
        c.ns.FinishClassTraining(False)
        self.assertEqual(c.ns.RouteForDisplay().stops[1].id, 900)

    def test_standalone_only_arrow_has_compact_done_and_skip_controls(self):
        c = training_client(); c.ns.db.config.routeArrow = False; c.ns.db.config.standaloneArrow = True
        c.ns.UpdateNavigation(); frame = c.ns.standaloneNavigation
        self.assertTrue(frame.training.IsShown(frame.training))
        frame.training.done.OnClick()
        self.assertEqual(c.ns.navigation.state.stop.id, 900)
        self.assertFalse(frame.training.IsShown(frame.training))

    def test_arrival_alone_does_not_acknowledge_training_or_complete_a_quest(self):
        c = training_client(); c.ns.guideServiceData.trainers[1].x = .21
        c.ns.UpdateNavigation(); self.assertTrue(c.ns.navigation.state.arrived)
        self.assertEqual(c.ns.db.classTraining[c.ns.self].checked, 0)
        self.assertEqual(c.ns.navigation.state.stop.kind, 'trainer')
        self.assertFalse(c.ns.Completed(900))

    def test_cached_negative_results_do_not_rescan_on_each_arrow_tick(self):
        c = training_client(); c.ns.guideServiceData.trainers[1].x = .9
        c.lua.globals().oldDistance = c.ns.TravelPointDistance
        c.lua.execute('distanceCalls=0')
        c.ns.TravelPointDistance = c.lua.eval('function(...)distanceCalls=distanceCalls+1;return oldDistance(...)end')
        stop = c.ns.selectedRoute.stops[1]
        c.ns.ClassTrainingDestination(stop); calls = c.lua.globals().distanceCalls
        for _ in range(20): c.ns.ClassTrainingDestination(stop)
        self.assertEqual(c.lua.globals().distanceCalls, calls)
        c.lua.globals().clock = 3; c.ns.ClassTrainingDestination(stop)
        self.assertGreater(c.lua.globals().distanceCalls, calls)

    def test_npc_confirmation_takes_precedence_without_creating_a_training_stop(self):
        c = training_client()
        confirmation = c.lua.table_from({'id': 901, 'kind': 'a', 'confirmation': True,
            'title': 'Check NPC offers', 'mapID': 501, 'x': .21, 'y': .27})
        c.ns.CurrentQuestConfirmation = lambda: confirmation
        c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.state.stop.id, 901)
        self.assertIsNone(c.ns.db.classTraining[c.ns.self].pending)
        self.assertEqual(c.ns.RouteForDisplay().stops[1].id, 901)

    def test_training_is_independent_of_class_quests_and_the_option_resumes_immediately(self):
        c = training_client(); c.ns.db.config.classQuests = False
        c.ns.UpdateNavigation(); self.assertEqual(c.ns.navigation.state.stop.kind, 'trainer')
        c.ns.db.config.classTraining = False; c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.state.stop.id, 900)
        c.ns.db.config.classTraining = True; c.ns.UpdateNavigation()
        self.assertEqual(c.ns.navigation.state.stop.kind, 'trainer')
        self.assertFalse(c.ns.GuideQuestSkipped(900))

    def test_public_world_geometry_can_find_a_nearby_trainer_across_a_city_map_boundary(self):
        c = training_client()
        c.lua.execute('''function CreateVector2D(x,y)return {GetXY=function()return x,y end}end
            C_Map.GetWorldPosFromMapPos=function(map,p)
              local x,y=p:GetXY();return 1,CreateVector2D(x*1000,y*1000)
            end''')
        c.ns.guideServiceData.trainers[1].mapID = 502
        self.assertEqual(c.ns.ClassTrainingDestination(c.ns.selectedRoute.stops[1]).mapID, 502)

    def test_a_known_hostile_settlement_excludes_even_a_neutral_class_trainer(self):
        c = training_client(); c.ns.guideServiceData.trainers[1].faction = 'Both'
        c.ns.travelData = c.lua.table_from({'nodes': {}, 'edges': [], 'settlements': [{
            'name': 'Enemy town', 'faction': 'Alliance', 'mapID': 501,
            'minX': .23, 'maxX': .24, 'minY': .37, 'maxY': .38}]}, recursive=True)
        self.assertEqual(c.ns.ClassTrainingDestination(c.ns.selectedRoute.stops[1]).id, 900)

    def test_flight_and_ghost_travel_retain_pending_training_without_acknowledging_it(self):
        for flag in ('UnitOnTaxi', 'UnitIsGhost'):
            c = training_client(); c.ns.UpdateNavigation()
            c.lua.execute(f'function {flag}()return true end')
            self.assertEqual(c.ns.ClassTrainingDestination(c.ns.selectedRoute.stops[1]).id, 900)
            self.assertFalse(c.ns.FinishClassTraining(True))
            self.assertIsNotNone(c.ns.db.classTraining[c.ns.self].pending)
            c.lua.execute(f'function {flag}()return false end')
            c.ns.UpdateNavigation(); self.assertEqual(c.ns.navigation.state.stop.kind, 'trainer')

    def test_invalid_saved_state_is_repaired_inside_addon_loaded(self):
        c = training_client(Client(quests=(), saved_variables={'classTraining': {'Alice-TestRealm': {
            'checked': 'bad', 'declined': -1, 'pending': {'id': False}}}}))
        state = c.ns.db.classTraining[c.ns.self]
        self.assertEqual(state.checked, 0); self.assertEqual(state.declined, 0)
        self.assertIsNone(state.pending)
        c.ns.UpdateNavigation(); self.assertEqual(c.ns.navigation.state.stop.kind, 'trainer')

    def test_shipped_class_trainers_include_new_forever_locations_and_known_ownership_only(self):
        c = Client(); data = list(c.ns.guideServiceData.trainers.values())
        meta = json.loads((ROOT / 'WowTogether/GuideServiceData.json').read_text())
        self.assertEqual(len(data), meta['class_trainer_locations'])
        self.assertEqual(len(data), 151)
        self.assertEqual({p.classID for p in data}, {1, 2, 3, 4, 5, 7, 8, 9, 11})
        self.assertTrue({1411, 1412, 1420, 1453, 1454, 1458, 2521}.issubset({p.mapID for p in data}))
        for place in data:
            self.assertTrue(c.ns.ValidTravelPoint(place))
            self.assertIn(place.faction, ('Horde', 'Alliance', 'Both'))
            self.assertNotIn('spell', place.name.lower())


if __name__ == '__main__':
    unittest.main()
