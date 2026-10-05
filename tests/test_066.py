"""Guide reload, party catch-up consent, compact public nameplate hints and UI.

Lua 5.1 fixtures validate state transitions; live map layout still needs beta testing.
"""
import json
import unittest
from test_addon import Client
from test_routes import catalogue, guide, map_canvas
from test_061 import world_quest, run_plan
from test_063 import guide_client, zone, order, primitive, learner, learn
from test_057 import mob_client


def party(complete=(900, 901), peer_complete=(), active=(), peer_active=()):
    c = Client(quests=active, completed=complete)
    c.guide_environment(level=12); map_canvas(c)
    catalogue(c, {900: world_quest('First'), 901: world_quest('Second', previousQuest=900),
                  902: world_quest('Unrelated'), 903: world_quest('Later', previousQuest=901)})
    c.receive('1|S|1|1|1|' + ','.join(map(str, peer_active)))
    c.receive('1|P|12|2|501|Test Coast')
    c.receive('1|C|2|1|1|' + ','.join(map(str, peer_complete)))
    c.receive('1|K|2|1|1|900,901,902,903')
    c.ns.db.config.dungeonPrompts = False
    c.ns.db.config.zonePrompts = False
    return c


def reload(c, completed=(), active=()):
    c.ns.handlers.PLAYER_LOGOUT()
    saved = primitive(c.lua.globals().WowTogetherDB)
    fresh = Client(quests=active, completed=completed, saved_variables=saved)
    fresh.guide_environment(level=12)
    fresh.lua.globals().grouped, fresh.lua.globals().peer = False, None
    fresh.ns.UpdateRoster()
    fresh.ns.catalogue = fresh.lua.table_from(primitive(c.ns.catalogue), recursive=True)
    map_canvas(fresh)
    fresh.ns.handlers.PLAYER_LOGIN()
    run_plan(fresh); fresh.drain()
    return fresh


class ResumeTests(unittest.TestCase):
    def test_reload_preserves_fixed_order_and_uses_current_progress_without_invitation(self):
        c = guide_client(26); g = zone(c)
        c.ns.ShowGuideOnMap(g); run_plan(c)
        before = order(g)
        fresh = reload(c, completed=(900,), active=(901,))
        self.assertEqual(fresh.ns.routeSelection.key, g.key)
        self.assertEqual(order(fresh.ns.routeSelection), before)
        self.assertEqual(len(fresh.ns.routeSelection.records), 26)
        self.assertNotIn(900, {s.id for s in fresh.ns.selectedRoute.stops.values()})
        self.assertNotIn((901, 'a'), {(s.id, s.kind) for s in fresh.ns.selectedRoute.stops.values()})
        self.assertIsNone(fresh.lua.globals().WorldMapFrame.mapID)  # No forced map opening on login.
        self.assertFalse(any(msg.startswith('1|V|') for _, msg, _ in fresh.drain()))
        self.assertNotIn('memberKey', primitive(fresh.ns.db.guideState[fresh.ns.self].guide.fixedPlan[1]))

    def test_clear_removes_only_current_char_checkpoint_and_reload_does_not_restart(self):
        c = guide_client(2); c.ns.ActivateRoute(zone(c))
        c.ns.db.guideState['Other-TestRealm'] = c.lua.table_from({'schema': 1})
        c.ns.ClearRoute()
        self.assertIsNone(c.ns.db.guideState[c.ns.self])
        self.assertIsNotNone(c.ns.db.guideState['Other-TestRealm'])
        self.assertIsNone(reload(c).ns.routeSelection)

    def test_manual_skips_survive_without_becoming_completed_credit(self):
        c = guide_client(3); c.ns.ShowGuideOnMap(zone(c)); run_plan(c)
        id = c.ns.selectedRoute.stops[1].id
        c.ns.SkipGuide('quest')
        fresh = reload(c)
        self.assertTrue(fresh.ns.GuideQuestSkipped(id))
        self.assertFalse(fresh.ns.Completed(id))
        self.assertNotIn(id, {s.id for s in fresh.ns.selectedRoute.stops.values()})

    def test_invalid_checkpoint_is_discarded_safely(self):
        c = guide_client(2); c.ns.ActivateRoute(zone(c))
        c.ns.db.guideState[c.ns.self].guide.title = None
        fresh = reload(c)
        self.assertIsNone(fresh.ns.routeSelection)
        self.assertIn('invalid', fresh.ns.guideResumeStatus)

    def test_login_in_combat_defers_until_regen(self):
        c = guide_client(2); c.ns.ActivateRoute(zone(c))
        saved = primitive(c.ns.db)
        fresh = Client(quests=(), saved_variables=saved)
        fresh.guide_environment(level=12); map_canvas(fresh)
        fresh.ns.catalogue = fresh.lua.table_from(primitive(c.ns.catalogue), recursive=True)
        fresh.lua.globals().grouped, fresh.lua.globals().peer = False, None
        fresh.ns.UpdateRoster(); fresh.lua.globals().combat = True
        fresh.ns.handlers.PLAYER_LOGIN()
        self.assertIsNone(fresh.ns.routeSelection)
        self.assertIsNotNone(fresh.ns.pendingSavedGuide)
        fresh.lua.globals().combat = False
        fresh.ns.handlers.PLAYER_REGEN_ENABLED(); run_plan(fresh)
        self.assertIsNotNone(fresh.ns.routeSelection)

    def test_outside_quest_updates_and_completed_guide_keep_controls_until_explicit_clear(self):
        c = guide_client(2); c.ns.ShowGuideOnMap(zone(c)); run_plan(c)
        key, before = c.ns.routeSelection.key, order(c.ns.routeSelection)
        c.lua.execute("entries={{questID=999,title='Outside guide',isHeader=false}}")
        c.ns.handlers.QUEST_LOG_UPDATE(); c.ns.SyncNow(False)
        self.assertEqual(c.ns.routeSelection.key, key)
        self.assertEqual(order(c.ns.routeSelection), before)
        self.assertTrue(c.ns.navigation.IsShown(c.ns.navigation))
        c.lua.execute('finished[900]=true;finished[901]=true')
        c.ns.Refresh()
        self.assertTrue(c.ns.selectedRoute.complete)
        self.assertTrue(c.ns.navigation.IsShown(c.ns.navigation))
        self.assertEqual(c.ns.routeStats.pins, 0)
        c.ns.ClearRoute(); c.ns.Refresh()
        self.assertFalse(c.ns.navigation.IsShown(c.ns.navigation))


class CatchupTests(unittest.TestCase):
    def test_completion_gaps_include_prerequisites_exclude_unrelated_quests(self):
        c = party()
        g = c.ns.PartyCatchupGuide()
        self.assertEqual({r.id for r in g.records.values()}, {900, 901})
        self.assertEqual(g.focusKey, 'Bob-TestRealm')
        self.assertTrue(g.catchup)
        self.assertFalse(g.fixedRoute)
        route = c.ns.BuildGuideRoute(g, False)
        self.assertTrue(all(s.memberKey == 'Bob-TestRealm' for s in route.stops.values()))
        self.assertFalse(any(s.id == 901 for s in route.stops.values()))  # Parent has not been handed in.
        c.receive('1|S|3|1|1|'); c.receive('1|C|4|1|1|900'); c.receive('1|K|4|1|1|900,901,902,903')
        next_route = c.ns.BuildGuideRoute(g, False)
        self.assertEqual(next_route.stops[1].id, 901)

    def test_unknown_or_stale_history_does_not_claim_progression_gaps(self):
        c = party(); peer = c.ns.members['Bob-TestRealm']
        for field, value in [('historyRevision', None), ('completionRevision', 0), ('syncPending', True)]:
            old = peer[field]; peer[field] = value
            result, reason = c.ns.PartyCatchupGuide()
            self.assertIsNone(result); self.assertIn('Waiting', reason)
            peer[field] = old
        peer.historyChecked[901] = None
        self.assertIsNone(c.ns.PartyCatchupGuide()[0])

    def test_offer_preserves_existing_guide_keep_and_accept_are_explicit(self):
        c = party(); current = guide(c, (902,))
        c.ns.ActivateRoute(current)
        self.assertTrue(c.ns.ShowPartyCatchup(None, True))
        self.assertEqual(c.ns.routeSelection.key, current.key)
        c.ns.activityPrompt.later.OnClick()
        self.assertEqual(c.ns.routeSelection.key, current.key)
        c.ns.ShowPartyCatchup(None, True); c.ns.activityPrompt.accept.OnClick(); run_plan(c)
        self.assertTrue(c.ns.routeSelection.catchup)
        self.assertFalse(c.ns.routeSelection.fixedRoute)
        self.assertTrue(any(msg.endswith('|catchup') for _, msg, _ in c.drain() if msg.startswith('1|V|')))

    def test_friends_still_choose_follow_or_keep_for_catchup_invitations(self):
        c = party(); c.ns.ActivateRoute(guide(c, (902,)))
        packet = '1|V|1|1|1|zone|501|900|900,901|level-zone:kalimdor/test-coast|1|255|catchup'
        c.receive(packet)
        self.assertTrue(c.ns.partyRoutePrompt.invite.catchup)
        self.assertEqual(c.ns.routeSelection.key, 'quest:900')
        c.ns.partyRoutePrompt.keep.OnClick()
        self.assertFalse(c.ns.routeSelection.catchup)
        c.receive(packet.replace('|V|1|', '|V|2|'))
        c.ns.partyRoutePrompt.follow.OnClick(); run_plan(c)
        self.assertTrue(c.ns.routeSelection.catchup)
        self.assertEqual({r.id for r in c.ns.routeSelection.records.values()}, {900, 901})

    def test_low_level_junk_wrong_faction_repeatables_and_professions_are_excluded(self):
        c = party()
        c.ns.catalogue.quests[900].previousQuest = None
        c.ns.catalogue.quests[901].previousQuest = None
        for change in ({'level': 1}, {'side': 'Alliance'}, {'repeatable': True}, {'categoryPath': 'professions/cooking'}):
            data = {900: world_quest('Excluded', **change), 901: world_quest('Unfinished')}
            catalogue(c, data)
            c.lua.globals().finished[901] = False
            self.assertIsNone(c.ns.PartyCatchupGuide()[0])

    def test_other_zones_use_the_same_completion_and_prerequisite_logic(self):
        c = party(); c.ns.profile.mapID = 600
        data = {900: world_quest('Parent', 'Second Zone', 600),
                901: world_quest('Child', 'Second Zone', 600, previousQuest=900),
                902: world_quest('Unrelated', 'Second Zone', 600)}
        catalogue(c, data)
        g = c.ns.PartyCatchupGuide()
        self.assertEqual(g.homeMapID, 600)
        self.assertEqual({r.id for r in g.records.values()}, {900, 901})

    def test_useful_low_level_prerequisite_is_included_and_explained(self):
        c = party(complete=(901,))
        c.ns.catalogue.quests[900].level = 1
        g = c.ns.PartyCatchupGuide()
        self.assertTrue(g.catchupTargets[901])
        self.assertTrue(g.catchupRequired[900])
        c.ns.ActivateRoute(g); c.ns.Refresh()
        self.assertIn('prerequisite', c.ns.navigation.context.text)
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 900)

    def test_alternative_completed_branch_does_not_require_other_branch(self):
        c = party(complete=(900, 901), peer_complete=(900,))
        c.ns.catalogue.quests[901].previousQuest = None
        c.ns.catalogue.quests[901].prerequisiteAny = c.lua.table_from([900, 902])
        g = c.ns.PartyCatchupGuide()
        self.assertEqual({r.id for r in g.records.values()}, {901})
        self.assertEqual(c.ns.BuildGuideRoute(g, False).stops[1].id, 901)

    def test_missing_history_requests_retry_on_manual_sync_and_include_recursive_ancestors(self):
        c = party(); peer = c.ns.members['Bob-TestRealm']
        peer.historyChecked = c.lua.table()
        records = c.lua.table_from([c.ns.CatalogueRecord(903)])
        c.ns.RequestCatchupHistory(records)
        messages = [msg for _, msg, _ in c.drain() if msg.startswith('1|Y|')]
        self.assertTrue(any('900' in msg and '901' in msg for msg in messages))
        c.ns.RequestCatchupHistory(records)
        self.assertFalse(any(msg.startswith('1|Y|') for _, msg, _ in c.drain()))
        c.ns.SyncNow(True); c.ns.RequestCatchupHistory(records)
        self.assertTrue(any(msg.startswith('1|Y|') for _, msg, _ in c.drain()))

    def test_history_request_and_route_plan_bounds(self):
        c = party()
        catalogue(c, {i: world_quest(str(i)) for i in range(1000, 1514)})
        c.ns.ResetCatchupHistory()
        for first in range(1000, 1504, 18):
            c.receive('1|Y|' + ','.join(map(str, range(first, min(first + 18, 1504)))))
        self.assertEqual(len(list(c.ns.RequestedCatchupHistory().keys())), 504)
        c.receive('1|Y|' + ','.join(map(str, range(1504, 1514))))
        self.assertEqual(len(list(c.ns.RequestedCatchupHistory().keys())), 504)  # Reject overflow atomically.
        c.receive('1|V|1|1|1|zone|501|1000|1000|level-zone:kalimdor/test-coast|1|255|fixed|catchup')
        self.assertIsNone(c.ns.partyRoutePrompt)

    def test_history_request_is_bounded_canonical_and_roster_checked(self):
        c = party(); c.ns.ResetCatchupHistory()
        for payload in ('', '0900', '900,900', '999', '900,'):
            c.receive('1|Y|' + payload)
            self.assertEqual(set(c.ns.RequestedCatchupHistory().keys()), set())
        c.receive('1|Y|900,901', sender='Outsider-TestRealm')
        self.assertEqual(set(c.ns.RequestedCatchupHistory().keys()), set())
        c.receive('1|Y|900,901')
        self.assertEqual(set(c.ns.RequestedCatchupHistory().keys()), {900, 901})
        self.assertIn(901, c.ns.QuestIDs())
        c.lua.globals().peer = None; c.ns.UpdateRoster()
        self.assertEqual(set(c.ns.RequestedCatchupHistory().keys()), set())

    def test_raid_and_solo_do_not_offer_catchup(self):
        for field in ('raid', 'grouped'):
            c = party(); c.lua.globals()[field] = field == 'raid'
            self.assertIsNone(c.ns.PartyCatchupGuide()[0])


class CleanUITests(unittest.TestCase):
    def test_learning_still_applies_but_source_only_appears_in_optional_export(self):
        c = learner(); learn(c)
        c.lua.globals().finished[900] = False
        allowed, reason = c.ns.LearnedPrerequisiteAllowed(901, c.ns.profile, c.ns.self)
        self.assertFalse(allowed); self.assertEqual(reason, 'Finish Quest 0 first.')
        c.ns.ActivateRoute(zone(c)); c.ns.Refresh()
        self.assertNotIn('Observed by', c.ns.navigation.step.text)
        self.assertNotIn('Observed by', c.ns.navigation.context.text)
        c.ns.SetOption('exportCharacterNames', True)
        finding = json.loads(c.ns.ExportGuideFindings())['findings'][0]
        self.assertIsNotNone(finding['sourceCharacter'])

    def test_markers_anchor_to_name_fall_back_to_healthbar_and_allow_independent_toggle(self):
        c = mob_client()
        c.lua.execute("plates.nameplate1.UnitFrame={name=CreateFrame('Frame'),healthBar=CreateFrame('Frame')}")
        c.ns.SetOption('npcMarker', 'quest'); c.ns.UpdateNPCHints()
        hint = c.ns.npcHints['nameplate1']
        self.assertTrue(c.lua.eval('rawequal')(hint.point[2], c.lua.globals().plates.nameplate1.UnitFrame.name))
        self.assertEqual(hint.point[4], 3)
        self.assertEqual(hint.width, 16)
        self.assertIn('AvailableQuestIcon', hint.icon.texture)
        c.lua.execute('plates.nameplate1.UnitFrame.name=secret'); c.ns.UpdateNPCHints()
        self.assertTrue(c.lua.eval('rawequal')(hint.point[2], c.lua.globals().plates.nameplate1.UnitFrame.healthBar))
        c.ns.SetOption('nameplateHints', False); c.ns.UpdateNPCHints()
        self.assertFalse(hint.IsShown(hint))
        self.assertTrue(c.ns.Option('npcHints'))  # Item tooltip master remains enabled.

    def test_map_controls_are_below_viewport_not_children_of_the_canvas(self):
        c = guide_client(2); c.ns.ActivateRoute(zone(c))
        legend = c.ns.routeProvider.legend
        self.assertTrue(c.lua.eval('rawequal')(legend.GetParent(legend), c.lua.globals().WorldMapFrame))
        self.assertEqual(legend.point[1], 'TOPLEFT')
        self.assertEqual(legend.point[3], 'BOTTOMLEFT')
        self.assertLess(legend.point[5], 0)


class PrerequisiteBundleTests(unittest.TestCase):
    def test_nearby_hand_in_unlock_bonus_works_for_arbitrary_chain_ids(self):
        c = guide_client(3)
        data = {900: world_quest('Parent', level=12), 901: world_quest('Child', level=12, previousQuest=900),
                902: world_quest('Nearby unrelated', level=12)}
        data[900]['objectives'][0].update(x=.30, y=.25)
        data[900]['ends'][0].update(x=.33, y=.25)
        data[901]['starts'][0].update(x=.33, y=.25)
        data[902]['starts'][0].update(x=.325, y=.25)
        catalogue(c, data)
        g = zone(c); c.ns.GenerateFixedGuide(g, False)
        steps = [(s.id, s.kind) for s in g.fixedPlan.values()]
        self.assertLess(steps.index((900, 't')), steps.index((902, 'a')))
        self.assertLess(steps.index((900, 't')), steps.index((901, 'a')))
        self.assertEqual(steps[steps.index((900, 't')) + 1], (901, 'a'))


if __name__ == '__main__':
    unittest.main()
