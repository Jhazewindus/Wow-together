"""Exact host checks for live leveling-trip ordering."""
import math
import random
import re
import unittest
from pathlib import Path

from lupa.lua51 import LuaRuntime
from test_addon import Client
from test_routes import catalogue, guide, quest


ROOT = Path(__file__).resolve().parents[1]
PRELUDE = r'''
ns = {}
function ns.ValidTravelPoint(p) return type(p)=="table" and type(p.x)=="number" and type(p.y)=="number" and p.mapID end
WORLD_CALLS = 0
C_Map = {GetMapWorldSize = function() WORLD_CALLS = WORLD_CALLS + 1; return 5000, 3500 end}
function ns.ReadPublic(f, ...) return f(...) end
function ns.NormalizedDistance(a,b)
    if not ns.ValidTravelPoint(a) or not ns.ValidTravelPoint(b) or a.mapID~=b.mapID then return math.huge end
    return math.sqrt(((a.x-b.x)*1.5)^2+(a.y-b.y)^2)
end
function ns.WalkingDistance(mapID, a, b, metrics)
    if not ns.ValidTravelPoint(a) or not ns.ValidTravelPoint(b) then return end
    local w,h
    local c=metrics and metrics[mapID]
    if c then w,h=c[1],c[2]
    else w,h=ns.ReadPublic(C_Map.GetMapWorldSize,mapID); if metrics then metrics[mapID]={w,h} end end
    return math.sqrt(((a.x-b.x)*w)^2+((a.y-b.y)*h)^2)
end
function ns.Option() return 0.16 end
'''


def optimizer_runtime(force_beam=False, expose_batch=False):
    runtime = LuaRuntime(unpack_returned_tuples=True)
    runtime.execute(PRELUDE)
    source = (ROOT / 'WowTogether' / 'GuideOptimizer.lua').read_text()
    source = source.replace('local addonName, ns = ...', '')
    if force_beam:
        source, count = re.subn(r'local EXACT_STATE_BUDGET = 60000',
                                'local EXACT_STATE_BUDGET = 0', source, count=1)
        if count != 1:
            raise AssertionError('exact state budget declaration not found')
    if expose_batch:
        source, count = source.replace('local function orderKey(state)',
                                       'ns.ChooseBatch = chooseBatch\nlocal function orderKey(state)', 1), source.count('local function orderKey(state)')
        if count != 1:
            raise AssertionError('batch selection function not found')
    runtime.execute(source)
    return runtime


def lua_tasks(runtime, tasks):
    result = runtime.table()
    for i, (quest_id, coords) in enumerate(tasks, 1):
        stages = runtime.table()
        for j, (x, y) in enumerate(coords, 1):
            kind = 'a' if j == 1 else 't' if j == len(coords) else 'q'
            stages[j] = runtime.table_from({'id': quest_id, 'kind': kind, 'x': x, 'y': y, 'mapID': 1})
        result[i] = runtime.table_from({'id': quest_id, 'stages': stages})
    return result


def lua_position(runtime, position):
    return runtime.table_from({'mapID': 1, 'x': position[0], 'y': position[1]}) if position else None


def optimize(runtime, tasks, position):
    runtime.globals().WORLD_CALLS = 0
    stops, cost, method = runtime.globals().ns.OptimizeTripOrder(
        lua_tasks(runtime, tasks), 1, lua_position(runtime, position), False)
    order = [(int(stops[i].id), str(stops[i].kind), float(stops[i].x), float(stops[i].y))
             for i in range(1, len(stops) + 1)]
    return order, float(cost), str(method), int(runtime.globals().WORLD_CALLS)


def distance(a, b):
    return math.hypot((a[0] - b[0]) * 5000, (a[1] - b[1]) * 3500)


def walked_cost(order, position):
    total, last = 0.0, position
    for _, _, x, y in order:
        current = (x, y)
        if last is not None:
            total += distance(last, current)
        last = current
    return total


def assert_valid_order(test, order, tasks):
    expected = {quest_id: coords for quest_id, coords in tasks}
    offsets = {quest_id: 0 for quest_id, _ in tasks}
    for quest_id, _, x, y in order:
        test.assertIn(quest_id, expected)
        offset = offsets[quest_id]
        test.assertLess(offset, len(expected[quest_id]))
        test.assertEqual((x, y), expected[quest_id][offset])
        offsets[quest_id] += 1
    test.assertEqual(offsets, {quest_id: len(coords) for quest_id, coords in tasks})


def brute_cost(tasks, position):
    best = math.inf
    progress = [0] * len(tasks)

    def visit(last, cost):
        nonlocal best
        if cost >= best:
            return
        if all(progress[i] == len(tasks[i][1]) for i in range(len(tasks))):
            best = cost
            return
        for i, (_, coords) in enumerate(tasks):
            if progress[i] < len(coords):
                point = coords[progress[i]]
                progress[i] += 1
                visit(point, cost + (distance(last, point) if last is not None else 0.0))
                progress[i] -= 1

    visit(position, 0.0)
    return best


class TripOrderingTests(unittest.TestCase):
    def test_small_trips_are_valid_and_match_brute_force(self):
        runtime = optimizer_runtime()
        rng = random.Random(7)
        for case in range(25):
            task_count = rng.randint(2, 4)
            tasks = []
            for i in range(task_count):
                stages = rng.randint(2, 3)
                coords = [(round(rng.random(), 5), round(rng.random(), 5)) for _ in range(stages)]
                tasks.append((1000 + case * 10 + i, coords))
            position = (round(rng.random(), 5), round(rng.random(), 5)) if case % 3 else None
            order, cost, method, _ = optimize(runtime, tasks, position)
            self.assertEqual(method, 'exact')
            assert_valid_order(self, order, tasks)
            self.assertAlmostEqual(cost, walked_cost(order, position), places=6)
            self.assertAlmostEqual(cost, brute_cost(tasks, position), places=6)

    def test_exact_beats_or_matches_beam_and_fallback_keeps_legacy_order(self):
        tasks = [
            (41, [(0.84, 0.12), (0.51, 0.35), (0.31, 0.8)]),
            (42, [(0.15, 0.78), (0.34, 0.42), (0.65, 0.18)]),
            (43, [(0.8, 0.86), (0.55, 0.65), (0.18, 0.25)]),
        ]
        position = (0.1, 0.1)
        exact, exact_cost, exact_method, _ = optimize(optimizer_runtime(), tasks, position)
        beam, beam_cost, beam_method, _ = optimize(optimizer_runtime(force_beam=True), tasks, position)
        self.assertEqual(exact_method, 'exact')
        self.assertEqual(beam_method, 'beam')
        self.assertLessEqual(exact_cost, beam_cost + 1e-6)
        self.assertEqual(beam, [
            (42, 'a', 0.15, 0.78), (42, 'q', 0.34, 0.42), (42, 't', 0.65, 0.18),
            (41, 'a', 0.84, 0.12), (43, 'a', 0.8, 0.86), (43, 'q', 0.55, 0.65),
            (41, 'q', 0.51, 0.35), (43, 't', 0.18, 0.25), (41, 't', 0.31, 0.8),
        ])

    def test_cooperative_optimizer_yields_and_completes(self):
        tasks = [(2000 + i, [(i / 7, j / 5) for j in range(4 if i < 2 else 3)]) for i in range(6)]
        runtime = optimizer_runtime()
        result = runtime.eval(r'''
        function(tasks)
            local co=coroutine.create(function() return ns.OptimizeTripOrder(tasks,1,{mapID=1,x=.5,y=.5},true) end)
            local yields=0
            while true do
                local ok,a,b,c=coroutine.resume(co); assert(ok,a)
                if coroutine.status(co)=='dead' then return yields,a,b,c end
                yields=yields+1
            end
        end''')(lua_tasks(runtime, tasks))
        self.assertGreater(result[0], 0)
        self.assertEqual(len(result[1]), 20)
        self.assertEqual(result[3], 'exact')

    def test_world_size_is_cached_across_all_build_route_phases(self):
        client = Client(quests=())
        client.guide_environment(level=12)
        catalogue(client, {900: quest('First'), 901: quest('Second')})
        route_guide = guide(client, (900, 901))
        route_guide.mapID = 501
        client.ns.profile.mapID = 501
        client.lua.execute('''
        mapSizeCalls=0
        C_Map.GetMapWorldSize=function() mapSizeCalls=mapSizeCalls+1; return 5000,3500 end
        ''')
        route = client.ns.BuildLevelingRoute(route_guide, False, False)
        self.assertIn(route.tripSearch, ('exact', 'beam'))
        self.assertEqual(client.lua.globals().mapSizeCalls, 1)

    def test_fresh_batch_radius_uses_nearest_existing_trip_stop(self):
        runtime = optimizer_runtime(expose_batch=True)
        tasks = runtime.table()

        def task(quest_id, coords, active=False):
            stages = runtime.table()
            for i, (x, y) in enumerate(coords, 1):
                kind = 'a' if i == 1 else 't' if i == len(coords) else 'q'
                stages[i] = runtime.table_from({'id': quest_id, 'kind': kind, 'x': x, 'y': y, 'mapID': 1})
            tasks[quest_id - 10] = runtime.table_from({
                'id': quest_id, 'stages': stages, 'first': stages[1], 'xp': 0,
                'active': active, 'ready': False})

        task(11, [(0.2, 0), (0.2, 0), (0.2, 0)], active=True)
        task(12, [(0, 0), (1, 0), (0, 0)])
        selected = runtime.globals().ns.ChooseBatch(
            runtime.table_from({'batchIDs': runtime.table()}), tasks, 1,
            runtime.table_from({'mapID': 1, 'x': 0, 'y': 0}), runtime.table())
        self.assertEqual([int(selected[i].id) for i in range(1, len(selected) + 1)], [11, 12])


if __name__ == '__main__':
    unittest.main()
