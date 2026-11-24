"""The guide window reports its own state, can be reset, and survives a failing add-on part."""
import unittest

from test_addon import Client


def client():
    c = Client(quests=(), default_guide=True)
    c.drain()
    c.lua.execute('local ns = ...; printed = {}; ns.Print = function(text) printed[#printed + 1] = text end', c.ns)
    return c


class HudDiagnosticsTests(unittest.TestCase):
    def test_the_report_names_what_decides_what_is_drawn(self):
        c = client(); ns = c.ns
        c.lua.globals().SlashCmdList["WOWTOGETHER"]('hud')
        text = ' '.join(c.lua.globals().printed.values())
        for expected in ('Guide window: ', 'alpha', 'size', 'Glance', 'solid background', 'Header: title', 'Header buttons: pause',
                         'menu', 'close', 'path strip', 'travel button', 'Errors in the window\'s add-on parts: none recorded'):
            self.assertIn(expected, text)

    def test_a_failing_add_on_part_is_recorded_and_the_window_still_updates(self):
        c = client(); ns = c.ns
        c.lua.execute('local ns = ...; ns.UpdateLevelingPathStrip = function() error("strip broke") end; '
                      'ns.UpdateTravelButton = function() error("button broke") end', ns)
        ns.navigation.title.text = 'stale'
        ns.UpdateNavigation()                                         # Must not raise.
        self.assertIn('strip broke', ns.hudErrors['path strip'])
        self.assertIn('button broke', ns.hudErrors['travel button'])
        if ns.navigation.IsShown(ns.navigation):
            self.assertNotEqual(ns.navigation.title.text, 'stale')   # The window carried on past the failures.
        ns.HudDiagnostics()
        self.assertIn('path strip: ', list(c.lua.globals().printed.values())[-1])

    def test_reset_restores_the_full_solid_window_in_its_default_place(self):
        c = client(); ns = c.ns
        ns.SetOption('guideGlance', True); ns.SetOption('guideOpaque', False)
        nav = ns.navigation
        nav.SetAlpha(nav, 0.2)
        c.lua.globals().SlashCmdList["WOWTOGETHER"]('hud reset')
        self.assertFalse(ns.Option('guideGlance'))
        self.assertTrue(ns.Option('guideOpaque'))
        self.assertEqual(nav.alpha, 1)
        self.assertEqual(nav.point[1], 'BOTTOM')
        self.assertIn('Guide window reset', list(c.lua.globals().printed.values())[-1])

    def test_the_background_is_applied_even_when_an_attached_panel_is_missing(self):
        c = client(); ns = c.ns
        c.lua.execute('''
            local ns = ...
            local nav = ns.navigation
            fills, stripBorders = {}, {}
            nav.SetBackdropColor = function(self, r, g, b, a) fills[#fills + 1] = a end
            nav.pathStrip.SetBackdropBorderColor = function(self, r, g, b, a) stripBorders[#stripBorders + 1] = a end
            nav.work, nav.questItem = nil, nil          -- Two attached panels are missing.
        ''', ns)
        ns.SetOption('guideOpaque', True)
        ns.UpdateNavigationBackground()
        self.assertEqual(list(c.lua.globals().fills.values())[-1], 1)          # The window's own fill is set regardless.
        self.assertEqual(list(c.lua.globals().stripBorders.values())[-1], 0)   # And the strip, listed after the gap, is reached.


if __name__ == '__main__':
    unittest.main()


class CombatLayoutTests(unittest.TestCase):
    """The guide window carries secure buttons: it is never resized or re-laid-out during combat."""

    def window(self):
        c = client(); ns = c.ns
        c.lua.execute('''
            local ns = ...
            combat = false
            function InCombatLockdown() return combat end
            local nav = ns.navigation
            heights, anchors = {}, {}
            local setHeight = nav.SetHeight
            nav.SetHeight = function(self, value) heights[#heights + 1] = value; return setHeight(self, value) end
            local setPoint = nav.SetPoint
            nav.SetPoint = function(self, ...) anchors[#anchors + 1] = (...); return setPoint(self, ...) end
        ''', ns)
        ns.SetOption('guideGlance', False)
        ns.UpdateNavigation(); ns.LayoutNavigation()
        c.lua.execute('heights, anchors, printed = {}, {}, {}')
        return c

    def count(self, c, name):
        return len(list(c.lua.globals()[name].values()))

    def test_switching_mode_in_a_fight_waits_for_the_fight_to_end(self):
        c = self.window(); ns = c.ns; g = c.lua.globals()
        g.combat = True
        g.SlashCmdList["WOWTOGETHER"]('glance')
        self.assertTrue(ns.Option('guideGlance'))                    # The choice is remembered...
        self.assertFalse(ns.GlanceActive())                          # ...the window keeps its shape...
        self.assertTrue(ns.GlancePending())
        self.assertEqual(self.count(c, 'heights'), 0)                # ...and is not resized mid-fight.
        self.assertIn('when this fight ends', list(g.printed.values())[-1])
        for _ in range(3):
            ns.UpdateNavigation(); ns.LayoutNavigation()
        self.assertEqual(self.count(c, 'heights'), 0)
        g.combat = False
        ns.frame.OnEvent(ns.frame, "PLAYER_REGEN_ENABLED")
        self.assertTrue(ns.GlanceActive())                           # Now it switches.
        self.assertFalse(ns.GlancePending())

    def test_switching_mode_outside_combat_is_immediate(self):
        c = self.window(); ns = c.ns; g = c.lua.globals()
        g.SlashCmdList["WOWTOGETHER"]('glance')
        self.assertTrue(ns.GlanceActive())
        self.assertIn('Guide window: Glance.', list(g.printed.values())[-1])

    def test_switching_mode_never_changes_the_windows_height(self):
        c = self.window(); ns = c.ns; g = c.lua.globals()
        for _ in range(4):                                           # Glance, full, Glance, full.
            g.SlashCmdList["WOWTOGETHER"]('glance')
            ns.UpdateNavigation(); ns.LayoutNavigation()
        self.assertEqual(self.count(c, 'heights'), 0)                # The height change is what lost the window in play.

    def test_any_height_change_waits_for_combat_to_end(self):
        c = self.window(); ns = c.ns; g = c.lua.globals()
        nav = ns.navigation
        g.combat = True
        c.lua.execute('local ns = ...; ns.navigation.normalHeight = 220', ns)   # e.g. a suggestion strip appearing
        ns.LayoutNavigation()
        self.assertEqual(self.count(c, 'heights'), 0)
        self.assertTrue(nav.heightPending)
        g.combat = False
        ns.frame.OnEvent(ns.frame, "PLAYER_REGEN_ENABLED")
        self.assertEqual(list(g.heights.values())[-1], 220)
        self.assertIsNone(nav.heightPending)

    def test_a_window_the_game_cannot_place_is_put_back_after_combat_and_the_report_says_so(self):
        c = self.window(); ns = c.ns; g = c.lua.globals()
        c.lua.execute('local ns = ...; lost = true; ns.navigation.GetLeft = function() if lost then return nil end return 100 end', ns)
        self.assertFalse(ns.NavigationPlaced())
        g.combat = True
        self.assertFalse(ns.ReanchorNavigation('test'))              # Not during a fight.
        g.combat = False
        ns.frame.OnEvent(ns.frame, "PLAYER_REGEN_ENABLED")
        self.assertGreaterEqual(self.count(c, 'anchors'), 1)         # Fastened to the screen again.
        ns.HudDiagnostics()
        text = ' '.join(g.printed.values())
        self.assertIn('Guide window placement:', text)
        self.assertIn('Game can place it: false', text)
        self.assertIn('no position after combat; put back', text)
        self.assertIn('Guide window repairs (', text)
        self.assertIn('Control frame with the same anchor and size:', text)

    def test_a_shown_window_keeps_repairing_and_retries_immediately_when_reopened(self):
        c = self.window(); ns = c.ns; g = c.lua.globals()
        c.lua.execute('''
            local ns = ...
            clock = 100; function GetTime() return clock end
            lost = true
            ns.navigation.GetLeft = function() if lost then return nil end return 100 end
            local setPoint = ns.navigation.SetPoint
            ns.navigation.SetPoint = function(self, ...) anchors[#anchors + 1] = (...); if cure then lost = false end; return setPoint(self, ...) end
            cure = false
        ''', ns)
        if not ns.navigation.IsShown(ns.navigation):
            ns.navigation.Show(ns.navigation)
        ns.HealNavigation()
        first = self.count(c, 'anchors')
        self.assertGreaterEqual(first, 1)                            # Fastened again at once.
        ns.HealNavigation()
        self.assertEqual(self.count(c, 'anchors'), first)            # Not again within two seconds.
        for _ in range(30):
            c.lua.execute('clock = clock + 3')
            ns.HealNavigation()
        self.assertGreater(ns.hudRepairs, 10)
        self.assertIn('still no position', list(ns.hudNotes.values())[-1])
        repairs = ns.hudRepairs
        ns.navigation.OnShow(ns.navigation)
        self.assertEqual(ns.hudRepairs, repairs + 1)

    def test_a_height_change_that_loses_the_window_is_repaired_on_the_spot(self):
        c = self.window(); ns = c.ns; g = c.lua.globals()
        c.lua.execute('''
            local ns = ...
            local nav = ns.navigation
            local lost = false
            local setHeight = nav.SetHeight
            nav.SetHeight = function(self, value) lost = true; return setHeight(self, value) end      -- as seen in play
            local setPoint = nav.SetPoint
            nav.SetPoint = function(self, ...) anchors[#anchors + 1] = (...); lost = false; return setPoint(self, ...) end
            nav.GetLeft = function() if lost then return nil end return 100 end
            nav.normalHeight = 230
        ''', ns)
        ns.LayoutNavigation()
        self.assertGreaterEqual(self.count(c, 'anchors'), 1)
        self.assertTrue(ns.NavigationPlaced())
        self.assertIn('no position after a height change; put back (worked)', list(ns.hudNotes.values())[-1])
