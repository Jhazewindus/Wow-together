"""Personal dungeon thresholds, partial geography and comparable skip exports.

Lua 5.1 host fixtures verify logic; actual beta offers still need live testing.
"""
import json
import unittest
from test_addon import Client
from test_routes import catalogue, guide, map_canvas, quest, route_client
from test_050 import solo, dungeon
from test_063 import guide_client, zone, order, offers


def collection(c):
    data = {900: quest('Early pickup', minLevel=5, categoryPath='dungeons/test-cavern'),
            901: quest('Last pickup', minLevel=15, level=18, categoryPath='dungeons/test-cavern')}
    catalogue(c, data)
    c.ns.SetOption('zonePrompts', False)
    return c.ns.DungeonGroups()[1]


def tick(c, level=None):
    if level is not None:
        c.lua.globals().playerLevel = level
        c.ns.ReadProfile()
    c.ns.ScheduleActivitySuggestions()
    c.drain()


class FullDungeonCollectionTests(unittest.TestCase):
    def test_popup_waits_for_highest_pickup_level_not_first_or_display_level(self):
        c = solo(); group = collection(c)
        tick(c, 14)
        self.assertIsNone(c.ns.activityPrompt)
        tick(c, 15)
        self.assertTrue(c.ns.activityPrompt.IsShown(c.ns.activityPrompt))
        self.assertIn('pickup level: 15', c.ns.activityPrompt.text.text)
        self.assertIn('Prerequisite hand-ins', c.ns.activityPrompt.text.text)
        self.assertEqual(c.ns.DungeonCollectionReadiness(group).count, 2)

    def test_other_identity_repeatables_professions_do_not_raise_threshold(self):
        c = solo()
        c.ns.profile.classID, c.ns.profile.raceID = 7, 2
        c.lua.globals().pyBand = lambda a, b: int(a) & int(b)
        c.lua.globals().pyShift = lambda a, b: int(a) << int(b)
        c.lua.execute('bit={band=function(a,b) return pyBand(a,b) end,lshift=function(a,b) return pyShift(a,b) end}')
        data = {902: quest('Other faction', side='Alliance', minLevel=60),
                903: quest('Other class', classMask=1, minLevel=60),
                904: quest('Other race', raceMask=32, minLevel=60),
                905: quest('Repeatable', repeatable=True, minLevel=60),
                906: quest('Profession', categoryPath='professions/cooking', questType='Dungeon', minLevel=60)}
        for id, q in data.items():
            if id != 906: q['categoryPath'] = 'dungeons/test-cavern'
        c.ns.SetOption('zonePrompts', False)
        catalogue(c, {**{900: quest(minLevel=5, categoryPath='dungeons/test-cavern'),
                              901: quest(minLevel=15, level=18, categoryPath='dungeons/test-cavern')}, **data})
        group = next(g for g in c.ns.DungeonGroups().values() if g.key == 'test-cavern')
        result = c.ns.DungeonCollectionReadiness(group)
        self.assertEqual((result.count, result.pickupLevel, result.unknown), (2, 15, 0))

    def test_matching_class_quest_only_counts_when_enabled(self):
        c = solo(); group = collection(c)
        q = c.ns.catalogue.quests[901]
        q.classMask = 64
        c.ns.profile.classID = 7
        c.lua.globals().pyBand = lambda a, b: int(a) & int(b)
        c.lua.globals().pyShift = lambda a, b: int(a) << int(b)
        c.lua.execute('bit={band=function(a,b) return pyBand(a,b) end,lshift=function(a,b) return pyShift(a,b) end}')
        self.assertEqual(c.ns.DungeonCollectionReadiness(group).pickupLevel, 5)
        c.ns.SetOption('classQuests', True)
        self.assertEqual(c.ns.DungeonCollectionReadiness(group).pickupLevel, 15)

    def test_unknown_pickup_level_or_identity_does_not_claim_full_collection_ready(self):
        for missing in ('minLevel', 'side'):
            with self.subTest(missing=missing):
                c = solo(); group = collection(c)
                c.ns.catalogue.quests[901][missing] = None
                tick(c, 18)
                self.assertIsNone(c.ns.activityPrompt)
                self.assertGreater(c.ns.DungeonCollectionReadiness(group).unknown, 0)
                self.assertIn('unknown', c.ns.DungeonCollectionSummary(group))
                self.assertIsNotNone(c.ns.DungeonGuide(group))

    def test_unmapped_far_dungeon_can_prompt_without_replacing_active_guide(self):
        c = solo(); group = collection(c)
        for q in c.ns.catalogue.quests.values(): q.starts, q.objectives, q.ends = None, None, None
        c.ns.catalogue.quests[902] = c.lua.table_from(quest('Current work', level=15), recursive=True)
        c.lua.execute("entries={{questID=902,title='Current work',isHeader=false}}")
        c.ns.ReadQuests(); map_canvas(c)
        current = c.ns.CurrentQuestChoices()[1]
        c.ns.ActivateRoute(current)
        current_key = current.key
        tick(c, 15)
        self.assertTrue(c.ns.activityPrompt.IsShown(c.ns.activityPrompt))
        self.assertEqual(c.ns.routeSelection.key, current_key)
        c.ns.activityPrompt.accept.OnClick()
        self.assertTrue(c.ns.dungeonWindow.IsShown(c.ns.dungeonWindow))
        self.assertIn('Early pickup', c.ns.dungeonWindow.text.text)
        self.assertIn('Last pickup', c.ns.dungeonWindow.text.text)
        self.assertEqual(c.ns.routeSelection.key, current_key)

    def test_unsynced_party_does_not_block_personal_collection_start_or_completion(self):
        c = route_client(); map_canvas(c); group = dungeon(c)
        c.ns.SetOption('zonePrompts', False)
        tick(c)
        self.assertTrue(c.ns.activityPrompt.IsShown(c.ns.activityPrompt))
        plan = c.ns.DungeonGuide(group)
        self.assertTrue(plan.personal)
        self.assertEqual([s.kind for s in c.ns.BuildDungeonRoute(plan, True).stops.values()], ['a', 'a', 'q'])
        c.ns.RequestStartRoute(plan)
        self.assertEqual(c.ns.routeSelection.key, 'dungeon:test-cavern')
        self.assertFalse(any('|G|' in msg for _, msg, _ in c.drain()))
        c.lua.execute('finished[900]=true; finished[901]=true')
        c.ns.UpdateSelectedRoute(c.lua.table())
        self.assertTrue(c.ns.selectedRoute.complete)
        self.assertEqual(len(c.ns.selectedRoute.stops), 0)

    def test_old_early_notice_does_not_suppress_new_threshold_but_new_notice_is_once(self):
        c = solo(); group = collection(c)
        c.ns.db.activityNotices = c.lua.table()
        c.ns.db.activityNotices[c.ns.ActivityNoticeKey('dungeon:' + group.key)] = True
        tick(c, 15)
        self.assertTrue(c.ns.activityPrompt.IsShown(c.ns.activityPrompt))
        c.ns.activityPrompt.later.OnClick()
        tick(c, 16)
        self.assertFalse(c.ns.activityPrompt.IsShown(c.ns.activityPrompt))

    def test_completed_collection_never_prompts_and_pickup_level_above_display_still_can(self):
        c = solo(); group = collection(c)
        c.lua.execute('finished[900]=true; finished[901]=true')
        tick(c, 15)
        self.assertIsNone(c.ns.activityPrompt)
        c = solo(); group = collection(c)
        c.ns.catalogue.quests[901].level = 8
        tick(c, 15)
        self.assertTrue(c.ns.activityPrompt.IsShown(c.ns.activityPrompt))


class PartialObjectiveOrderTests(unittest.TestCase):
    def test_generic_partial_objective_does_not_send_hand_in_behind_distant_travel(self):
        c = solo()
        catalogue(c, {900: quest('Parent', objectiveLocationsIncomplete=True),
                      901: quest('Child', previousQuest=900),
                      902: quest('Unrelated far trip', map_id=502)})
        g = guide(c, (900, 901, 902)); g.fixedRoute = True
        c.ns.GenerateFixedGuide(g, False)
        stages = [(s.id, s.kind) for s in g.fixedPlan.values()]
        self.assertLess(stages.index((900, 't')), stages.index((901, 'a')))
        self.assertLess(stages.index((901, 'a')), stages.index((902, 'a')))
        gaps = [s for s in g.fixedPlan.values() if s.unknownLocation]
        self.assertTrue(gaps)
        self.assertTrue(all(s.x is None and s.y is None for s in gaps))
        self.assertTrue(all(s.x is not None for s in c.ns.BuildGuideRoute(g, False).previewStops.values()))

    def test_complete_missing_offer_then_new_offer_restores_generic_pickup_in_same_plan(self):
        c = guide_client(2)
        c.lua.execute("function UnitGUID() return 'Creature-0-1-2-3-123-ABC' end")
        for q in c.ns.catalogue.quests.values(): q.starts[1].entityID = 123
        c.ns.catalogue.quests[901].previousQuest = 900
        g = zone(c); c.ns.ActivateRoute(g); before = order(g)
        c.lua.globals().finished[900] = True
        offers(c, [])
        c.ns.UpdateFixedGuideRoute(g)
        self.assertEqual(c.ns.selectedRoute.pendingStop.id, 901)
        self.assertFalse(c.ns.GuideQuestSkipped(901))
        offers(c, [901])
        c.ns.UpdateFixedGuideRoute(g)
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 901)
        self.assertEqual(c.ns.selectedRoute.stops[1].kind, 'a')
        self.assertEqual(order(g), before)

    def test_manual_skip_stays_skipped_after_offer_and_does_not_change_order(self):
        c = guide_client(2)
        c.ns.catalogue.quests[901].previousQuest = 900
        g = zone(c); c.ns.ActivateRoute(g)
        c.lua.globals().finished[900] = True
        c.ns.UpdateFixedGuideRoute(g); before = order(g)
        c.ns.SkipGuide('quest')
        c.ns.offered[901] = True
        route = c.ns.BuildGuideRoute(g, False)
        self.assertNotIn(901, {s.id for s in route.previewStops.values()})
        self.assertTrue(c.ns.GuideQuestSkipped(901))
        self.assertEqual(order(g), before)

    def test_actual_full_mulgore_followup_stays_next_to_parent_hand_in(self):
        c = Client(quests=(), use_catalogue=True); c.guide_environment(level=2)
        c.lua.globals().grouped = False
        c.ns.profile.classID, c.ns.profile.raceID = 3, 6
        records = [c.ns.CatalogueRecord(id) for id, q in c.ns.catalogue.quests.items()
                   if q.categoryPath == 'kalimdor/mulgore']
        g = c.lua.table_from({'records': records}, recursive=True)
        c.ns.GenerateFixedGuide(g, False)
        stages = [(s.id, s.kind) for s in g.fixedPlan.values()]
        self.assertEqual(stages.index((750, 'a')), stages.index((747, 't')) + 1)


class SkipEvidenceTests(unittest.TestCase):
    def test_skip_records_exact_guide_step_and_level_without_learning_unlock(self):
        for kind in ('step', 'quest'):
            with self.subTest(kind=kind):
                c = guide_client(2); g = zone(c); c.ns.ActivateRoute(g)
                stop = c.ns.selectedRoute.stops[1]
                c.ns.SkipGuide(kind)
                event = json.loads(c.ns.ExportQuestResearch())['events'][-1]
                self.assertEqual(event['guideKey'], g.key)
                self.assertEqual(event['stepKey'], c.ns.GuideStepKey(stop))
                self.assertEqual(event['stepKind'], stop.kind)
                self.assertEqual(event['guideStep'], stop.guideStep)
                self.assertEqual(event['level'], 12)
                self.assertEqual(event['questID'], stop.id)
                self.assertEqual(event['addon'], c.ns.VERSION)
                self.assertEqual(json.loads(c.ns.ExportGuideFindings())['findings'], [])

    def test_invited_route_skip_exports_omit_sender_name_including_merged_routes(self):
        for prefix in ('', 'with-log:'):
            with self.subTest(prefix=prefix):
                c = guide_client(2); g = zone(c); c.ns.ActivateRoute(g)
                g.key = prefix + 'party:Private Friend-PrivateRealm:123'
                c.ns.SkipGuide('step')
                exported = c.ns.ExportQuestResearch()
                self.assertNotIn('Private Friend', exported)
                self.assertNotIn('PrivateRealm', exported)
                self.assertEqual(json.loads(exported)['events'][-1]['guideKey'], 'party-route')

    def test_restricted_metadata_is_omitted(self):
        c = guide_client(2); secret = c.lua.globals().secret
        c.ns.RecordQuestResearch('skip-step', c.lua.table_from({
            'questID': 900, 'guideKey': secret, 'stepKey': secret, 'stepKind': secret, 'guideStep': secret}))
        event = json.loads(c.ns.ExportQuestResearch())['events'][-1]
        self.assertFalse(any(key in event for key in ('guideKey', 'stepKey', 'stepKind', 'guideStep')))


class TemporaryDeferralTests(unittest.TestCase):
    def setup_guide(self, count=3):
        c = guide_client(count)
        c.lua.execute("function UnitGUID() return 'Creature-0-1-2-3-123-ABC' end")
        for q in c.ns.catalogue.quests.values(): q.starts[1].entityID = 123
        g = zone(c); c.ns.ActivateRoute(g)
        return c, g

    def test_missing_offer_defers_all_stages_then_restores_original_position_and_records_both(self):
        c, g = self.setup_guide(); before = order(g)
        offers(c, [901, 902]); c.ns.UpdateFixedGuideRoute(g)
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 901)
        self.assertNotIn(900, {s.id for s in c.ns.selectedRoute.stops.values()})
        self.assertEqual(c.ns.selectedRoute.deferredQuests, 1)
        self.assertFalse(c.ns.GuideQuestSkipped(900))
        for _ in range(4): c.ns.UpdateFixedGuideRoute(g)
        events = json.loads(c.ns.ExportQuestResearch())['events']
        deferred = [e for e in events if e['event'] == 'defer-pickup']
        self.assertEqual(len(deferred), 1)
        self.assertEqual(deferred[0]['questID'], 900)
        offers(c, [900, 901, 902]); c.ns.UpdateFixedGuideRoute(g)
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 900)
        self.assertEqual(order(g), before)
        self.assertEqual(c.ns.selectedRoute.deferredQuests, 0)
        events = json.loads(c.ns.ExportQuestResearch())['events']
        self.assertEqual([e['questID'] for e in events if e['event'] == 'restore-pickup'], [900])
        self.assertEqual(json.loads(c.ns.ExportGuideFindings())['findings'], [])

    def test_all_deferred_keeps_selected_guide_and_explains_why_it_is_waiting(self):
        c, g = self.setup_guide(); offers(c, [])
        c.ns.UpdateFixedGuideRoute(g)
        self.assertEqual(len(c.ns.selectedRoute.stops), 0)
        self.assertGreater(c.ns.selectedRoute.remainingSteps, 0)
        self.assertEqual(c.ns.routeSelection.key, g.key)
        self.assertIn('did not offer', c.ns.selectedRoute.pendingReason)
        self.assertEqual(c.ns.selectedRoute.deferredQuests, 3)

    def test_known_level_gate_defers_until_level_met_without_inventing_absence(self):
        c, g = self.setup_guide()
        c.ns.catalogue.quests[900].minLevel = 13
        c.ns.UpdateFixedGuideRoute(g)
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 901)
        self.assertFalse(c.ns.GuideQuestSkipped(900))
        self.assertFalse(any(e['event'] == 'defer-pickup' for e in json.loads(c.ns.ExportQuestResearch())['events']))
        c.lua.globals().playerLevel = 13; c.ns.ReadProfile(); c.ns.UpdateFixedGuideRoute(g)
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 900)

    def test_partial_offer_list_does_not_defer_and_active_quest_is_kept(self):
        c, g = self.setup_guide(); offers(c, [901], full=False)
        c.ns.UpdateFixedGuideRoute(g)
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 900)
        c.ns.active[900] = 'Quest 0'; offers(c, [901, 902])
        c.ns.UpdateFixedGuideRoute(g)
        self.assertIn((900, 'q'), {(s.id, s.kind) for s in c.ns.selectedRoute.stops.values()})
        self.assertEqual(c.ns.selectedRoute.deferredQuests, 0)

    def test_opening_npc_triggers_deferral_and_restoration_without_manual_scan(self):
        c, g = self.setup_guide(); before = order(g)
        c.lua.execute('nativeOffers={{questID=901,title="Quest 1"},{questID=902,title="Quest 2"}}; C_GossipInfo={GetAvailableQuests=function() return nativeOffers end}')
        c.ns.InitializeOffers()
        c.ns.handlers.GOSSIP_SHOW(); c.drain()
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 901)
        c.lua.execute('table.insert(nativeOffers,{questID=900,title="Quest 0"})')
        c.ns.handlers.GOSSIP_SHOW(); c.drain()
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 900)
        self.assertEqual(order(g), before)

    def test_preview_does_not_record_an_automatic_skip_and_observations_survive_reload(self):
        c, g = self.setup_guide(); c.ns.routeSelection = None
        offers(c, [901, 902]); c.ns.BuildFixedGuideRoute(g, False)
        self.assertFalse(any(e['event'] == 'defer-pickup' for e in json.loads(c.ns.ExportQuestResearch())['events']))
        c.ns.routeSelection = g; c.ns.UpdateFixedGuideRoute(g)
        from test_063 import primitive
        saved = primitive(c.ns.db)
        loaded = Client(quests=(), saved_variables=saved)
        events = json.loads(loaded.ns.ExportQuestResearch())['events']
        self.assertEqual([e['questID'] for e in events if e['event'] == 'defer-pickup'], [900])


if __name__ == '__main__':
    unittest.main()
