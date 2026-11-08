"""The compatibility route-cost API reproduces the pre-extraction weights."""
import unittest

from test_addon import Client


class RouteCostTests(unittest.TestCase):
    def test_shared_cost_keeps_existing_travel_reward_and_saving_values(self):
        c = Client(quests=())
        weights = c.ns.ROUTE_WEIGHTS
        self.assertEqual(c.ns.RouteCostMinimumSaving(100000), 50)
        self.assertEqual(c.ns.RouteCostMinimumSaving(200000), 100)
        quest = c.lua.table_from({'level': 10, 'xp': 1000})
        self.assertEqual(c.ns.RouteCostQuestReward(quest, 15), 1000)
        self.assertEqual(c.ns.RouteCostQuestReward(quest, 16), 800)
        self.assertEqual(c.ns.RouteCostQuestReward(quest, 25), 100)
        self.assertEqual(weights.walkingDistanceFactor, 1.25)
        self.assertEqual(weights.normalizedDistanceScale, 6000)

    def test_step_cost_combines_only_explicit_weights(self):
        c = Client(quests=())
        c.ns.catalogue = c.lua.table_from({'quests': {1: {'id': 1, 'xp': 100, 'level': 10}}}, recursive=True)
        model = c.ns.RouteCostModel(c.lua.table_from({'travel': c.lua.eval('function() return 12 end'), 'logLimit': 10}))
        stop = c.lua.table_from({'id': 1})
        state = c.lua.table_from({'activeCount': 8, 'logLimit': 10, 'rewardWeight': .01,
                                  'logPressureWeight': 3, 'profile': {'level': 10}} , recursive=True)
        self.assertAlmostEqual(model.stepCost(model, stop, None, state), -1)
        self.assertAlmostEqual(model.stepCost(model, stop, stop, state), 11)


if __name__ == '__main__':
    unittest.main()
