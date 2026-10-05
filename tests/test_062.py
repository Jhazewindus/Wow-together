"""Synthetic Lua 5.1 pickup rules; host tests do not certify live beta APIs."""
import unittest
from test_addon import Client
from test_050 import solo
from test_056 import dialog_client
from test_061 import selected, world_quest, run_plan
from test_routes import catalogue, guide, map_canvas


def allowed(c, id, key=None):
    key = key or c.ns.self
    profile = c.ns.profile if key == c.ns.self else c.ns.members[key].profile
    result = c.ns.CatalogueAllowed(id, profile, key)
    return result[0] if isinstance(result, tuple) else result


def client():
    c = solo(); map_canvas(c)
    catalogue(c, {900: world_quest('First'), 901: world_quest('Next', previousQuest=900),
                  902: world_quest('Independent')})
    c.lua.execute('''
    function IsPushableQuest() error('sharing must not gate pickups') end
    C_QuestLog.IsPushableQuest=IsPushableQuest
    function IsQuestCompletable() error('turn-in dialog must not gate pickups') end
    ''')
    return c


def peer(c):
    key = 'Bob-TestRealm'
    c.ns.members[key] = c.lua.table_from({'profile': c.ns.profile, 'active': {},
        'activeRevision': 7, 'completionRevision': 8, 'historyRevision': 8,
        'completed': {}, 'historyChecked': {900: True, 901: True, 902: True},
        'offered': {901: True}, 'offerRevision': 9}, recursive=True)
    return key, c.ns.members[key]


class UniversalPickupTests(unittest.TestCase):
    def test_unfinished_prerequisite_is_not_unlocked_by_acceptance_or_ready_status(self):
        c = client()
        self.assertFalse(allowed(c, 901))
        c.ns.active[900] = 'First'; c.ns.readyToTurnIn[900] = True
        self.assertFalse(allowed(c, 901))
        c.lua.globals().finished[900] = True
        self.assertTrue(allowed(c, 901))

    def test_alternatives_need_one_real_completion_and_unknown_history_stays_unknown(self):
        c = client()
        c.ns.catalogue.quests[901].previousQuest = None
        c.ns.catalogue.quests[901].prerequisiteAny = c.lua.table_from([900, 902])
        self.assertFalse(allowed(c, 901))
        c.lua.execute('originalCompleted=C_QuestLog.IsQuestFlaggedCompleted; C_QuestLog.IsQuestFlaggedCompleted=function(id) if id==900 then return secret end return originalCompleted(id) end')
        self.assertIsNone(allowed(c, 901))
        self.assertEqual(len(c.ns.RouteStages(c.ns.CatalogueRecord(901), c.ns.self)), 0)
        c.lua.globals().finished[902] = True
        self.assertTrue(allowed(c, 901))

    def test_npc_offer_cannot_bypass_a_known_unfinished_or_restricted_prerequisite(self):
        c = client(); c.ns.offered[901] = True
        self.assertEqual(len(c.ns.RouteStages(c.ns.CatalogueRecord(901), c.ns.self)), 0)
        c.lua.execute('originalCompleted=C_QuestLog.IsQuestFlaggedCompleted; C_QuestLog.IsQuestFlaggedCompleted=function(id) if id==900 then return secret end return originalCompleted(id) end')
        self.assertIsNone(allowed(c, 901))
        self.assertEqual(len(c.ns.RouteStages(c.ns.CatalogueRecord(901), c.ns.self)), 0)
        c.lua.execute('C_QuestLog.IsQuestFlaggedCompleted=originalCompleted')
        c.lua.globals().finished[900] = True
        self.assertGreater(len(c.ns.RouteStages(c.ns.CatalogueRecord(901), c.ns.self)), 0)

    def test_every_route_mode_excludes_locked_pickups(self):
        for mode in ('normal', 'zone', 'chain', 'bundle', 'circuit', 'dungeon'):
            with self.subTest(mode=mode):
                c = client()
                g = selected(c, (900, 901, 902)) if mode in ('zone', 'chain') else guide(c, (900, 901, 902))
                g.mode, g.mapID = mode, 501
                if mode == 'bundle': g.pickupIDs = c.lua.table_from({900: True, 901: True, 902: True})
                route = c.ns.BuildGuideRoute(g, False)
                self.assertNotIn(901, {s.id for s in route.stops.values()})
                self.assertIn(902, {s.id for s in route.stops.values()})

    def test_sharing_and_open_dialog_flags_cannot_affect_any_pickup(self):
        c = client()
        for flag in ('true', 'false', 'nil', 'secret'):
            with self.subTest(flag=flag):
                c.lua.execute(f'function IsPushableQuest() return {flag} end; C_QuestLog.IsPushableQuest=IsPushableQuest; function IsQuestCompletable() return {flag} end')
                self.assertTrue(allowed(c, 900))
                self.assertFalse(allowed(c, 901))
        c = client()
        c.ns.ShowGuideOnMap(selected(c)); run_plan(c)
        self.assertEqual({s.id for s in c.ns.selectedRoute.stops.values()}, {900})

    def test_live_offer_confirms_missing_metadata_after_known_requirements(self):
        c = client(); c.ns.catalogue.detailSource = 'partial detail fixture'
        self.assertIsNone(allowed(c, 900))
        c.ns.offered[900] = True
        self.assertTrue(allowed(c, 900))
        c.ns.offered[901] = True
        self.assertFalse(allowed(c, 901))
        c.lua.globals().finished[900] = True
        self.assertTrue(allowed(c, 901))

    def test_unverified_branches_need_actual_offer_and_known_history(self):
        c = client(); c.ns.catalogue.quests[901].prerequisitesUnverified = True
        c.lua.globals().finished[900] = True
        self.assertIsNone(allowed(c, 901))
        c.ns.offered[901] = True
        self.assertTrue(allowed(c, 901))
        c.lua.globals().finished[900] = False
        self.assertFalse(allowed(c, 901))

    def test_actual_npc_absence_blocks_until_progress_invalidates_it(self):
        c = client()
        for id in (900, 901): c.ns.catalogue.quests[id].starts[1].entityID = 123
        c.lua.execute("function UnitGUID() return 'Creature-0-1-2-3-123-ABC' end")
        c.ns.RecordNPCOfferAvailability(c.lua.table_from([{'questID': 900}], recursive=True))
        self.assertFalse(allowed(c, 901))
        c.lua.globals().finished[900] = True
        self.assertFalse(allowed(c, 901))
        c.ns.handlers.QUEST_TURNED_IN(900)
        self.assertTrue(allowed(c, 901))
        c.ns.RecordNPCOfferAvailability(c.lua.table_from([{'questID': 901}], recursive=True))
        self.assertTrue(c.ns.PickupOfferEvidence(c.ns.self, 901))

    def test_turn_in_unlocks_the_retained_full_guide_without_manual_scan(self):
        c = client(); c.ns.ShowGuideOnMap(selected(c)); run_plan(c)
        self.assertEqual({s.id for s in c.ns.selectedRoute.stops.values()}, {900})
        c.lua.globals().finished[900] = True
        c.ns.handlers.QUEST_TURNED_IN(900); c.drain()
        self.assertEqual({s.id for s in c.ns.selectedRoute.stops.values()}, {901})
        self.assertEqual(c.ns.selectedRoute.stops[1].kind, 'a')
        self.assertEqual(len(c.ns.routeSelection.records), 2)

    def test_accepted_objectives_and_turn_ins_are_not_removed_by_pickup_rules(self):
        c = client(); c.ns.active[901] = 'Next'
        self.assertEqual(c.ns.RouteStages(c.ns.CatalogueRecord(901), c.ns.self)[1].kind, 'q')
        c.ns.readyToTurnIn[901] = True
        self.assertEqual(c.ns.RouteStages(c.ns.CatalogueRecord(901), c.ns.self)[1].kind, 't')

    def test_positive_offer_cannot_override_faction_or_level(self):
        c = client(); c.ns.offered[900] = True
        c.ns.catalogue.quests[900].side = 'Alliance'
        self.assertFalse(allowed(c, 900))
        c.ns.catalogue.quests[900].side = 'Horde'; c.ns.catalogue.quests[900].minLevel = 50
        self.assertFalse(allowed(c, 900))

    def test_invalidated_legacy_pickup_clears_markers_but_retains_selection(self):
        c = client(); c.ns.ShowGuideOnMap(guide(c))
        self.assertGreater(c.ns.routeStats.pins, 0)
        c.ns.catalogue.quests[900].previousQuest = 899
        c.ns.Refresh()
        self.assertIsNotNone(c.ns.routeSelection)
        self.assertEqual(len(c.ns.selectedRoute.stops), 0)
        self.assertEqual(c.ns.routeStats.pins, 0)

    def test_optional_auto_selection_cannot_reopen_locked_cached_pickup(self):
        c = client(); c.ns.db.config.autoSelectQuests = True
        c.ns.selectedRoute = c.lua.table_from({'stops': [{'id': 901, 'kind': 'a'}]}, recursive=True)
        c.ns.offered[901] = True
        c.lua.execute('C_GossipInfo={SelectAvailableQuest=function(id) selectedQuest=id end}')
        c.ns.AutoSelectGuideQuest()
        self.assertIsNone(c.lua.globals().selectedQuest)
        c.lua.globals().finished[900] = True; c.ns.AutoSelectGuideQuest()
        self.assertEqual(c.lua.globals().selectedQuest, 901)

    def test_diagnostics_show_per_quest_requirement_and_offer_evidence(self):
        c = client(); c.ns.routeSelection = selected(c)
        c.ns.Diagnostics()
        text = c.ns.diagnosticsText.text
        self.assertIn('sharing only', text)
        self.assertIn('opened-dialog turn-in only', text)
        self.assertIn('Next (901; NPC not checked): Finish First first.', text)
        self.assertIn('hidden requirements may still need NPC confirmation', text)


class CharacterEvidenceTests(unittest.TestCase):
    def test_each_character_requires_their_own_chain_completion(self):
        c = client(); key, member = peer(c)
        c.lua.globals().finished[900] = True
        self.assertTrue(allowed(c, 901)); self.assertFalse(allowed(c, 901, key))
        c.lua.globals().finished[900] = False; member.completed[900] = True
        self.assertFalse(allowed(c, 901)); self.assertTrue(allowed(c, 901, key))
        member.completed[900] = None; member.historyChecked[900] = None
        self.assertIsNone(allowed(c, 901, key))

    def test_peer_offer_is_not_reused_after_log_changes_or_reload(self):
        c = client(); key, member = peer(c)
        c.ns.catalogue.detailSource = 'partial'; member.completed[900] = True
        self.assertTrue(allowed(c, 901, key))
        member.activeRevision = 10
        self.assertIsNone(c.ns.PickupOfferEvidence(key, 901)); self.assertIsNone(allowed(c, 901, key))
        member.offerRevision = 11; member.syncPending = True
        self.assertIsNone(allowed(c, 901, key))

    def test_retired_sharing_packets_cannot_override_chain_history(self):
        c = Client(quests=()); c.guide_environment(level=12)
        catalogue(c, {900: world_quest('First'), 901: world_quest('Next', previousQuest=900)})
        key, member = peer(c); accepted = c.ns.syncStats.accepted
        c.receive('1|E|7|99|1|1|1|901:1')
        self.assertEqual(c.ns.syncStats.accepted, accepted)
        self.assertFalse(allowed(c, 901, key))

    def test_old_pickup_setting_is_removed_without_resetting_other_config(self):
        c = Client(quests=(), saved_variables={'config': {'betaPickupCheck': True, 'autoAccept': True}})
        self.assertIsNone(c.ns.db.config.betaPickupCheck)
        self.assertTrue(c.ns.Option('autoAccept'))

    def test_completion_api_is_called_only_for_opened_turn_in_without_arguments(self):
        c = dialog_client(); c.ns.db.config.autoTurnIn = True
        c.lua.execute("function IsQuestCompletable(...) assert(select('#', ...)==0); return true end")
        c.ns.handlers.QUEST_PROGRESS()
        self.assertEqual(c.lua.globals().progressCalls, 1)


if __name__ == '__main__':
    unittest.main()
