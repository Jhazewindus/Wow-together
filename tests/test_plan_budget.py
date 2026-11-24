"""Route planning hands the frame back by the clock, so its cost per frame is bounded."""
import unittest

from test_leveling_path import scene, drain


def plan(c, zone, clock, limit=60000):
    ns = c.ns
    if clock:
        c.lua.execute('profile = 0; readings = 0; function debugprofilestop() profile = profile + 1; readings = readings + 1; return profile end')
    else:
        c.lua.execute('debugprofilestop = nil; readings = 0')
    guide = next(g for g in ns.LevelingGuideChoices().values() if g.mode == 'zone' and zone in (g.zone or ''))
    ns.ShowGuideOnMap(guide)
    frames, worst = 0, 0
    pop = c.lua.eval('function() local callback = table.remove(timers, 1); callback() end')
    while len(c.lua.globals().timers) and frames < limit:
        before = c.lua.globals().readings
        pop(); frames += 1
        worst = max(worst, c.lua.globals().readings - before)
    route = ns.selectedRoute
    stops = [(stop.id, stop.kind) for stop in route.stops.values()] if route and route.stops else []
    return frames, worst, stops


class PlanBudgetTests(unittest.TestCase):
    def test_the_rule_counts_without_a_clock_and_stops_on_time_with_one(self):
        c = scene(32, 0.3); ns = c.ns
        c.lua.execute('local ns = ...; ns.planSliceStart = nil', ns)
        self.assertTrue(ns.PlanShouldYield(200, 200))
        self.assertFalse(ns.PlanShouldYield(201, 200))
        c.lua.execute('local ns = ...; now = 100; function debugprofilestop() return now end; ns.planSliceStart = 100', ns)
        self.assertFalse(ns.PlanShouldYield(200, 200))               # A slice has only just begun.
        c.lua.execute('now = 104.9')
        self.assertFalse(ns.PlanShouldYield(204, 200))
        c.lua.execute('now = 105')
        self.assertFalse(ns.PlanShouldYield(205, 200))               # The clock is read on every fourth item only.
        self.assertTrue(ns.PlanShouldYield(208, 200))                # Five milliseconds used: hand the frame back.
        c.lua.execute('now = 50')
        self.assertTrue(ns.PlanShouldYield(212, 200))                # A clock that runs backwards is not trusted.

    def test_a_planned_route_is_the_same_with_and_without_the_clock(self):
        counted = plan(scene(32, 0.3), 'Hillsbrad', clock=False)
        timed = plan(scene(32, 0.3), 'Hillsbrad', clock=True)
        self.assertTrue(counted[2])
        self.assertEqual(timed[2], counted[2])                       # Pacing changes when it pauses, not what it decides.

    def test_each_frame_of_planning_stops_once_its_time_is_used(self):
        # A big zone, watched for its first three thousand frames of planning.
        frames, worst, stops = plan(scene(22, 0.3), 'The Barrens', clock=True, limit=3000)
        self.assertEqual(frames, 3000)                               # It takes many frames...
        self.assertLessEqual(worst, 12)                              # ...and none runs on past its few milliseconds of clock.


if __name__ == '__main__':
    unittest.main()
