"""Same-hub reward/log-space choices retain the full guide and its recovery."""
import unittest

from test_063 import guide_client, zone, order
from test_061 import world_quest, run_plan
from test_routes import catalogue
from test_066 import reload
from test_addon import Client


def hub_fixture(reward=100, handin_x=0):
    c = guide_client(3)
    catalogue(c, {900: world_quest('Ready reward', minLevel=1, xp=reward),
                  901: world_quest('New work', minLevel=1, xp=100),
                  902: world_quest('Other work', minLevel=1, xp=100)})
    operations = ((900, 'a', 0), (900, 'q', 0), (901, 'a', 0), (902, 'a', 0),
                  (901, 'q', .9), (902, 'q', .9), (900, 't', handin_x),
                  (901, 't', 0), (902, 't', 0))
    plan = c.lua.table_from([{'id': ident, 'kind': kind, 'mapID': 501,
                             'x': x, 'y': 0, 'title': c.ns.CatalogueQuest(ident).title}
                            for ident, kind, x in operations], recursive=True)
    distance = c.lua.eval('function(a,b) return math.abs(a.x-b.x)*1000 end')
    return c, plan, distance


def sequence(plan):
    return [(s.id, s.kind) for s in plan.values()]


class HubFlowTests(unittest.TestCase):
    def test_equal_travel_handin_frees_room_before_next_pickups(self):
        c, plan, distance = hub_fixture()
        old = sequence(plan)
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        actual = sequence(plan)
        self.assertEqual(result.moves, 1)
        self.assertEqual(result.after.distance, result.before.distance)
        self.assertEqual((result.before.peakLog, result.after.peakLog), (3, 2))
        self.assertEqual(sorted(actual), sorted(old))
        self.assertEqual((actual[0], actual[-1]), (old[0], old[-1]))
        self.assertLess(actual.index((900, 't')), actual.index((901, 'a')))
        self.assertEqual([s for s in actual if s[1] == 'q'], [s for s in old if s[1] == 'q'])
        self.assertEqual(result.changes[1].kind, 'hub-progression')
        self.assertEqual(result.changes[1].logPeakReduced, 1)
        self.assertTrue(next(s for s in plan.values() if s.id == 900 and s.kind == 't').flowLogSpace)

    def test_equal_travel_collects_xp_before_required_pickup_level(self):
        c, plan, distance = hub_fixture()
        c.ns.catalogue.quests[901].minLevel = 2
        c.ns.xpBaseline = c.lua.table_from({1: 100, 2: 1000, 3: 2000})
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        self.assertEqual(result.before.levelDeficitXP, 100)
        self.assertEqual(result.after.levelDeficitXP, 0)
        self.assertEqual(result.after.distance, result.before.distance)
        self.assertEqual(result.changes[1].levelDeficitReduced, 100)
        reward = next(s for s in plan.values() if s.id == 900 and s.kind == 't')
        self.assertTrue(reward.flowRewardFirst)
        decision = c.ns.GuideDestinationDecision(reward, zone(c), c.lua.table_from({'stops': plan}))
        self.assertEqual(decision.code, 'reward-first')
        self.assertIn('XP', decision.why)

    def test_more_walking_is_not_justified_by_fewer_held_quests_alone(self):
        c, plan, _ = hub_fixture()
        # Same future reward hub off the outgoing work leg. Unlike collinear
        # coordinates, taking one reward early truly adds walking here.
        for s in plan.values():
            if s.kind == 't': s.y = .1
        distance = c.lua.eval('function(a,b) return math.sqrt((a.x-b.x)^2+(a.y-b.y)^2)*1000 end')
        old = sequence(plan)
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        self.assertEqual(sequence(plan), old)
        self.assertEqual(result.moves, 0)

    def test_no_reward_still_allows_proven_log_space_benefit(self):
        c, plan, distance = hub_fixture(reward=0)
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        self.assertEqual((result.before.peakLog, result.after.peakLog), (3, 2))
        self.assertEqual(result.before.questXP, result.after.questXP)

    def test_review_or_missing_location_boundary_is_not_crossed(self):
        for field in ('unknownLocation', 'planNeedsReview'):
            c, plan, distance = hub_fixture()
            plan[4][field] = True
            old = sequence(plan)
            c.ns.ImproveQuestFlow(plan, distance, False, None)
            self.assertEqual(sequence(plan), old)

    def test_capacity_replay_includes_unrelated_reserved_log_slots(self):
        c, plan, distance = hub_fixture()
        settings = c.lua.table_from({'logCapacity': 4, 'initialLog': 2})
        model = c.ns.NewGuideFlowModel(plan, distance, settings)
        before = model.evaluate(plan)
        self.assertFalse(before.valid)
        self.assertEqual(before.logOverflow, 1)
        c.ns.ImproveQuestFlow(plan, distance, False, None)
        after = c.ns.NewGuideFlowModel(plan, distance, settings).evaluate(plan)
        self.assertTrue(after.valid)
        self.assertEqual(after.peakLog, 4)
        self.assertEqual(after.finishLog, 2)
        self.assertEqual(after.initialLog, 2)

    def test_reward_replay_uses_the_same_explicit_starting_xp(self):
        c, plan, distance = hub_fixture()
        c.ns.catalogue.quests[901].minLevel = 2
        settings = c.lua.table_from({'startXP': 50, 'xpCurve': {1: 100, 2: 1000}}, recursive=True)
        before = c.ns.NewGuideFlowModel(plan, distance, settings).evaluate(plan)
        self.assertEqual(before.levelDeficitXP, 50)
        c.ns.ImproveQuestFlow(plan, distance, False, None)
        after = c.ns.NewGuideFlowModel(plan, distance, settings).evaluate(plan)
        self.assertEqual(after.levelDeficitXP, 0)
        self.assertEqual(after.startXP, before.startXP)

    def test_unchanged_hub_visits_are_not_reshuffled(self):
        c, plan, distance = hub_fixture(reward=0)
        # Ready work, then all hand-ins at one point. Moving one hand-in among
        # others supplies no new XP or room at an intervening pickup.
        plan = c.lua.table_from([plan[i] for i in (1, 3, 4, 2, 5, 6, 7, 8, 9)])
        old = sequence(plan)
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        self.assertEqual(result.moves, 0)
        self.assertEqual(sequence(plan), old)

    def test_explanations_survive_save_reload_and_completed_handin_disappears(self):
        c, plan, distance = hub_fixture()
        c.ns.ImproveQuestFlow(plan, distance, False, None)
        g = zone(c)
        for index, s in plan.items(): s.guideStep = index
        g.fixedPlan = plan
        c.ns.ActivateRoute(g)
        fresh = reload(c)
        self.assertEqual(order(fresh.ns.routeSelection), order(g))
        handin = next(s for s in fresh.ns.routeSelection.fixedPlan.values() if s.id == 900 and s.kind == 't')
        self.assertTrue(handin.flowLogSpace)
        self.assertEqual(fresh.ns.GuideDestinationDecision(handin, fresh.ns.routeSelection, fresh.ns.selectedRoute).code, 'quest-log-space')
        fresh.ns.handlers.QUEST_TURNED_IN(900)
        fresh.ns.UpdateSelectedRoute()
        self.assertNotIn(900, {s.id for s in fresh.ns.selectedRoute.stops.values()})
        self.assertEqual(order(fresh.ns.routeSelection), order(g))

    def test_cooperative_scan_keeps_order_without_unbounded_hub_replays(self):
        c = guide_client(26); g = zone(c)
        c.ns.ShowGuideOnMap(g)
        slices = run_plan(c)
        self.assertLessEqual(slices, 200)
        old = order(g)
        c.ns.ScanGuideProgress(); c.drain()
        self.assertEqual(order(c.ns.routeSelection), old)


class PlaceholderScopeTests(unittest.TestCase):
    def test_explicit_editorial_markers_are_excluded_without_hiding_real_quests(self):
        c = guide_client(5)
        catalogue(c, {900: world_quest('Real first'), 901: world_quest('Real second'),
                      902: world_quest('<NYI> <TXT> Get those Hyenas!!!'),
                      903: world_quest('Legends of the Earth <nyi>'),
                      904: world_quest('< Txt > No Reward')})
        self.assertEqual({r.id for r in zone(c).records.values()}, {900, 901})
        for ident in (902, 903, 904):
            self.assertTrue(c.ns.IsRetiredQuest(ident))
            self.assertFalse(c.ns.LevelingQuestEnabled(ident))
            self.assertIsNotNone(c.ns.CatalogueQuest(ident))  # Research/library facts stay intact.
        self.assertFalse(c.ns.IsRetiredQuest(900))

    def test_retained_guide_skips_placeholder_instructions_without_completed_credit(self):
        c = guide_client(3); g = zone(c)
        c.ns.GenerateFixedGuide(g, False)
        c.ns.catalogue.quests[900].title = '<NYI> Old placeholder'
        route = c.ns.BuildFixedGuideRoute(g, False)
        self.assertNotIn(900, {s.id for s in route.stops.values()})
        self.assertFalse(c.ns.Completed(900))
        self.assertFalse(c.ns.GuideQuestSkipped(900))

    def test_thousand_needles_keeps_real_intro_and_centaur_chain_at_twenty_five(self):
        c = Client(quests=(), use_catalogue=True); c.guide_environment(level=25)
        c.lua.execute("grouped=false; function UnitClass() return 'Shaman','SHAMAN',7 end; function UnitRace() return 'Orc','Orc',2 end")
        c.ns.db.config.soloMode = True; c.ns.ReadProfile()
        records = c.ns.LevelingGuideRecords('level-zone:kalimdor/thousand-needles:levels:21-30')
        ids = {r.id for r in records.values()}
        self.assertTrue({4542, 4841}.issubset(ids))
        self.assertNotIn(4323, ids)
        self.assertTrue(c.ns.LevelingQuestEnabled(4542))
        self.assertTrue(c.ns.LevelingQuestEnabled(4841))


if __name__ == '__main__': unittest.main()
