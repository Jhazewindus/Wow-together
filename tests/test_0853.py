"""Ready rewards at an existing visit improve progress without extra walking."""
import unittest

from test_063 import guide_client, zone, order
from test_061 import world_quest
from test_routes import catalogue
from test_066 import reload


def reward_fixture(reward=100, handin_x=0, extra_work=0):
    c = guide_client(6)
    ids = (900, 901, 902, 910, 911, 912)
    catalogue(c, {i: world_quest('Quest ' + str(i), minLevel=1,
                                xp=reward if i == 900 else 0) for i in ids})
    # A later independent three-quest loop fixes the peak log at three.
    # No minimum-level or hard-combat gate changes when A is rewarded sooner.
    stages = [(900, 'a', 0), (901, 'a', 0), (900, 'q', .4), (901, 'q', .4),
              (901, 't', 0), (902, 'a', 0)]
    stages += [(902, 'q', .9)] * (1 + extra_work)
    stages += [(900, 't', handin_x), (902, 't', 0)]
    stages += [(i, 'a', 0) for i in (910, 911, 912)]
    stages += [(i, 'q', .2) for i in (910, 911, 912)]
    stages += [(i, 't', 0) for i in (910, 911, 912)]
    plan = c.lua.table_from([{'id': i, 'kind': kind, 'mapID': 501,
                             'x': x, 'y': 0, 'title': 'Quest ' + str(i)}
                            for i, kind, x in stages], recursive=True)
    distance = c.lua.eval('''function(a,b)
        if a.mapID ~= b.mapID then return 15000, 'unmapped-estimate' end
        return math.abs(a.x-b.x)*1000, 'local-estimate'
    end''')
    return c, plan, distance


def sequence(plan):
    return [(s.id, s.kind) for s in plan.values()]


class ReadyRewardTests(unittest.TestCase):
    def test_ready_reward_collects_xp_before_work_with_same_full_travel_and_log_peak(self):
        c, plan, distance = reward_fixture()
        original = list(plan.values())
        before_model = c.ns.NewGuideFlowModel(plan, distance)
        before = before_model.evaluate(plan)
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        self.assertTrue(result.after.valid)
        self.assertEqual(result.before.distance, result.after.distance)
        self.assertEqual(result.before.peakLog, result.after.peakLog)
        self.assertEqual(result.before.levelDeficitXP, result.after.levelDeficitXP)
        self.assertEqual(result.before.difficultyPressure, result.after.difficultyPressure)
        self.assertEqual(result.before.questXP, result.after.questXP)
        self.assertGreater(result.after.rewardXPBeforeWork, result.before.rewardXPBeforeWork)
        actual = sequence(plan)
        self.assertLess(actual.index((900, 't')), actual.index((902, 'q')))
        self.assertEqual([s for s in sequence(plan) if s[1] == 'q'], [(s.id, s.kind) for s in original if s.kind == 'q'])
        same = c.lua.eval('function(a,b) return a == b end')
        self.assertTrue(same(plan[1], original[0]) and same(plan[len(plan)], original[-1]))
        self.assertEqual(len(plan), len(original))
        for stop in original:
            if stop.kind == 'q':
                self.assertGreaterEqual(result.after.workRewards[stop], before.workRewards[stop])
        move = next(m for m in result.changes.values() if m.kind == 'reward-visit')
        self.assertGreater(move.rewardBeforeWorkGained, 0)

    def test_reward_search_includes_ready_handins_beyond_old_lookahead(self):
        c, plan, distance = reward_fixture(extra_work=135)
        self.assertGreater(sequence(plan).index((900, 't')), 128)
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        self.assertLess(sequence(plan).index((900, 't')), sequence(plan).index((902, 'q')))
        self.assertEqual(result.after.distance, result.before.distance)
        self.assertEqual(len(plan), 153)

    def test_same_visit_combines_multiple_ready_rewards(self):
        c, plan, distance = reward_fixture()
        c.ns.catalogue.quests[901].xp = 200
        # Add a third already-ready quest as the visit anchor. Both rewards
        # remain delayed in the old pass because peak/gates are unchanged.
        c.ns.catalogue.quests[903] = c.lua.table_from(world_quest('Visit anchor', minLevel=1, xp=0), recursive=True)
        original = list(plan.values())
        points = [{'id': 903, 'kind': k, 'mapID': 501, 'x': x, 'y': 0, 'title': 'Visit anchor'}
                  for k, x in (('a', 0), ('q', .4), ('t', 0))]
        # Keep the delayed 901 hand-in immediately before 900's old hand-in.
        arranged = [original[0], original[1], c.lua.table_from(points[0]), original[2], original[3],
                    c.lua.table_from(points[1]), c.lua.table_from(points[2]), original[5], original[6],
                    original[4], *original[7:]]
        plan = c.lua.table_from(arranged)
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        actual = sequence(plan)
        for ident in (900, 901):
            self.assertLess(actual.index((ident, 't')), actual.index((902, 'q')))
        self.assertTrue(any(m.kind == 'reward-visit' and m.actions == 2 for m in result.changes.values()))
        self.assertEqual(result.after.distance, result.before.distance)
        self.assertGreater(result.after.rewardXPBeforeWork, result.before.rewardXPBeforeWork)

    def test_bracket_guard_rejects_grey_reward_loss_hidden_at_low_starting_level(self):
        def setup():
            c, plan, distance = reward_fixture(reward=26000, handin_x=.4)
            c.ns.catalogue.quests[900].level = 22
            c.ns.catalogue.quests[901].level = 14
            c.ns.catalogue.quests[901].xp = 500
            return c, plan, distance
        c, plan, distance = setup()
        original = c.lua.table_from(list(plan.values()))
        # The old single starting-level replay sees useful early rewards.
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        self.assertTrue(any(m.kind == 'reward-visit' for m in result.changes.values()))
        model = c.ns.NewGuideFlowModel(original, distance, c.lua.table_from({'startLevel': 20}))
        self.assertLess(model.evaluate(plan).questXP, model.evaluate(original).questXP)
        # The same guide must retain XP at the top of its bracket as well.
        c, plan, distance = setup()
        old = sequence(plan)
        options = c.lua.table_from({'levelLow': 11, 'levelHigh': 20})
        result = c.ns.ImproveQuestFlow(plan, distance, False, None, options)
        self.assertEqual(sequence(plan), old)
        self.assertFalse(any(m.kind == 'reward-visit' for m in result.changes.values()))

    def test_extra_walking_is_not_justified_by_earlier_xp_alone(self):
        c, plan, _ = reward_fixture()
        # Rewards already share a future stop off the outgoing path. Pulling
        # one into the current visit would add a separate off-path detour.
        for s in plan.values():
            if s.kind == 't' and s.id in (900, 902): s.y = .05
        distance = c.lua.eval('function(a,b) return math.sqrt((a.x-b.x)^2+(a.y-b.y)^2)*1000 end')
        old = sequence(plan)
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        self.assertEqual(sequence(plan), old)
        self.assertEqual(result.moves, 0)

    def test_unknown_reward_does_not_invent_early_xp_benefit(self):
        c, plan, distance = reward_fixture(reward=None)
        old = sequence(plan)
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        self.assertEqual(sequence(plan), old)
        self.assertEqual(result.after.rewardXPBeforeWork, 0)
        self.assertEqual(result.after.unknownRewards, 1)

    def test_unfinished_work_does_not_become_a_ready_handin(self):
        c, plan, distance = reward_fixture()
        # A's objective now follows the early visit, so the hand-in cannot
        # become ready there. No work may be pulled just to earn early XP.
        original = list(plan.values())
        plan = c.lua.table_from([original[0], original[1], original[3], original[4],
                                original[5], original[2], *original[6:]])
        before_q = [s for s in sequence(plan) if s[1] == 'q']
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        actual = sequence(plan)
        self.assertGreater(actual.index((900, 't')), actual.index((900, 'q')))
        self.assertEqual([s for s in sequence(plan) if s[1] == 'q'], before_q)
        self.assertFalse(any(m.kind == 'reward-visit' for m in result.changes.values()))

    def test_missing_or_review_boundary_blocks_ready_reward_move(self):
        for field in ('unknownLocation', 'planNeedsReview'):
            c, plan, distance = reward_fixture()
            plan[7][field] = True
            old = sequence(plan)
            result = c.ns.ImproveQuestFlow(plan, distance, False, None)
            self.assertEqual(sequence(plan), old)
            self.assertEqual(result.moves, 0)

    def test_different_map_is_not_the_same_reward_visit(self):
        c, plan, distance = reward_fixture()
        plan[8].mapID = 502
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        self.assertFalse(any(m.kind == 'reward-visit' for m in result.changes.values()))

    def test_escort_adjacency_and_final_handin_are_preserved(self):
        c, plan, distance = reward_fixture()
        plan[7].action = 'escort'
        result = c.ns.ImproveQuestFlow(plan, distance, False, None)
        actual = sequence(plan)
        self.assertEqual(actual.index((902, 'q')), actual.index((902, 'a')) + 1)
        self.assertEqual(actual[-1], (912, 't'))
        self.assertTrue(result.after.valid)

    def test_reason_and_fixed_order_survive_reload_scan_and_progress(self):
        c, plan, distance = reward_fixture()
        c.ns.ImproveQuestFlow(plan, distance, False, None)
        g = zone(c)
        for index, stop in plan.items(): stop.guideStep = index
        g.fixedPlan = plan
        c.ns.ActivateRoute(g)
        fresh = reload(c)
        handin = next(s for s in fresh.ns.routeSelection.fixedPlan.values() if s.id == 900 and s.kind == 't')
        self.assertTrue(handin.flowEarlyReward)
        decision = fresh.ns.GuideDestinationDecision(handin, fresh.ns.routeSelection, fresh.ns.selectedRoute)
        self.assertEqual(decision.code, 'early-reward')
        self.assertIn('while you', decision.why)
        before = order(fresh.ns.routeSelection)
        fresh.ns.ScanGuideProgress(); fresh.drain()
        self.assertEqual(order(fresh.ns.routeSelection), before)
        fresh.ns.handlers.QUEST_TURNED_IN(900); fresh.ns.UpdateSelectedRoute()
        self.assertEqual(order(fresh.ns.routeSelection), before)
        self.assertNotIn(900, {s.id for s in fresh.ns.selectedRoute.stops.values()})


if __name__ == '__main__': unittest.main()
