"""Fixed-guide costs must price the same mapped barriers as live navigation.

Synthetic map geometry validates route comparisons, not beta terrain accuracy.
"""
import unittest

from test_070 import point
from test_0856 import terrain_client
from test_0853 import reward_fixture, sequence
from test_0854 import fixture
from test_063 import guide_client, zone, order
from test_061 import run_plan


def costs(c, cooperative=False, checkpoint=None):
    cache = c.lua.table()
    return c.ns.NewFixedTravelCost(
        lambda a, b: c.ns.FixedGuideGeometry(a, b, cache), cooperative, checkpoint)


class FixedTerrainCostTests(unittest.TestCase):
    def test_short_local_chord_crossing_ridge_uses_visible_bends(self):
        c = terrain_client()
        a, b = point(c, 501, .35), point(c, 501, .65)
        metric, _ = costs(c)
        length, basis = metric(a, b)
        self.assertEqual(basis, 'network-estimate')
        self.assertGreater(length, 300)
        path = c.ns.FindTravelPath(a, b, False)
        self.assertTrue(path.hasTerrain)
        self.assertAlmostEqual(length, path.seconds * 7)

    def test_zero_cost_published_walk_cannot_bypass_ridge(self):
        c = terrain_client()
        a, b = point(c, 501, .1), point(c, 501, .9)
        c.ns.travelData.nodes.WEST, c.ns.travelData.nodes.EAST = a, b
        c.ns.travelData.edges[1] = c.lua.table_from(
            {'from': 'WEST', 'to': 'EAST', 'method': 'walk', 'seconds': 0})
        metric, _ = costs(c)
        length, basis = metric(a, b)
        self.assertEqual(basis, 'network-estimate')
        self.assertGreater(length, 800)
        self.assertAlmostEqual(length, c.ns.FindTravelPath(a, b, False).seconds * 7)

    def test_ridge_is_not_bypassed_by_a_distant_anchor_attachment(self):
        c = terrain_client()
        a, b = point(c, 501, .1), point(c, 501, .9)
        c.ns.travelData.nodes.FAR = b
        metric, _ = costs(c)
        length, basis = metric(a, b)
        self.assertEqual(basis, 'network-estimate')
        self.assertGreater(length, 1000)

    def test_missing_mesa_approach_is_blocked_without_deleting_quest(self):
        c = terrain_client()
        metric, _ = costs(c)
        length, basis = metric(point(c, 501, .1), point(c, 501, .5))
        self.assertEqual(basis, 'blocked')
        self.assertGreaterEqual(length, 20000)
        self.assertFalse(c.ns.Completed(900))
        self.assertFalse(c.ns.GuideQuestSkipped(900))

    def test_work_inside_same_mesa_and_open_ground_keep_local_estimates(self):
        c = terrain_client(); metric, _ = costs(c)
        for a, b in ((point(c, 501, .45), point(c, 501, .55)),
                     (point(c, 501, .1, .1), point(c, 501, .3, .1)),
                     (point(c, 502, .1), point(c, 502, .3))):
            length, basis = metric(a, b)
            self.assertEqual(basis, 'local-estimate')
            self.assertAlmostEqual(length, abs(a.x - b.x) * 1000)

    def test_personal_flight_is_not_assumed_by_generic_guide(self):
        c = terrain_client()
        a, b = point(c, 501, .1), point(c, 501, .9)
        c.ns.travelData.nodes.WEST, c.ns.travelData.nodes.EAST = a, b
        c.ns.travelData.edges[1] = c.lua.table_from(
            {'from': 'WEST', 'to': 'EAST', 'method': 'taxi', 'seconds': 1})
        state = c.ns.db.flights[c.ns.self]
        for ident, x in ((9033, .1), (9034, .9)):
            state.nodes[ident] = c.lua.table_from({'id': ident, 'known': True,
                'point': {'mapID': 501, 'x': x, 'y': .37}}, recursive=True)
        state.edges['9033:9034'] = c.lua.table_from({'source': 9033, 'destination': 9034})
        state.timings['9033:9034'] = c.lua.table_from({'mean': 1, 'samples': 1,
            'validated': True, 'build': c.ns.flightTimingBuild})
        metric, _ = costs(c)
        self.assertGreater(metric(a, b)[0], 1000)
        self.assertLess(c.ns.FindTravelPath(a, b, True).seconds, 60)

    def test_directed_ship_crosses_barrier_without_becoming_a_walk(self):
        c = terrain_client()
        a, b = point(c, 501, .1), point(c, 501, .9)
        c.ns.travelData.nodes.WEST, c.ns.travelData.nodes.EAST = a, b
        c.ns.travelData.edges[1] = c.lua.table_from(
            {'from': 'WEST', 'to': 'EAST', 'method': 'ship', 'seconds': 10})
        metric, _ = costs(c)
        self.assertEqual(metric(a, b), (70, 'network-estimate'))
        self.assertGreater(metric(b, a)[0], 1000)

    def test_hostile_settlement_still_blocks_a_terrain_corner_shortcut(self):
        c = terrain_client()
        c.ns.travelData.settlements = c.lua.table_from([{'name': 'Enemy town',
            'faction': 'Alliance', 'mapID': 501, 'minX': .4, 'maxX': .6,
            'minY': 0, 'maxY': .3}], recursive=True)
        a, b = point(c, 501, .1), point(c, 501, .9)
        metric, _ = costs(c)
        path = c.ns.FindTravelPath(a, b, False)
        self.assertTrue(all(s.to.y > .5 for s in list(path.legs.values())[:-1]))
        self.assertAlmostEqual(metric(a, b)[0], path.seconds * 7)

    def test_projection_checks_a_published_cross_zone_walk(self):
        c = terrain_client(); c.lua.execute('bounds[502].x=500')
        a, b = point(c, 501, .1), point(c, 502, .4)
        c.ns.travelData.nodes.WEST, c.ns.travelData.nodes.EAST = a, b
        c.ns.travelData.edges[1] = c.lua.table_from(
            {'from': 'WEST', 'to': 'EAST', 'method': 'walk', 'seconds': 0})
        metric, _ = costs(c)
        self.assertEqual(metric(a, b)[1], 'blocked')

    def test_loading_checkpoint_keeps_costs_and_explicit_reset_clears_them(self):
        c = terrain_client(); metric, reset = costs(c)
        a, b = point(c, 501, .35), point(c, 501, .65)
        before = metric(a, b)
        reset(True)
        self.assertEqual(metric(a, b), before)
        reset()
        self.assertEqual(metric(a, b), before)

    def test_corner_graph_does_not_leak_into_default_flight_geometry(self):
        c = terrain_client(); metric, _ = costs(c)
        a, b = point(c, 501, .1), point(c, 501, .9)
        old_nodes = len(c.ns.travelData.nodes)
        self.assertEqual(metric(a, b)[1], 'network-estimate')
        self.assertEqual(len(c.ns.travelData.nodes), old_nodes)
        self.assertIsNone(c.ns.PublishedTravelDistance('TERRAIN_501_1_1', 'TERRAIN_501_1_2'))

    def test_unknown_physical_scale_cannot_price_visibility_as_a_known_route(self):
        c = terrain_client()
        c.lua.execute('C_Map.GetMapWorldSize=function() return secret,secret end;C_Map.GetWorldPosFromMapPos=nil')
        metric, _ = costs(c)
        self.assertEqual(metric(point(c, 501, .35), point(c, 501, .65))[1], 'blocked')

    def test_new_terrain_cost_snapshot_does_not_reuse_an_old_corner_graph(self):
        c = terrain_client(); first, _ = costs(c)
        a, b = point(c, 501, .35), point(c, 501, .65)
        self.assertEqual(first(a, b)[1], 'network-estimate')
        c.ns.travelTerrainData = c.lua.table_from({'maps': {}}, recursive=True)
        second, _ = costs(c)
        self.assertEqual(second(a, b)[1], 'local-estimate')
        self.assertEqual(first(a, b)[1], 'network-estimate')

    def test_terrain_comparison_starts_after_established_ready_rewards(self):
        def setup():
            c, plan, _ = reward_fixture(reward=100, handin_x=.4)
            metric = c.lua.eval("function(a,b) return math.abs(a.x-b.x)*1000,'network-estimate' end")
            # A tempting new path price makes an earlier reward visit costly.
            terrain = c.lua.eval('''function(a,b)
                return math.abs(a.x-b.x)*1000+(b.x==.4 and b.kind=='t' and a.kind~='t' and 1000 or 0),'network-estimate'
            end''')
            return c, plan, metric, terrain
        a, original, old_cost, _ = setup()
        a.ns.OptimizeFixedPlan(original, old_cost, False, None, old_cost)
        baseline = sequence(original)
        b, plan, old_cost, terrain_cost = setup()
        # Tokens and reward facts represent the identical starting/ending work.
        tokens = {(s.id, s.kind): s for s in plan.values()}
        original = b.lua.table_from([tokens[token] for token in baseline])
        model = b.ns.NewGuideFlowModel(original, terrain_cost)
        before = model.evaluate(original)
        result = b.ns.OptimizeFixedPlan(plan, old_cost, False, None, old_cost, None, terrain_cost)
        after = model.evaluate(plan)
        self.assertIsNotNone(result.terrain)
        self.assertTrue(after.valid)
        self.assertLessEqual(after.distance, before.distance)
        for stop, reward in before.workRewards.items():
            self.assertGreaterEqual(after.workRewards[stop], reward)

    def test_identical_geography_retains_established_order_without_extra_search(self):
        c, plan, metric = fixture()
        old = c.lua.table_from(list(plan.values()))
        c.ns.OptimizeFixedPlan(old, metric, False, None, metric)
        result = c.ns.OptimizeFixedPlan(plan, metric, False, None, metric, None, metric)
        self.assertIsNone(result.terrain)
        self.assertEqual(sequence(plan), sequence(old))

    def test_loading_yields_without_default_flight_queries_corrupting_corner_graph(self):
        c = terrain_client()
        c.lua.globals().flow_ns = c.ns
        c.lua.execute('''
        for i=1,240 do table.insert(flow_ns.travelData.edges,
            {from='absent',to='absent',method='walk',seconds=0}) end
        job=coroutine.create(function()
            local cost=flow_ns.NewFixedTravelCost(function(a,b)
                return math.sqrt((a.x-b.x)^2+(a.y-b.y)^2)*1000 end,true)
            return cost({mapID=501,x=.1,y=.37},{mapID=501,x=.9,y=.37})
        end)
        resumes=0
        while coroutine.status(job)~='dead' do
            assert(flow_ns.PublishedTravelDistance('TERRAIN_501_1_1','TERRAIN_501_1_2')==nil)
            local ok,length,basis=coroutine.resume(job);assert(ok,length)
            resumes=resumes+1;assert(resumes<100)
            if coroutine.status(job)=='dead' then assert(length>1000 and basis=='network-estimate') end
        end
        ''')
        self.assertGreater(c.lua.globals().resumes, 1)


def scheduler_client(timer):
    c = guide_client(2); g = zone(c)
    c.ns.GenerateFixedGuide(g, False)
    c.lua.globals().schedule_ns = c.ns
    c.lua.execute('''
    local original=schedule_ns.BuildGuideRoute
    schedule_ns.ScanGuideProgress=function() end
    work_count=0
    schedule_ns.BuildGuideRoute=function(guide)
        for i=1,40 do work_count=work_count+1;coroutine.yield() end
        return original(guide,true,false)
    end
    timers={};delays={}
    ''' + timer)
    c.ns.PlanLevelingGuide(g, False)
    return c, g


def one_callback(c):
    c.lua.eval('table.remove')(c.lua.globals().timers, 1)()


class PlanningBudgetTests(unittest.TestCase):
    def test_small_yields_share_callbacks_without_changing_route(self):
        c, g = scheduler_client('function debugprofilestop() return 0 end')
        before = order(g)
        one_callback(c)
        self.assertEqual(c.lua.globals().work_count, 16)
        self.assertIsNotNone(c.ns.routePlanning)
        self.assertLess(run_plan(c), 8)
        self.assertEqual(order(c.ns.routeSelection), before)

    def test_elapsed_time_budget_returns_control_before_finishing(self):
        c, _ = scheduler_client('cpu_clock=0;function debugprofilestop() cpu_clock=cpu_clock+1;return cpu_clock end')
        one_callback(c)
        self.assertEqual(c.lua.globals().work_count, 3)
        self.assertIsNotNone(c.ns.routePlanning)
        run_plan(c)
        self.assertIsNone(c.ns.routePlanningError)

    def test_missing_private_invalid_or_backwards_clock_retains_single_resume(self):
        timers = ('debugprofilestop=nil', 'function debugprofilestop()return secret end',
                  'function debugprofilestop()return 0/0 end',
                  'function debugprofilestop()return math.huge end',
                  'cpu_clock=11;function debugprofilestop()cpu_clock=cpu_clock-1;return cpu_clock end')
        for timer in timers:
            with self.subTest(timer=timer):
                c, _ = scheduler_client(timer)
                one_callback(c)
                self.assertEqual(c.lua.globals().work_count, 1)
                self.assertIsNotNone(c.ns.routePlanning)

    def test_cancelled_or_failed_job_cannot_publish_a_stale_route(self):
        for failure in (False, True):
            with self.subTest(failure=failure):
                c, _ = scheduler_client('function debugprofilestop()return 0 end')
                c.lua.globals().fail_job = failure
                c.lua.execute('''
                schedule_ns.BuildGuideRoute=function()
                    coroutine.yield()
                    if fail_job then error('fixture job failed') end
                    schedule_ns.CancelGuidePlanning();coroutine.yield()
                    error('cancelled job must not resume')
                end
                ''')
                one_callback(c)
                self.assertIsNone(c.ns.routePlanning)
                self.assertIsNone(c.ns.preparedLevelingRoute)
                self.assertIsNone(c.ns.routeSelection)
                if failure:
                    self.assertIn('fixture job failed', c.ns.routePlanningErrorDetail)


if __name__ == '__main__':
    unittest.main()
