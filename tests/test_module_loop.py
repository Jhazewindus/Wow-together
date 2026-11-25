"""A farm's walking loop is ordered at once: no path search per pair of points."""
import math
import unittest

import test_leveling_path as T


def ring(c, count, scramble=7):
    """Points round a circle in Stranglethorn Vale, deliberately out of order."""
    return c.lua.eval('''function(n, step)
        local points = {}
        for i = 1, n do
            local angle = ((i * step) % n) / n * 6.2832
            points[i] = {mapID = 1434, x = 0.40 + 0.12 * math.cos(angle), y = 0.30 + 0.12 * math.sin(angle),
                label = "Spawn " .. i, reason = "test"}
        end
        return points
    end''')(count, scramble)


def length(c, points):
    total, previous = 0, None
    for point in points:
        if previous is not None:
            total += c.ns.TravelPointDistance(previous, point)
        previous = point
    return total


class LoopOrderTests(unittest.TestCase):
    def setUp(self):
        self.c = T.scene(35, 0.3, map_id=1434, zone='Stranglethorn Vale', path=False)
        T.drain(self.c)
        self.c.lua.execute('local ns = ...; searches = 0; local find = ns.FindTravelPath; '
                           'ns.FindTravelPath = function(...) searches = searches + 1; return find(...) end', self.c.ns)

    def test_twenty_four_points_are_ordered_without_a_single_path_search(self):
        # It searched for a path between every pair: 552 searches, and the game froze when a farm was started.
        c = self.c
        points = ring(c, 24)
        loop = c.ns.TrailLoop(points)
        self.assertEqual(c.lua.globals().searches, 0)
        ordered = list(loop.points.values())
        self.assertEqual(len(ordered), 25)                                          # Every point once, and back to the first.
        self.assertEqual(ordered[0].label, ordered[-1].label)
        self.assertEqual(len({point.label for point in ordered}), 24)

    def test_the_loop_is_close_to_the_shortest_way_round(self):
        c = self.c
        points = ring(c, 24)
        scrambled = list(points.values()); scrambled.append(scrambled[0])
        loop = c.ns.TrailLoop(points)
        ordered = list(loop.points.values())
        around = length(c, ordered)
        self.assertLess(around, length(c, scrambled) * 0.5)                         # Far better than the order given.
        in_order = sorted(points.values(), key=lambda p: math.atan2(p.y - 0.30, p.x - 0.40))
        in_order.append(in_order[0])
        self.assertLess(around, length(c, in_order) * 1.1)                          # Within a tenth of walking the ring in order.

    def test_a_small_loop_is_still_ordered_exactly(self):
        c = self.c
        points = ring(c, 6, scramble=5)
        loop = c.ns.TrailLoop(points)
        ordered = list(loop.points.values())
        in_order = sorted(points.values(), key=lambda p: math.atan2(p.y - 0.30, p.x - 0.40))
        in_order.append(in_order[0])
        self.assertAlmostEqual(length(c, ordered), length(c, in_order), delta=1)
        self.assertEqual(c.lua.globals().searches, 0)

    def test_starting_a_loop_is_immediate_and_gives_every_point_a_stop(self):
        c = self.c
        c.lua.globals().points = ring(c, 24)
        result = c.lua.eval('''function()
            WowTogetherModuleAPI.RegisterModule("LoopTest", {})
            return WowTogetherModuleAPI.StartModuleLoop("LoopTest", {title = "Test", points = points, onStop = function() end})
        end''')()
        self.assertTrue(result if not isinstance(result, tuple) else result[0])
        self.assertEqual(len(list(c.ns.selectedRoute.stops.values())), 25)
        self.assertLess(c.lua.globals().searches, 30)                               # Not hundreds.


if __name__ == '__main__':
    unittest.main()
