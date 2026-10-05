"""Patrick/main-developer regressions: scope, loading, patrol facts and XP estimates."""
import unittest
import random

from test_addon import Client
from test_routes import catalogue, guide, map_canvas
from test_061 import world_quest
from test_063 import order, primitive
from test_066 import reload
from test_076 import npc_client, offer
from test_060 import flight_client
from forever_beta_facts import patrol_paths, apply_fields


class DialogScopeTests(unittest.TestCase):
    def test_accepts_three_selected_offers_but_leaves_unrelated_quest_manual(self):
        c, g = npc_client(False)
        c.ns.db.config.autoAccept = True
        c.lua.execute('accepts=0; function AcceptQuest() accepts=accepts+1 end')
        c.ns.catalogue.quests[903] = c.lua.table_from(world_quest('Outside guide'), recursive=True)
        offer(c, (900, 901, 902, 903))
        for id in (900, 901, 902, 903): c.ns.AutoAcceptOpenedQuest(id)
        self.assertEqual(c.lua.globals().accepts, 3)
        self.assertEqual(c.ns.autoAcceptAttempt, 902)

    def test_no_guide_no_offer_or_failed_prerequisite_never_auto_accepts(self):
        c, g = npc_client(False)
        c.ns.db.config.autoAccept = True
        c.lua.execute('accepts=0; function AcceptQuest() accepts=accepts+1 end')
        c.ns.AutoAcceptOpenedQuest(900)
        offer(c)
        c.ns.catalogue.quests[900].previousQuest = 899
        c.ns.AutoAcceptOpenedQuest(900)
        c.ns.routeSelection = None
        c.ns.AutoAcceptOpenedQuest(901)
        self.assertEqual(c.lua.globals().accepts, 0)

    def test_explicit_dungeon_guide_can_accept_its_quest(self):
        c, g = npc_client(False)
        g.mode, g.personal = 'dungeon', True
        c.ns.catalogue.quests[900].questType = 'Dungeon'
        offer(c, (900,))
        self.assertTrue(c.ns.CanAutoAcceptGuideQuest(900))
        c.ns.db.guideSkips[c.ns.self].quests[900] = True
        self.assertFalse(c.ns.CanAutoAcceptGuideQuest(900))

    def test_under_review_pickup_waits_for_actual_offer_without_inventing_races(self):
        c, g = npc_client(False)
        c.ns.catalogue.quests[900].pickupRequiresOffer = True
        for race in (2, 8, 6, 96):
            c.ns.profile.raceID = race
            self.assertFalse(c.ns.CatalogueAllowed(900, c.ns.profile, c.ns.self)[0])
        offer(c, (900,))
        self.assertTrue(c.ns.CatalogueAllowed(900, c.ns.profile, c.ns.self))


class StableProgressTests(unittest.TestCase):
    def test_loading_does_not_replace_last_log_but_a_real_abandon_does(self):
        c = Client(quests=(900, 901))
        c.lua.execute('C_QuestLog.GetInfo=function(index) if index==1 then return entries[index] end end')
        self.assertFalse(c.ns.ReadQuests())
        self.assertEqual(set(c.ns.active), {900, 901})
        c.lua.execute('entries={{questID=901,title="Still active"}}; C_QuestLog.GetInfo=function(index) return entries[index] end')
        self.assertTrue(c.ns.ReadQuests())
        self.assertEqual(set(c.ns.active), {901})

    def test_confirmed_nonrepeatable_history_survives_transient_false_and_reload(self):
        c, g = npc_client(False)
        before = order(g)
        c.ns.handlers.QUEST_TURNED_IN(900)
        c.ns.UpdateSelectedRoute()
        c.ns.handlers.ZONE_CHANGED_NEW_AREA()
        self.assertEqual(order(g), before)
        self.assertNotIn(900, {s.id for s in c.ns.selectedRoute.stops.values()})
        self.assertTrue(c.ns.Completed(900))
        fresh = reload(c)
        self.assertTrue(fresh.ns.Completed(900))
        self.assertEqual(order(fresh.ns.routeSelection), before)

    def test_completion_memory_is_personal_build_scoped_and_not_repeatable(self):
        c = Client(quests=())
        catalogue(c, {900:world_quest('Ordinary'), 901:world_quest('Repeat', repeatable=True)})
        c.ns.RememberQuestCompletion(900); c.ns.RememberQuestCompletion(901)
        saved = primitive(c.ns.db)
        self.assertTrue(Client(quests=(), saved_variables=saved).ns.Completed(900))
        other = Client(name='Other', quests=(), saved_variables=saved)
        self.assertFalse(other.ns.Completed(900))
        self.assertFalse(c.ns.Completed(901))
        c.lua.execute('GetBuildInfo=function() return "1.60.1","changed",0,16001 end')
        c.ns.InitializeQuestHistory()
        self.assertFalse(c.ns.Completed(900))

    def test_reacceptance_clears_old_completion_and_unknown_is_never_saved(self):
        c = Client(quests=())
        c.ns.RememberQuestCompletion(900)
        c.ns.handlers.QUEST_ACCEPTED(1, 900)
        self.assertFalse(c.ns.Completed(900))
        c.lua.execute('C_QuestLog.IsQuestFlaggedCompleted=function() return secret end')
        self.assertIsNone(c.ns.Completed(901))
        self.assertIsNone(c.ns.questHistory[901])


class MarkerAndFlightTests(unittest.TestCase):
    def test_star_default_migrates_once_and_explicit_cross_stays(self):
        c = Client(saved_variables={'config':{'npcMarker':'cross'}})
        self.assertEqual(c.ns.Option('npcMarker'), 'star')
        self.assertIn('Icon_1', c.ns.StopIcon(c.lua.table_from({'kind':'q','action':'kill'})))
        c.ns.SetOption('npcMarker', 'cross'); c.ns.InitializeConfig()
        self.assertEqual(c.ns.Option('npcMarker'), 'cross')

    def test_first_flight_estimate_counts_down_then_uses_measured_trip(self):
        c = flight_client(); c.ns.ReadFlightMap(); c.ns.NoteFlightSelection(54)
        c.lua.globals().flying = True
        first = c.ns.FlightState()
        self.assertTrue(first.estimated)
        c.lua.globals().clock = 110
        self.assertAlmostEqual(c.ns.FlightState().remaining, first.remaining - 10)
        c.ns.UpdateNavigation()
        self.assertIn('Estimated', c.ns.navigation.distance.text)
        c.lua.globals().flying = False; c.ns.FinishFlight()
        c.ns.NoteFlightSelection(54)
        self.assertFalse(c.ns.pendingFlight.estimated)
        self.assertEqual(c.ns.pendingFlight.expected, 10)

    def test_patrol_lines_are_separate_clipped_and_clear_with_toggle(self):
        c, g = npc_client(False)
        c.ns.questEntities = c.lua.table_from({'npc':{123:{'patrols':[{'mapID':501,'points':[[.1,.1],[.2,.2],[.3,.1]]}]}}}, recursive=True)
        c.lua.globals().WorldMapFrame.SetMapID(c.lua.globals().WorldMapFrame, 501)
        c.ns.DrawRoute()
        self.assertEqual(c.ns.routeStats.patrols, 2)
        self.assertGreater(c.ns.routeStats.lines, 0)
        c.ns.SetOption('patrolHints', False)
        self.assertEqual(c.ns.routeStats.patrols, 0)
        self.assertFalse(c.ns.routeProvider.patrolLines[1].IsShown(c.ns.routeProvider.patrolLines[1]))


class PatrolSourceTests(unittest.TestCase):
    def test_flat_and_nested_explicit_paths_preserve_order_and_reject_invalid_points(self):
        flat = {1:{1:30,2:40},2:{1:35,2:45}}
        self.assertEqual(patrol_paths(flat), [[[30,40],[35,45]]])
        self.assertEqual(patrol_paths({1:flat,2:flat}), [[[30,40],[35,45]],[[30,40],[35,45]]])
        self.assertEqual(patrol_paths({1:{1:200,2:40},2:{1:35,2:45}}), [])
        self.assertEqual(patrol_paths({1:{1:30,2:40}}), [])

    def test_explicit_beta_removal_clears_inherited_patrol(self):
        row = {'waypoints':{14:{1:{1:30,2:40},2:{1:35,2:45}}}}
        apply_fields(row, {'waypoints':None})
        self.assertIsNone(row['waypoints'])


class XPProjectionTests(unittest.TestCase):
    def client(self):
        c, g = npc_client(False)
        g.fullGuide = True
        c.ns.xpBaseline = c.lua.table_from({12:1000,13:1200,14:1400})
        c.lua.execute('UnitXP=function() return 500 end; UnitXPMax=function() return 1000 end')
        c.ns.ReadGuideXP()
        for q in c.ns.catalogue.quests.values(): q.xp = 400
        g.xpStartLevel = None  # Fixture changed the source facts after activation.
        return c, g

    def test_forecast_counts_unique_unfinished_rewards_and_keeps_start_snapshot(self):
        c, g = self.client()
        estimate = c.ns.GuideXPProjection(g)
        self.assertEqual((estimate.reward,estimate.startLevel,estimate.finishLevel), (1200,12,13))
        self.assertTrue(estimate.baseline)
        c.ns.CaptureGuideXP(g)
        c.ns.RememberQuestCompletion(900)
        c.ns.profile.level = 13
        self.assertIn('Lv 12', c.ns.GuideXPText(g))
        self.assertIn('1200 XP', c.ns.GuideXPText(g))

    def test_missing_reward_and_curve_are_reported_not_fabricated(self):
        c, g = self.client()
        c.ns.catalogue.quests[901].xp = None
        c.ns.xpBaseline = None
        estimate = c.ns.GuideXPProjection(g)
        self.assertEqual(estimate.unknown, 1)
        self.assertTrue(estimate.unavailable)
        self.assertIn('XP curve incomplete', c.ns.GuideXPText(g))
        g.xpStartLevel, g.xpUnknown = 'corrupt', None
        self.assertIn('XP curve incomplete', c.ns.GuideXPText(g))

    def test_skips_and_wrong_race_are_excluded_and_secret_xp_not_used(self):
        c, g = self.client()
        c.ns.db.guideSkips[c.ns.self].quests[901] = True
        c.ns.catalogue.quests[902].allowedRaceIDs = c.lua.table_from([6])
        c.lua.execute('UnitXP=function() return secret end; UnitXPMax=function() return secret end')
        estimate = c.ns.GuideXPProjection(g)
        self.assertEqual(estimate.reward, 400)
        self.assertTrue(estimate.assumedStart)


class FixedBundleTests(unittest.TestCase):
    def test_bundle_search_shortens_route_without_splitting_escorts_or_stage_order(self):
        c = Client(quests=())
        catalogue(c, {900+i:world_quest(str(i)) for i in range(6)})
        source, rng = [], random.Random(0)
        for i in range(6):
            x, y = rng.random(), rng.random()
            source.extend([{'id':900+i,'kind':'a','mapID':501,'x':x,'y':y},
                {'id':900+i,'kind':'q','mapID':501,'x':x,'y':y,'action':'escort'},
                {'id':900+i,'kind':'t','mapID':501,'x':rng.random(),'y':rng.random()}])
        plan = c.lua.table_from(source, recursive=True)
        distance = c.lua.eval('function(a,b) return math.sqrt((a.x-b.x)^2+(a.y-b.y)^2)*1000 end')
        result = c.ns.OptimizeFixedPlan(plan, distance, False)
        self.assertGreater(result.bundles, 0)
        self.assertLess(result.after, result.before)
        self.assertEqual(len(plan), len(source))
        for id in range(900,906):
            positions = {s.kind:i for i,s in plan.items() if s.id==id}
            self.assertEqual(positions['q'],positions['a']+1)
            self.assertGreater(positions['t'],positions['q'])


if __name__ == '__main__': unittest.main()
