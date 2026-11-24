"""The addon's own performance record: what each slow moment was doing."""
import unittest

from test_addon import Client


class RecorderTests(unittest.TestCase):
    def recorder(self):
        c = Client(quests=(), default_guide=True)
        c.drain()
        c.lua.execute('''
            local ns = ...
            ms, seconds = 0, 100
            ns.PerfSetClock(function() return ms end)
            function GetTime() return seconds end
            lines = {}
        ''', c.ns)
        return c

    def test_events_refreshes_and_the_guide_window_are_timed_by_name(self):
        c = self.recorder(); ns = c.ns
        c.lua.execute('''
            local ns = ...
            ns.On("QUEST_LOG_UPDATE", function() ms = ms + 80 end)        -- an 80 ms handler
            ns.frame.OnEvent(ns.frame, "QUEST_LOG_UPDATE")
            local path = ns.PerfBegin("path", true); ms = ms + 2; ns.PerfEnd("path", path)
            local card = ns.PerfBegin("card", true); ms = ms + 3; ns.PerfEnd("card", card)
            seconds = seconds + 6                                           -- the five-second window closes
            local again = ns.PerfBegin("card", true); ms = ms + 1; ns.PerfEnd("card", again)
            ns.PerfReport(function(text) lines[#lines + 1] = text end)
        ''', ns)
        text = ' '.join(c.lua.globals().lines.values())
        self.assertIn('1 windows of 5 s', text)
        self.assertIn('QUEST_LOG_UPDATE', text)
        self.assertIn('Slowest single calls (each is a visible hitch): QUEST_LOG_UPDATE 80 ms', text)
        record = ns.db.perfLog[1]
        self.assertIn('path', record.top)
        self.assertIn('card', record.top)
        self.assertNotIn('SAFE MODE', text)                         # This build records; it never slows itself down.
        self.assertIsNone(ns.EnterSafeMode)

    def test_a_refresh_reports_where_its_time_went_and_the_command_clears_the_record(self):
        c = self.recorder(); ns = c.ns
        c.lua.execute('''
            local ns = ...
            local route = ns.UpdateSelectedRoute
            ns.UpdateSelectedRoute = function(...) ms = ms + 40; return route(...) end
            local started = ns.PerfBegin("QUEST_ACCEPTED", true)
            ns.Refresh(true)
            ns.PerfEnd("QUEST_ACCEPTED", started)
            seconds = seconds + 6
            local tick = ns.PerfBegin("card", true); ns.PerfEnd("card", tick)
        ''', ns)
        record = ns.db.perfLog[1]
        self.assertIn('refresh:route 40ms', record.parts)           # Named inside the event that caused it.
        self.assertIn('QUEST_ACCEPTED', record.top)
        ns.PerfCommand('clear')
        self.assertEqual(len(list(ns.db.perfLog.values())), 0)


if __name__ == '__main__':
    unittest.main()


class CoverageTests(unittest.TestCase):
    """Nothing the addon does later, from a timer, is invisible to the record."""

    def test_work_started_from_a_timer_is_timed_under_its_name(self):
        c = RecorderTests().recorder(); ns = c.ns
        c.lua.execute('''
            local ns = ...
            timers = {}
            ns.After("plan", 0, function() ms = ms + 7 end)
            ns.After("timer:Example", 0, function() ms = ms + 90 end)
            for _, callback in ipairs(timers) do callback() end
            seconds = seconds + 6
            local tick = ns.PerfBegin("card", true); ns.PerfEnd("card", tick)
            ns.PerfReport(function(text) lines[#lines + 1] = text end)
        ''', ns)
        record = ns.db.perfLog[1]
        self.assertIn('timer:Example 90ms/1', record.top)
        self.assertIn('plan 7ms/1', record.top)
        self.assertIn('timer:Example 90 ms', ' '.join(c.lua.globals().lines.values()))

    def test_no_file_starts_a_timer_behind_the_recorders_back(self):
        import os, re
        root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'WowTogether')
        offenders = []
        for name in sorted(os.listdir(root)):
            if name.endswith('.lua') and name != 'Perf.lua':
                text = open(os.path.join(root, name), encoding='utf-8').read()
                if 'C_Timer.After(' in text:
                    offenders.append(name)
        self.assertEqual(offenders, [])                              # Timers go through ns.After.


class ClosedWindowTests(unittest.TestCase):
    """A refresh caused by the game does not draw the main window while it is closed."""

    def client(self):
        c = Client(quests=(), default_guide=True)
        c.drain()
        c.lua.execute('local ns = ...; renders = 0; local render = ns.Render; ns.Render = function(...) renders = renders + 1; return render(...) end', c.ns)
        c.lua.execute('local ns = ...; ns.On("QUEST_DETAIL", function() ns.Refresh() end)', c.ns)
        return c

    def test_an_event_refresh_skips_the_closed_window_and_draws_the_open_one(self):
        c = self.client(); ns = c.ns; g = c.lua.globals()
        if ns.window.IsShown(ns.window):
            ns.ToggleWindow()
        g.renders = 0
        ns.frame.OnEvent(ns.frame, "QUEST_DETAIL")
        self.assertEqual(g.renders, 0)                               # Closed: nothing drawn at the quest giver.
        ns.Refresh()
        self.assertGreaterEqual(g.renders, 1)                        # Asked for by the interface itself: drawn.
        ns.ToggleWindow(); c.drain()
        g.renders = 0
        ns.frame.OnEvent(ns.frame, "QUEST_DETAIL")
        self.assertGreaterEqual(g.renders, 1)                        # Open: kept up to date.


class GlanceCommandTests(unittest.TestCase):
    def test_the_command_switches_glance_both_ways(self):
        c = Client(quests=(), default_guide=True)
        c.drain()
        c.lua.execute('local ns = ...; printed = {}; ns.Print = function(text) printed[#printed + 1] = text end', c.ns)
        before = bool(c.ns.Option('guideGlance'))
        c.lua.globals().SlashCmdList["WOWTOGETHER"]('glance')
        self.assertEqual(bool(c.ns.Option('guideGlance')), not before)
        c.lua.globals().SlashCmdList["WOWTOGETHER"]('glance')
        self.assertEqual(bool(c.ns.Option('guideGlance')), before)
        self.assertEqual(len(list(c.lua.globals().printed.values())), 2)


class KillRefreshTests(unittest.TestCase):
    """One kill with loot raises several events; they must become one refresh, not one each."""

    EVENTS = ("QUEST_LOG_UPDATE", "UNIT_QUEST_LOG_CHANGED", "QUEST_WATCH_UPDATE", "BAG_UPDATE_DELAYED", "QUEST_POI_UPDATE")

    def client(self):
        # Playing alone, as the report came from: party sync has its own refreshes and is not part of this.
        c = Client(quests=(), default_guide=True, party_mode='never')
        c.drain()
        c.lua.execute('''
            local ns = ...
            refreshes = 0
            local refresh = ns.Refresh
            ns.Refresh = function(...) refreshes = refreshes + 1; return refresh(...) end
            clock = 1000
            function GetTime() return clock end
            timers = {}
        ''', c.ns)
        return c

    def fire(self, c, event):
        if event == "UNIT_QUEST_LOG_CHANGED":
            c.ns.frame.OnEvent(c.ns.frame, event, "player")
        else:
            c.ns.frame.OnEvent(c.ns.frame, event)

    def run_timers(self, c, advance=0.25, rounds=40):
        for _ in range(rounds):
            if not len(c.lua.globals().timers):
                break
            c.lua.execute('clock = clock + %f' % advance)
            c.lua.eval('function() local list = timers; timers = {}; for _, callback in ipairs(list) do callback() end end')()

    def test_the_events_of_one_kill_cause_a_single_refresh(self):
        c = self.client(); g = c.lua.globals()
        for event in self.EVENTS:                                    # All within a moment of each other.
            self.fire(c, event)
            c.lua.execute('clock = clock + 0.05')
        self.assertEqual(g.refreshes, 0)                             # None straight away, in the middle of the fight.
        self.run_timers(c)
        self.assertEqual(g.refreshes, 1)                             # One, once things have settled.

    def test_a_long_run_of_events_is_not_starved(self):
        c = self.client(); g = c.lua.globals()
        pop = c.lua.eval('function() local list = timers; timers = {}; for _, callback in ipairs(list) do callback() end end')
        for _ in range(12):                                          # Events every 0.1 s for 1.2 s: never a quiet moment.
            self.fire(c, "BAG_UPDATE_DELAYED")
            c.lua.execute('clock = clock + 0.1')
            pop()
        self.assertGreaterEqual(g.refreshes, 1)                      # Still refreshed within three quarters of a second.
        self.assertLessEqual(g.refreshes, 2)

    def test_a_refresh_the_interface_asks_for_is_immediate(self):
        c = self.client(); g = c.lua.globals()
        c.ns.ScheduleRefresh()
        self.assertEqual(g.refreshes, 1)
        c.ns.ScheduleRefresh(True)                                   # A background one waits with the rest.
        self.assertEqual(g.refreshes, 1)


class BuildStampTests(unittest.TestCase):
    def test_reports_and_the_login_line_say_which_test_build_this_is(self):
        c = Client(quests=(), default_guide=True)
        c.drain()
        c.lua.execute('''
            local ns = ...
            ns.testBuild = "2026-11-23 15:00 example"
            lines, ms, seconds = {}, 0, 100
            ns.PerfSetClock(function() return ms end)
            function GetTime() return seconds end
            local a = ns.PerfBegin("card", true); ms = ms + 2; ns.PerfEnd("card", a)
            seconds = seconds + 6
            local b = ns.PerfBegin("card", true); ns.PerfEnd("card", b)
            ns.PerfReport(function(text) lines[#lines + 1] = text end)
        ''', c.ns)
        self.assertEqual(list(c.lua.globals().lines.values())[0], 'Test build: 2026-11-23 15:00 example.')
        import os
        stamp = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'WowTogether', 'BuildStamp.lua'), encoding='utf-8').read()
        self.assertRegex(stamp, r'ns\.testBuild = (nil|"[^"]+")')      # A stamp on a test build, nil in the repository.
