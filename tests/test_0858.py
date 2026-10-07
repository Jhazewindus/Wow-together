"""Connection ranking must retain nearby links before comparing full guides."""
import itertools
import unittest

from test_070 import network_client, point
from test_0853 import reward_fixture, sequence
from test_0854 import fixture


class TravelConnectionRankingTests(unittest.TestCase):
    def client(self, order=(0, 1, 2, 3)):
        nodes = {chr(65 + i): {'mapID': 501, 'x': .1 + rank * .01, 'y': .37}
                 for i, rank in enumerate(order)}
        nodes['Z'] = {'mapID': 502, 'x': .1, 'y': .37}
        origin = chr(65 + order.index(0))
        c = network_client([{'from': origin, 'to': 'Z', 'method': 'ship', 'seconds': 10}], nodes)
        cache = c.lua.table()
        metric, reset = c.ns.NewFixedTravelCost(
            lambda a, b: c.ns.FixedGuideGeometry(a, b, cache), False, None)
        return c, metric, reset

    def test_nearest_connection_is_not_evicted_by_later_more_expensive_nodes(self):
        c, metric, _ = self.client()
        # Old ranking compared raw lengths with already inflated costs. Four
        # progressively farther nodes evicted the only connected nearest one.
        length, basis = metric(point(c, 501, 0), point(c, 502, .1))
        self.assertEqual(basis, 'network-estimate')
        self.assertAlmostEqual(length, 100 * 1.25 + 10 * 7)

    def test_cost_and_reachability_are_independent_of_source_node_names(self):
        for order in itertools.permutations(range(4)):
            with self.subTest(order=order):
                c, metric, _ = self.client(order)
                length, basis = metric(point(c, 501, 0), point(c, 502, .1))
                self.assertEqual(basis, 'network-estimate')
                self.assertAlmostEqual(length, 195)

    def test_loading_and_explicit_reset_keep_the_correct_connection(self):
        c, metric, reset = self.client()
        a, b = point(c, 501, 0), point(c, 502, .1)
        for checkpoint in (True, False):
            self.assertEqual(metric(a, b), (195, 'network-estimate'))
            reset(checkpoint)
        self.assertEqual(metric(a, b), (195, 'network-estimate'))

    def test_reverse_transport_is_not_created_by_the_better_attachment(self):
        c, metric, _ = self.client()
        a, b = point(c, 501, 0), point(c, 502, .1)
        self.assertEqual(metric(a, b)[1], 'network-estimate')
        self.assertEqual(metric(b, a)[1], 'unmapped-estimate')

    def test_corrected_pricing_cannot_discard_an_established_early_reward(self):
        c, plan, _ = reward_fixture(reward=100, handin_x=.4)
        metric = c.lua.eval("function(a,b) return math.abs(a.x-b.x)*1000,'network-estimate' end")
        corrected = c.lua.eval('''function(a,b)
            return math.abs(a.x-b.x)*1000+(b.x==.4 and b.kind=='t' and a.kind~='t' and 1000 or 0),'network-estimate'
        end''')
        c.ns.OptimizeFixedPlan(plan, metric, False, None, metric, None, metric)
        baseline = c.lua.table_from(list(plan.values()))
        model = c.ns.NewGuideFlowModel(baseline, corrected)
        before = model.evaluate(baseline)
        result = c.ns.OptimizeFixedPlan(plan, metric, False, None, metric, None, metric, corrected)
        after = model.evaluate(plan)
        self.assertIsNotNone(result.connections)
        self.assertTrue(after.valid)
        self.assertLessEqual(after.distance, before.distance)
        for stop, reward in before.workRewards.items():
            self.assertGreaterEqual(after.workRewards[stop], reward)
        self.assertEqual(result.after, after.distance)

    def test_unchanged_prices_do_not_run_another_search_or_change_order(self):
        c, plan, metric = fixture()
        baseline = c.lua.table_from(list(plan.values()))
        c.ns.OptimizeFixedPlan(baseline, metric, False, None, metric, None, metric)
        result = c.ns.OptimizeFixedPlan(plan, metric, False, None, metric, None, metric, metric)
        self.assertIsNone(result.connections)
        self.assertEqual(sequence(plan), sequence(baseline))


if __name__ == '__main__':
    unittest.main()
