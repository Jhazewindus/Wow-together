"""The route engine: one place that turns a set of spots into the loop with the least walking."""
import time
import unittest

from test_addon import Client


SETUP = r'''
    local ns = ...
    -- A zone 1000 yards wide and 500 tall: the map is not square, and distance must respect that.
    C_Map = C_Map or {}
    C_Map.GetMapWorldSize = function() return 1000, 500 end
    here = nil
    ns.PlayerPoint = function(mapID) return here end
    function spots(list)
        local out = {}
        for index, entry in ipairs(list) do out[index] = {mapID = 1424, x = entry[1], y = entry[2], value = entry[3], name = index} end
        return out
    end
    function names(plan)
        local out = {}
        for index = 1, #plan.points - 1 do out[index] = plan.points[index].name end
        return out
    end
'''


def engine():
    c = Client(quests=(), default_guide=True, party_mode='never')
    c.drain()
    c.lua.execute(SETUP, c.ns)
    return c


def plan(c, entries, options=None):
    points = c.lua.globals().spots(c.lua.table_from([c.lua.table_from(entry) for entry in entries]))
    result = c.ns.PlanLoop(points, c.lua.table_from(options) if options is not None else None)
    return result[0] if isinstance(result, tuple) else result


class OrderTests(unittest.TestCase):
    def test_a_handful_of_stops_come_back_in_the_shortest_order(self):
        c = engine()
        # The corners of a rectangle, given in a crossing order.
        loop = plan(c, [(0.1, 0.1), (0.9, 0.9), (0.9, 0.1), (0.1, 0.9)])
        order = list(c.lua.globals().names(loop).values())
        self.assertIn(order, ([1, 3, 2, 4], [1, 4, 2, 3]))                          # Round the edge, not across the middle.
        self.assertAlmostEqual(loop.yards, 2 * 800 + 2 * 400, delta=1)              # 800 yards wide, 400 tall.
        self.assertAlmostEqual(loop.seconds, 2400 / 7, delta=1)
        self.assertEqual((loop.stops, loop.available), (4, 4))

    def test_distance_uses_the_zones_real_proportions(self):
        c = engine()
        # Two spots the same map-distance from the first: one across (far in yards), one down (near in yards).
        loop = plan(c, [(0.5, 0.5), (0.9, 0.5), (0.5, 0.9)])
        self.assertAlmostEqual(loop.yards, 400 + 200 + (400 ** 2 + 200 ** 2) ** 0.5, delta=1)


class ChooseTests(unittest.TestCase):
    def test_with_more_spots_than_a_loop_holds_it_keeps_the_ones_that_lie_together(self):
        c = engine()
        tight = [(0.10 + (i % 6) * 0.01, 0.10 + (i // 6) * 0.02) for i in range(30)]
        scattered = [(0.30 + i * 0.02, 0.95 - i * 0.02) for i in range(30)]
        loop = plan(c, scattered + tight)
        self.assertEqual((loop.stops, loop.available), (24, 60))
        kept = list(c.lua.globals().names(loop).values())
        self.assertTrue(all(name > 30 for name in kept))                            # All from the tight group.

    def test_a_valuable_spot_a_little_out_of_the_way_still_makes_the_loop(self):
        c = engine()
        tight = [(0.10 + (i % 6) * 0.01, 0.10 + (i // 6) * 0.02) for i in range(30)]
        plain = plan(c, tight + [(0.18, 0.20)], {'stops': 24})
        self.assertNotIn(31, list(c.lua.globals().names(plain).values()))
        rich = plan(c, tight + [(0.18, 0.20, 50)], {'stops': 24})                   # The same spot, worth fifty times as much.
        self.assertIn(31, list(c.lua.globals().names(rich).values()))

    def test_the_number_of_stops_can_be_set_and_never_exceeds_twenty_four(self):
        c = engine()
        many = [(0.02 * i + 0.01, 0.5) for i in range(40)]
        self.assertEqual(plan(c, many, {'stops': 8}).stops, 8)
        self.assertEqual(plan(c, many, {'stops': 60}).stops, 24)

    def test_eighty_spots_are_planned_quickly(self):
        c = engine()
        many = [((i * 37 % 97) / 100 + 0.01, (i * 53 % 89) / 100 + 0.01) for i in range(80)]
        began = time.time()
        loop = plan(c, many)
        self.assertLess(time.time() - began, 0.5)                                   # The game runs Lua about ten times slower.
        self.assertEqual(loop.stops, 24)


class SizingTests(unittest.TestCase):
    """The loop is as long as a spot takes to come back, and no longer."""

    TIGHT = [(0.10 + (i % 5) * 0.01, 0.10 + (i // 5) * 0.02) for i in range(10)]    # Ten spots ten yards apart.
    FAR = [(0.50 + i * 0.04, 0.80) for i in range(10)]                             # Ten more, a long walk away and spread out.

    def test_without_a_respawn_time_it_takes_as_many_stops_as_it_may(self):
        c = engine()
        self.assertEqual(plan(c, self.TIGHT + self.FAR).stops, 20)

    def test_when_the_near_spots_fill_the_respawn_time_it_does_not_walk_to_the_far_ones(self):
        c = engine()
        # Ten seconds to work a spot, a hundred for it to come back: the ten near spots are a lap of a little over a hundred.
        loop = plan(c, self.TIGHT + self.FAR, {'respawn': 100, 'harvestSeconds': 10})
        self.assertEqual(loop.stops, 10)
        self.assertTrue(all(name <= 10 for name in c.lua.globals().names(loop).values()))
        self.assertGreaterEqual(loop.lapSeconds, 100)
        self.assertIsNone(loop.short)

    def test_a_long_respawn_makes_a_long_loop(self):
        c = engine()
        short = plan(c, self.TIGHT + self.FAR, {'respawn': 100, 'harvestSeconds': 10})
        long = plan(c, self.TIGHT + self.FAR, {'respawn': 900, 'harvestSeconds': 10})
        self.assertGreater(long.stops, short.stops)

    def test_a_quick_respawn_never_sends_you_to_the_far_spots(self):
        c = engine()
        loop = plan(c, self.TIGHT + self.FAR, {'respawn': 40, 'harvestSeconds': 10})
        self.assertLessEqual(loop.stops, 10)                                        # Near spots only: as good an hour, and more
        self.assertTrue(all(name <= 10 for name in c.lua.globals().names(loop).values()))   # forgiving if the respawn guess is off.
        self.assertGreaterEqual(loop.lapSeconds, 40)

    def test_it_says_so_when_every_spot_is_still_not_enough(self):
        c = engine()
        loop = plan(c, self.TIGHT, {'respawn': 600, 'harvestSeconds': 5})           # Ten spots, a lap of about a minute.
        self.assertEqual(loop.stops, 10)
        self.assertGreater(loop.short, 400)                                         # Hundreds of seconds short of the respawn.

    def test_the_lap_includes_the_time_spent_at_each_stop(self):
        c = engine()
        walking = plan(c, self.TIGHT, {'respawn': 1, 'harvestSeconds': 0})
        working = plan(c, self.TIGHT, {'respawn': 1, 'harvestSeconds': 30})
        self.assertAlmostEqual(working.lapSeconds - working.seconds, working.stops * 30, delta=0.01)
        self.assertAlmostEqual(walking.lapSeconds, walking.seconds, delta=0.01)

    def test_sizing_eighty_spots_is_still_quick(self):
        c = engine()
        many = [((i * 37 % 97) / 100 + 0.01, (i * 53 % 89) / 100 + 0.01) for i in range(80)]
        began = time.time()
        loop = plan(c, many, {'respawn': 300, 'harvestSeconds': 8})
        self.assertLess(time.time() - began, 0.6)
        self.assertGreaterEqual(loop.stops, 3)


class ArrivalTests(unittest.TestCase):
    def test_a_module_hears_each_time_the_player_reaches_a_stop(self):
        c = engine()
        c.lua.execute('''
            local ns = ...
            ns.RegisterModule("RouteTest", {})
            arrivals = {}
            local points = {}
            for i = 1, 4 do points[i] = {mapID = 1424, x = 0.1 + i * 0.1, y = 0.5, label = "Vein", reason = "known spot"} end
            started = {WowTogetherModuleAPI.StartModuleLoop("RouteTest", {title = "Four veins", points = points, onStop = function() end,
                respawn = 300, harvestSeconds = 8, onArrive = function(visited, stops) arrivals[#arrivals + 1] = visited .. "/" .. stops end})}
        ''', c.ns)
        g = c.lua.globals()
        self.assertTrue(g.started[1], g.started[2])
        self.assertEqual(c.ns.lastModuleLoopPlan.respawn, 300)
        refused = c.lua.eval('''function()
            return WowTogetherModuleAPI.StartModuleLoop("RouteTest", {title = "Bad", points = {{mapID = 1424, x = 0.5, y = 0.5, label = "a", reason = "b"}},
                onStop = function() end, respawn = -5})
        end''')()
        self.assertFalse(refused[0])


class StartTests(unittest.TestCase):
    def test_the_loop_begins_at_the_stop_nearest_the_player(self):
        c = engine()
        corners = [(0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9)]
        c.lua.execute('here = {mapID = 1424, x = 0.85, y = 0.85}')
        loop = plan(c, corners)
        self.assertEqual(c.lua.globals().names(loop)[1], 3)
        self.assertTrue(loop.startsNearPlayer)
        self.assertAlmostEqual(loop.yards, 2400, delta=1)                           # Turning it does not change its length.
        self.assertEqual(loop.points[1].name, loop.points[5].name)                  # Still closed.

    def test_a_player_elsewhere_or_a_plan_only_for_measuring_leaves_it_as_it_is(self):
        c = engine()
        corners = [(0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9)]
        self.assertFalse(plan(c, corners).startsNearPlayer)                         # Position not known.
        c.lua.execute('here = {mapID = 1424, x = 0.85, y = 0.85}')
        self.assertFalse(plan(c, corners, {'from': False}).startsNearPlayer)


class RefusalTests(unittest.TestCase):
    def test_nothing_too_much_and_nonsense_are_refused_with_a_reason(self):
        c = engine()
        empty = c.ns.PlanLoop(c.lua.table())
        self.assertIsNone(empty[0]); self.assertIn('No spots', empty[1])
        too_many = c.ns.PlanLoop(c.lua.globals().spots(c.lua.table_from([c.lua.table_from((0.01 * (i % 90) + 0.01, 0.5)) for i in range(81)])))
        self.assertIsNone(too_many[0]); self.assertIn('Too many', too_many[1])
        bad = c.ns.PlanLoop(c.lua.eval('{{mapID = 1424, x = 4, y = 0.5}}'))
        self.assertIsNone(bad[0])

    def test_one_spot_is_a_place_to_stand_not_an_error(self):
        c = engine()
        self.assertEqual(plan(c, [(0.5, 0.5)]).stops, 1)


class EveryLoopTests(unittest.TestCase):
    def test_a_loop_a_module_starts_is_planned_by_the_engine(self):
        c = engine()
        c.lua.execute('''
            local ns = ...
            ns.RegisterModule("RouteTest", {})
            local points = {}
            for i = 1, 30 do points[#points + 1] = {mapID = 1424, x = 0.10 + (i % 6) * 0.01, y = 0.10 + math.floor(i / 6) * 0.02, label = "Vein", reason = "known spot"} end
            for i = 1, 30 do points[#points + 1] = {mapID = 1424, x = 0.30 + i * 0.02, y = 0.95 - i * 0.02, label = "Vein", reason = "known spot"} end
            started = {WowTogetherModuleAPI.StartModuleLoop("RouteTest", {title = "Sixty veins", points = points, onStop = function() end})}
        ''', c.ns)
        g = c.lua.globals()
        self.assertTrue(g.started[1], g.started[2])
        made = c.ns.lastModuleLoopPlan
        self.assertEqual((made.stops, made.available), (24, 60))                    # Sixty offered, the best twenty-four walked.


if __name__ == '__main__':
    unittest.main()
