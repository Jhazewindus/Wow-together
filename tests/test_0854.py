"""Graph-aware ordering preserves the complete guide and progression."""
import unittest

from test_063 import guide_client, zone, order
from test_061 import world_quest
from test_066 import reload
from test_routes import catalogue
from test_0853 import reward_fixture, sequence
import test_0849


def fixture():
    c = guide_client(3)
    catalogue(c, {i: world_quest('Quest ' + str(i), minLevel=1, xp=0)
                  for i in (900, 901, 902)})
    points = [(i, 'a', 0) for i in (900, 901, 902)]
    points += [(900, 'q', .8), (901, 'q', .1), (902, 'q', .9)]
    points += [(i, 't', 0) for i in (900, 901, 902)]
    plan = c.lua.table_from([{'id': i, 'kind': kind, 'mapID': 501, 'x': x, 'y': 0}
                            for i, kind, x in points], recursive=True)
    # Stand-in published costs; client terrain/routing is tested separately.
    metric = c.lua.eval("function(a,b) return math.abs(a.x-b.x)*1000, 'network-estimate' end")
    return c, plan, metric


class FixedTravelOrderTests(unittest.TestCase):
    def test_loading_checkpoint_retains_costs_and_explicit_reset_recalculates_attachments(self):
        c, fallback = test_0849.TravelComparisonTests().client()
        c.lua.globals().attachment_calls = 0
        c.lua.globals().attachment_fallback = fallback
        counted = c.lua.eval('''function(a,b)
            attachment_calls=attachment_calls+1;return attachment_fallback(a,b)
        end''')
        cost, reset = c.ns.NewFixedTravelCost(counted, False, None)
        a, b = c.ns.travelData.nodes.WEST, c.ns.travelData.nodes.EAST
        first = cost(a, b)
        count = c.lua.globals().attachment_calls
        reset(True)
        self.assertEqual(cost(a, b), first)
        self.assertEqual(c.lua.globals().attachment_calls, count)
        reset()
        self.assertEqual(cost(a, b), first)
        self.assertGreater(c.lua.globals().attachment_calls, count)

    def test_full_graph_journey_improves_without_removing_actions_or_changing_endpoints(self):
        c, plan, metric = fixture()
        original = c.lua.table_from(list(plan.values()))
        model = c.ns.NewGuideFlowModel(original, metric)
        result = c.ns.ImproveFixedTravelOrder(plan, metric, False, None)
        after = model.evaluate(plan)
        self.assertTrue(after.valid)
        self.assertGreater(result.moves, 0)
        self.assertLess(after.distance, result.before.distance - 50)
        self.assertCountEqual(sequence(plan), sequence(original))
        self.assertEqual(sequence(plan)[0], sequence(original)[0])
        self.assertEqual(sequence(plan)[-1], sequence(original)[-1])
        for field in ('peakLog', 'levelDeficitXP', 'minimumKills', 'difficultyPressure', 'questXP'):
            self.assertEqual(after[field], result.before[field])
        self.assertTrue(all(m.kind in ('network-step', 'network-bundle') for m in result.changes.values()))
        self.assertAlmostEqual(sum(m.travelSaved for m in result.changes.values()),
                               result.before.distance - result.after.distance)

    def test_geometric_fallback_is_not_evidence_for_a_network_change(self):
        c, plan, _ = fixture()
        metric = c.lua.eval('''function(a,b)
            return math.abs(a.x-b.x)*1000,
                a.x == 0 and b.x == 0 and 'network-estimate' or 'unmapped-estimate'
        end''')
        old = sequence(plan)
        result = c.ns.ImproveFixedTravelOrder(plan, metric, False, None)
        self.assertEqual(sequence(plan), old)
        self.assertEqual(result.moves, 0)

    def test_purely_local_guide_skips_the_extra_search(self):
        c, plan, _ = fixture()
        metric = c.lua.eval("function(a,b) return math.abs(a.x-b.x)*1000, 'local-estimate' end")
        old = sequence(plan)
        result = c.ns.ImproveFixedTravelOrder(plan, metric, False, None)
        self.assertEqual(sequence(plan), old)
        self.assertEqual(result.candidates, 0)

    def test_uncertain_or_review_step_remains_a_recovery_boundary(self):
        for flag in ('unknownLocation', 'planNeedsReview'):
            c, plan, metric = fixture()
            plan[5][flag] = True
            old = sequence(plan)
            c.ns.ImproveFixedTravelOrder(plan, metric, False, None)
            self.assertEqual(sequence(plan), old)

    def test_low_precision_coordinate_savings_do_not_churn_order(self):
        c, plan, _ = fixture()
        metric = c.lua.eval("function(a,b) return math.abs(a.x-b.x)*10, 'network-estimate' end")
        old = sequence(plan)
        self.assertEqual(c.ns.ImproveFixedTravelOrder(plan, metric, False, None).moves, 0)
        self.assertEqual(sequence(plan), old)

    def test_known_unlock_and_escort_order_are_preserved(self):
        c, plan, metric = fixture()
        c.ns.catalogue.quests[902].previousQuest = 900
        stages = list(plan.values())
        # A complete parent loop must precede its child's acceptance. B's
        # escort starts immediately after accepting B even if another point
        # looks cheaper between them.
        plan = c.lua.table_from([stages[0], stages[3], stages[6], stages[1],
                                 stages[4], stages[2], stages[5], stages[7], stages[8]])
        stages[4].action = 'escort'
        model = c.ns.NewGuideFlowModel(plan, metric)
        c.ns.ImproveFixedTravelOrder(plan, metric, False, None)
        actual = sequence(plan)
        self.assertTrue(model.evaluate(plan).valid)
        self.assertLess(actual.index((900, 't')), actual.index((902, 'a')))
        self.assertEqual(actual.index((901, 'q')), actual.index((901, 'a')) + 1)

    def test_ready_reward_cannot_be_delayed_to_reduce_travel(self):
        c, plan, _ = reward_fixture(reward=100)
        # Establish the prior reward pass's useful first visit.
        metric = c.lua.eval("function(a,b) return math.abs(a.x-b.x)*1000, 'network-estimate' end")
        c.ns.ImproveQuestFlow(plan, metric, False, None)
        model = c.ns.NewGuideFlowModel(plan, metric)
        before = model.evaluate(plan)
        c.ns.ImproveFixedTravelOrder(plan, metric, False, None)
        after = model.evaluate(plan)
        for stop, reward in before.workRewards.items():
            self.assertGreaterEqual(after.workRewards[stop], reward)

    def test_bracket_replay_rejects_grey_xp_loss(self):
        c, plan, _ = reward_fixture(reward=50000, handin_x=.4)
        for quest in c.ns.catalogue.quests.values(): quest.level = 16
        c.ns.catalogue.quests[901].level = 14
        c.ns.catalogue.quests[901].xp = 500
        metric = c.lua.eval('''function(a,b)
            return math.abs(a.x-b.x)*1000 + (a.x==.9 and b.x==.4 and 500 or 0), 'network-estimate'
        end''')
        original = c.lua.table_from(list(plan.values()))
        stages = list(plan.values())
        tempting = c.lua.table_from(stages[:3] + [stages[7]] + stages[3:7] + stages[8:])
        high = c.ns.NewGuideFlowModel(original, metric, c.lua.table_from({'startLevel': 20}))
        self.assertLess(high.evaluate(tempting).distance, high.evaluate(original).distance)
        self.assertLess(high.evaluate(tempting).questXP, high.evaluate(original).questXP)
        options = c.lua.table_from({'levelLow': 11, 'levelHigh': 20})
        result = c.ns.ImproveFixedTravelOrder(plan, metric, False, None, options)
        for level in (11, 15, 20):
            model = c.ns.NewGuideFlowModel(original, metric, c.lua.table_from({'startLevel': level}))
            before, after = model.evaluate(original), model.evaluate(plan)
            self.assertGreaterEqual(after.questXP, before.questXP)
            self.assertLessEqual(after.levelDeficitXP, before.levelDeficitXP)
        self.assertGreater(result.candidates, 0)

    def test_cooperative_search_yields_and_matches_synchronous_order(self):
        def expand(c, plan):
            stops = list(plan.values())
            extras = [c.lua.table_from({'id': 900, 'kind': 'q', 'mapID': 501, 'x': .8, 'y': 0}) for _ in range(8)]
            return c.lua.table_from(stops[:4] + extras + stops[4:])
        a, plan, metric = fixture()
        plan = expand(a, plan)
        a.ns.ImproveFixedTravelOrder(plan, metric, False, None)
        b, other, cost = fixture()
        other = expand(b, other)
        b.lua.globals().test_plan, b.lua.globals().test_metric = other, cost
        resume = b.lua.eval('''function(ns)
            local co = coroutine.create(function() return ns.ImproveFixedTravelOrder(test_plan, test_metric, true) end)
            return function() local ok,value = coroutine.resume(co); assert(ok,value)
                return coroutine.status(co),value end
        end''')(b.ns)
        yields = 0
        while True:
            state, value = resume()
            if state == 'dead': break
            yields += 1
            self.assertLess(yields, 100)
        self.assertGreater(yields, 0)
        self.assertEqual(sequence(other), sequence(plan))

    def test_optimized_order_survives_reload_scan_and_quest_updates(self):
        c, plan, metric = fixture()
        c.ns.ImproveFixedTravelOrder(plan, metric, False, None)
        g = zone(c)
        for index, stop in plan.items(): stop.guideStep = index
        g.fixedPlan = plan
        c.ns.ActivateRoute(g)
        fresh = reload(c)
        old = order(fresh.ns.routeSelection)
        fresh.ns.ScanGuideProgress(); fresh.drain()
        self.assertEqual(order(fresh.ns.routeSelection), old)
        fresh.ns.handlers.QUEST_TURNED_IN(900); fresh.ns.UpdateSelectedRoute()
        self.assertEqual(order(fresh.ns.routeSelection), old)


if __name__ == '__main__':
    unittest.main()
