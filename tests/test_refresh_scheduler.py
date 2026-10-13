"""Background invalidations coalesce without changing direct refresh actions."""
import unittest

from test_addon import Client


class RefreshSchedulerTests(unittest.TestCase):
    def test_coalesces_background_requests_and_keeps_foreground_refresh_visible(self):
        client = Client(quests=(), default_guide=True)
        client.drain()
        client.lua.execute("timers, delays = {}, {}")
        client.ns.refreshStats = client.lua.table_from({"requested": 0, "coalesced": 0, "completed": 0})
        client.lua.globals().refreshRuns = 0
        client.ns.Refresh = client.lua.eval(
            "function(background) refreshRuns=refreshRuns+1; refreshBackground=background end")

        client.ns.ScheduleRefresh(True)
        client.ns.ScheduleRefresh(True)
        client.ns.ScheduleRefresh(False)
        self.assertEqual(client.lua.globals().refreshRuns, 1)
        self.assertTrue(client.lua.globals().refreshBackground)
        self.assertEqual(len(client.lua.globals().timers), 1)
        client.drain()
        self.assertEqual(client.lua.globals().refreshRuns, 2)
        self.assertFalse(client.lua.globals().refreshBackground)
        self.assertEqual(client.ns.refreshStats.requested, 3)
        self.assertEqual(client.ns.refreshStats.coalesced, 2)
        self.assertEqual(client.ns.refreshStats.completed, 2)

        client.ns.Refresh(False)
        self.assertEqual(client.lua.globals().refreshRuns, 3)


if __name__ == "__main__":
    unittest.main()
