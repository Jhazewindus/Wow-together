"""Fixed catalogue order, honest full previews and tentative local learning.

Lua 5.1 host fixtures verify logic, not native Forever API/rendering behavior.
"""
import json
import unittest
from test_addon import Client
from test_050 import solo
from test_061 import world_quest, run_plan, selected
from test_routes import catalogue, map_canvas


def guide_client(count=9):
    c = solo(); map_canvas(c)
    catalogue(c, {900 + i: world_quest('Quest ' + str(i)) for i in range(count)})
    return c


def zone(c):
    return next(g for g in c.ns.LevelingGuideChoices().values() if g.mode == 'zone')


def order(guide):
    return [(s.id, s.kind, s.mapID, s.x, s.y) for s in guide.fixedPlan.values()]


def learner():
    c = guide_client(2)
    c.lua.execute("function UnitClass() return 'Shaman','SHAMAN',7 end; function UnitRace() return 'Orc','Orc',2 end; function UnitGUID() return 'Creature-0-1-2-3-123-ABC' end")
    c.ns.ReadProfile()
    for id in (900, 901): c.ns.catalogue.quests[id].starts[1].entityID = 123
    return c


def offers(c, ids, full=True):
    c.ns.RecordNPCOfferAvailability(c.lua.table_from([{'questID': id} for id in ids], recursive=True), full)


def learn(c, full=True, level_change=False):
    c.ns.active[900] = 'Quest 0'
    offers(c, [900], full)
    c.ns.handlers.QUEST_TURNED_IN(900)
    c.ns.active[900] = None
    c.lua.globals().finished[900] = True
    if level_change: c.lua.globals().playerLevel = 13
    offers(c, [901])


def primitive(value):
    if hasattr(value, 'items'): return {k: primitive(v) for k, v in value.items()}
    return value


class FixedGuideTests(unittest.TestCase):
    def test_default_generates_all_quests_without_the_trip_limit(self):
        c = guide_client(26); g = zone(c)
        self.assertTrue(g.fixedRoute)
        c.ns.ShowGuideOnMap(g)
        self.assertEqual(c.ns.navigation.state.status, 'Loading route…')
        run_plan(c)
        self.assertEqual(len(g.fixedPlan), 78)
        self.assertEqual(len(c.ns.selectedRoute.stops), 78)
        self.assertEqual({s.id for s in g.fixedPlan.values()}, set(range(900, 926)))
        for id in range(900, 926):
            self.assertEqual([s.kind for s in g.fixedPlan.values() if s.id == id], ['a', 'q', 't'])

    def test_same_order_with_different_locations_levels_and_logs(self):
        a, b = guide_client(), guide_client()
        b.ns.profile.level = 19
        b.lua.execute("C_Map.GetPlayerMapPosition=function() return {GetXY=function() return .9,.9 end} end")
        b.ns.active[902] = 'Quest 2'; b.lua.globals().finished[900] = True
        ga, gb = zone(a), zone(b)
        a.ns.BuildGuideRoute(ga, False); b.ns.BuildGuideRoute(gb, False)
        self.assertEqual(order(ga), order(gb))

    def test_accept_abandon_turn_in_and_scan_keep_the_compiled_order(self):
        c = guide_client(2); g = zone(c)
        c.ns.ShowGuideOnMap(g); run_plan(c)
        before = order(g)
        c.lua.execute("entries={{questID=900,title='Quest 0',isHeader=false}}")
        c.ns.SyncNow(False); c.drain()
        self.assertEqual(order(c.ns.routeSelection), before)
        c.lua.execute('entries={}; C_Map.GetPlayerMapPosition=function() return {GetXY=function() return .8,.8 end} end')
        c.ns.ScanGuideProgress(); c.drain()
        self.assertEqual(order(c.ns.routeSelection), before)
        self.assertIsNone(c.ns.routePlanning)
        c.lua.globals().finished[900] = True; c.ns.handlers.QUEST_TURNED_IN(900); c.drain()
        self.assertEqual(order(c.ns.routeSelection), before)
        self.assertNotIn(900, {s.id for s in c.ns.selectedRoute.stops.values()})

    def test_prerequisite_hand_in_precedes_pickup_and_future_preview_is_locked(self):
        c = guide_client(2); c.ns.catalogue.quests[901].previousQuest = 900
        g = zone(c); route = c.ns.BuildGuideRoute(g, False)
        ops = [(s.id, s.kind) for s in g.fixedPlan.values()]
        self.assertLess(ops.index((900, 't')), ops.index((901, 'a')))
        self.assertEqual({s.id for s in route.previewStops.values()}, {900})
        c.lua.globals().finished[900] = True
        self.assertIn(901, {s.id for s in c.ns.BuildGuideRoute(g, False).previewStops.values()})

    def test_full_route_and_focus_toggle_cover_all_eligible_quests(self):
        c = guide_client(12)
        for i in range(12): c.ns.catalogue.quests[900 + i].objectives[1].x = .3 + i * .04
        g = zone(c); route = c.ns.BuildGuideRoute(g, False)
        c.ns.db.config.fullRoute = True
        self.assertEqual({s.id for s in c.ns.RouteDisplayStops(route).values()}, set(range(900, 912)))
        self.assertEqual(len(c.ns.RouteDisplayStops(route)), 36)
        c.ns.db.config.fullRoute = False
        self.assertLess(len(c.ns.RouteDisplayStops(route)), 36)
        self.assertEqual(len(g.fixedPlan), 36)

    def test_adaptive_full_preview_also_has_no_six_quest_limit(self):
        c = guide_client(12); c.ns.db.config.fixedZoneGuides = False
        route = c.ns.BuildGuideRoute(zone(c), False)
        self.assertEqual(route.tripQuests, 6)
        c.ns.db.config.fullRoute = True
        self.assertEqual({s.id for s in c.ns.RouteDisplayStops(route).values()}, set(range(900, 912)))

    def test_unknown_locations_are_counted_and_do_not_invent_destinations(self):
        c = guide_client(2)
        q = c.ns.catalogue.quests[900]; q.starts, q.objectives, q.ends = None, None, None
        g = zone(c); route = c.ns.BuildGuideRoute(g, False)
        self.assertEqual(g.coverage.pickups, 1)
        self.assertGreater(route.missing, 0)
        self.assertTrue(any(s.unknownLocation for s in g.fixedPlan.values()))
        self.assertTrue(all(s.x is not None and s.y is not None for s in route.previewStops.values()))

    def test_missing_location_can_be_skipped_without_changing_the_full_order(self):
        c = guide_client(2)
        for q in c.ns.catalogue.quests.values(): q.starts, q.objectives, q.ends = None, None, None
        g = zone(c); c.ns.ShowGuideOnMap(g); run_plan(c)
        before = order(g)
        self.assertTrue(c.ns.navigation.skipQuest.enabled)
        c.ns.SkipGuide('quest')
        self.assertTrue(c.ns.GuideQuestSkipped(900))
        self.assertEqual(order(c.ns.routeSelection), before)
        self.assertEqual(c.ns.selectedRoute.pendingStop.id, 901)

    def test_quest_cannot_become_a_turn_in_until_ready(self):
        c = guide_client(2); g = zone(c)
        c.ns.active[900] = 'Quest 0'; c.ns.active[901] = 'Quest 1'
        for q in c.ns.catalogue.quests.values(): q.objectives = None
        c.ns.BuildGuideRoute(g, False)
        # Skipping an objective does not assert a completed quest.
        for s in g.fixedPlan.values():
            if s.kind == 'q':
                c.ns.db.guideSkips[c.ns.self].steps[s.id] = c.lua.table_from({c.ns.GuideStepKey(s): True})
        route = c.ns.BuildGuideRoute(g, False)
        self.assertEqual(len(route.stops), 0)
        self.assertIn('before handing it in', route.pendingReason)

    def test_full_preview_can_draw_remote_map_without_connecting_zone_gaps(self):
        c = guide_client(2)
        for p in c.ns.catalogue.quests[901].starts.values(): p.mapID = 502
        for p in c.ns.catalogue.quests[901].objectives.values(): p.mapID = 502
        for p in c.ns.catalogue.quests[901].ends.values(): p.mapID = 502
        g = zone(c); c.ns.ShowGuideOnMap(g); run_plan(c)
        c.ns.db.config.fullRoute = True
        c.lua.globals().WorldMapFrame.SetMapID(c.lua.globals().WorldMapFrame, 502)
        c.ns.DrawRoute()
        self.assertGreater(c.ns.routeStats.pins, 0)
        self.assertIn('map 502', c.ns.routeStats.status)

    def test_follow_invite_keeps_fixed_mode_even_when_recipient_prefers_adaptive(self):
        c = guide_client(26)
        c.lua.globals().grouped = True
        c.unit_names({'player': ['Alice', 'TestRealm'], 'party1': ['Bob', 'TestRealm']})
        c.ns.db.config.fixedZoneGuides = False
        for part, ids in enumerate((range(900, 908), range(908, 916), range(916, 920)), 1):
            c.receive('1|V|7|' + str(part) + '|3|zone|501|900|' + ','.join(map(str, ids))
                + '|level-zone:kalimdor/test-coast|11|20|fixed')
        invite = c.ns.partyRoutePrompt.invite
        self.assertTrue(invite.fixedRoute)
        g = c.ns.BuildInvitedGuide(invite)
        self.assertTrue(g.fixedRoute)
        self.assertEqual(len(g.records), 26)

    def test_party_markers_wait_for_the_last_participant(self):
        c = guide_client(2)
        c.lua.globals().grouped = True
        c.unit_names({'player': ['Alice', 'TestRealm'], 'party1': ['Bob', 'TestRealm']})
        c.ns.members['Bob-TestRealm'] = c.lua.table_from({'active': {900: 'Quest 0'},
            'profile': {'level': 12, 'mapID': 501, 'faction': 'Horde'},
            'activeRevision': 2, 'completionRevision': 2, 'historyRevision': 2,
            'historyChecked': {900: True, 901: True}, 'completed': {}}, recursive=True)
        c.lua.globals().finished[900] = True
        route = c.ns.BuildGuideRoute(zone(c), False)
        self.assertIn(900, {s.id for s in route.stops.values()})
        self.assertEqual(next(s for s in route.stops.values() if s.id == 900).memberKey, 'Bob-TestRealm')


class ClientQuestLineProbeTests(unittest.TestCase):
    def test_public_fields_and_optional_membership_ids_are_copyable(self):
        c = guide_client(2)
        c.lua.execute("""C_QuestLine = {
          GetAvailableQuestLines=function() return {{questLineID=77,questLineName='Native line',
              questID=900,questName='Native quest',x=.2,y=.3,isHidden=false,isCampaign=false}} end,
          GetQuestLineQuests=function(id) assert(id==77); return {900,901} end} """)
        c.ns.ShowQuestLineReport()
        text = c.ns.diagnosticsText.text
        self.assertIn('Native line', text); self.assertIn('GetQuestLineQuests IDs: 900,901', text)
        self.assertIn('isCampaign: false', text)
        self.assertIn('No prerequisite order is inferred', text)

    def test_empty_missing_and_restricted_results_do_not_become_negative_pickup_evidence(self):
        c = guide_client(2); c.ns.ShowQuestLineReport()
        self.assertIn('missing', c.ns.diagnosticsText.text)
        c.lua.execute('C_QuestLine={GetAvailableQuestLines=function() return {} end}')
        c.ns.ShowQuestLineReport(); self.assertIn('empty table', c.ns.diagnosticsText.text)
        c.lua.execute('C_QuestLine.GetAvailableQuestLines=function() return {{questLineID=secret,questName=secret,x=secret}} end')
        c.ns.ShowQuestLineReport(); self.assertIn('restricted', c.ns.diagnosticsText.text)
        self.assertTrue(c.ns.CatalogueAllowed(900, c.ns.profile, c.ns.self))


class ObservedLearningTests(unittest.TestCase):
    def test_one_clear_hand_in_pair_learns_a_tentative_dependency(self):
        c = learner(); learn(c)
        rule = c.ns.LearnedQuestRule(901)
        self.assertEqual(rule.previousQuest, 900)
        self.assertTrue(rule.tentative)
        self.assertIn('Alice', rule.sourceCharacter)
        c.lua.globals().finished[900] = False; c.ns.InvalidateNPCOffers()
        allowed, reason = c.ns.CatalogueAllowed(901, c.ns.profile, c.ns.self)
        self.assertFalse(allowed); self.assertIn('Observed by', reason)
        self.assertEqual(list(c.ns.CataloguePrerequisiteIDs(901).values()), [900])

    def test_partial_npc_list_and_acceptance_never_imply_absence_or_unlock(self):
        c = learner(); learn(c, full=False)
        self.assertIsNone(c.ns.LearnedQuestRule(901))
        c = learner(); c.ns.active[900] = 'Quest 0'; offers(c, [900])
        c.ns.handlers.QUEST_ACCEPTED(1, 900); offers(c, [901])
        self.assertIsNone(c.ns.LearnedQuestRule(901))

    def test_level_changes_are_recorded_for_review_but_not_applied(self):
        c = learner(); learn(c, level_change=True)
        self.assertIsNone(c.ns.LearnedQuestRule(901))
        finding = json.loads(c.ns.ExportGuideFindings())['findings'][0]
        self.assertTrue(finding['ambiguous'])

    def test_known_alternative_prerequisites_are_never_narrowed(self):
        c = learner(); c.ns.catalogue.quests[901].prerequisiteAny = c.lua.table_from([900, 902])
        learn(c); c.lua.globals().finished[900] = False; c.lua.globals().finished[902] = True
        c.ns.InvalidateNPCOffers()
        self.assertTrue(c.ns.CatalogueAllowed(901, c.ns.profile, c.ns.self))
        self.assertEqual(list(c.ns.CataloguePrerequisiteIDs(901).values()), [900, 902])

    def test_contradictory_positive_offer_disables_a_tentative_rule(self):
        c = learner(); learn(c)
        c.lua.globals().finished[900] = False; offers(c, [901], full=False)
        self.assertIsNone(c.ns.LearnedQuestRule(901))
        self.assertTrue(json.loads(c.ns.ExportGuideFindings())['findings'][0]['disabled'])

    def test_multiple_hand_ins_and_other_accepted_quests_do_not_identify_one_parent(self):
        c = learner(); c.ns.active[900] = 'Quest 0'; offers(c, [900])
        c.ns.handlers.QUEST_TURNED_IN(900); c.ns.handlers.QUEST_TURNED_IN(999)
        c.lua.globals().finished[900] = True; c.ns.active[900] = None; offers(c, [901])
        self.assertIsNone(c.ns.LearnedQuestRule(901))
        c = learner(); c.ns.active[900] = 'Quest 0'; offers(c, [900])
        c.ns.handlers.QUEST_TURNED_IN(900); c.lua.globals().finished[900] = True
        c.ns.active[900] = None; c.ns.active[999] = 'Other accepted quest'; offers(c, [901])
        self.assertIsNone(c.ns.LearnedQuestRule(901))

    def test_repeatable_and_multiple_giver_rules_do_not_gate_new_characters(self):
        c = learner(); c.ns.catalogue.quests[901].repeatable = True; learn(c)
        self.assertIsNone(c.ns.LearnedQuestRule(901))
        c = learner(); c.ns.catalogue.quests[901].starts[2] = c.lua.table_from({'npc': True, 'entityID': 124})
        learn(c); self.assertIsNone(c.ns.LearnedQuestRule(901))

    def test_export_findings_include_proofs_but_names_are_explicitly_optional(self):
        c = learner(); learn(c)
        text = c.ns.ExportGuideFindings(); data = json.loads(text)
        self.assertEqual(data['format'], 'wow-together-guide-findings')
        self.assertEqual(len(data['findings'][0]['proofs']), 1)
        self.assertNotIn('Alice', text); self.assertNotIn('TestRealm', text)
        c.ns.db.config.exportCharacterNames = True
        self.assertIn('Alice', c.ns.ExportGuideFindings())
        self.assertNotIn('Alice', c.ns.ExportQuestResearch())
        c.ns.settings.findingsExport.OnClick()
        self.assertIn('Guide findings export', c.ns.diagnosticsWindow.title.text)

    def test_account_wide_rules_survive_reload_and_match_build_class_race(self):
        c = learner(); learn(c)
        saved = primitive(c.ns.db)
        fresh = Client(name='Fresh', quests=(), saved_variables=saved)
        fresh.guide_environment(level=12); fresh.lua.globals().grouped = False
        fresh.lua.execute("function UnitClass() return 'Shaman','SHAMAN',7 end; function UnitRace() return 'Orc','Orc',2 end")
        catalogue(fresh, {900: world_quest('Quest 0'), 901: world_quest('Quest 1')})
        fresh.ns.catalogue.quests[901].starts[1].entityID = 123
        fresh.ns.ReadProfile()
        self.assertEqual(fresh.ns.LearnedQuestRule(901).previousQuest, 900)
        allowed = fresh.ns.CatalogueAllowed(901, fresh.ns.profile, fresh.ns.self)
        self.assertFalse(allowed[0])
        fresh.ns.profile.classID = 8; self.assertIsNone(fresh.ns.LearnedQuestRule(901))
        fresh.ns.profile.classID = 7; fresh.ns.profile.raceID = 8; self.assertIsNone(fresh.ns.LearnedQuestRule(901))
        fresh.ns.profile.raceID = 2
        fresh.lua.execute("function GetBuildInfo() return '1.60.1','70205','test',16001 end")
        self.assertIsNone(fresh.ns.LearnedQuestRule(901))

    def test_live_offer_overrides_learned_rule_and_learning_toggle_keeps_capture(self):
        c = learner(); learn(c); c.lua.globals().finished[900] = False; c.ns.InvalidateNPCOffers()
        c.ns.offered[901] = True
        self.assertTrue(c.ns.CatalogueAllowed(901, c.ns.profile, c.ns.self))
        c.ns.offered[901] = None; c.ns.db.config.useLearnedQuests = False
        self.assertTrue(c.ns.CatalogueAllowed(901, c.ns.profile, c.ns.self))
        self.assertTrue(c.ns.Option('recordQuestData'))

    def test_unknown_or_truncated_history_never_creates_a_dependency(self):
        for truncated in (True, False):
            c = learner(); c.ns.active[900] = 'Quest 0'; offers(c, [900])
            before = c.ns.db.questResearch[c.ns.self].events[1]
            if truncated: before.historyTruncated = True
            else: before.notCompleted = c.lua.table_from([900])
            c.ns.handlers.QUEST_TURNED_IN(900); c.ns.active[900] = None
            c.lua.globals().finished[900] = True; offers(c, [901])
            self.assertIsNone(c.ns.LearnedQuestRule(901))

    def test_reputation_notifications_are_not_presented_as_actual_standing(self):
        c = learner(); c.ns.active[900] = 'Quest 0'; offers(c, [900])
        c.ns.handlers.UPDATE_FACTION(); c.ns.handlers.QUEST_TURNED_IN(900)
        c.ns.active[900] = None; c.lua.globals().finished[900] = True; offers(c, [901])
        self.assertTrue(json.loads(c.ns.ExportGuideFindings())['findings'][0]['reputationNotification'])
        self.assertTrue(c.ns.LearnedQuestRule(901).tentative)

    def test_a_learned_cycle_is_disabled(self):
        c = learner(); c.ns.catalogue.quests[900].previousQuest = 901
        learn(c)
        self.assertIsNone(c.ns.LearnedQuestRule(901))
        finding = json.loads(c.ns.ExportGuideFindings())['findings'][0]
        self.assertTrue(finding['disabled']); self.assertIn('cycle', finding['reason'])
