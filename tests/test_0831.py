"""Guide cancellation and route-stop regression checks in Lua 5.1."""
import unittest

from test_navigation import navigator
from test_074 import scanning_client


class StopGuideTests(unittest.TestCase):
    def test_stop_keeps_empty_window_and_preserves_skip_preferences(self):
        c, _ = scanning_client(); frame = c.ns.navigation
        c.ns.char.guideSkips = c.lua.table_from({'quests': {900: True}, 'steps': {}}, recursive=True)
        c.ns.SaveSelectedGuide()
        frame.stop.OnClick()
        self.assertTrue(frame.IsShown(frame))
        self.assertEqual(frame.title.text, 'No guide selected')
        self.assertIsNone(c.ns.routeSelection); self.assertIsNone(c.ns.selectedRoute)
        self.assertIsNone(c.ns.char.guideState)
        self.assertTrue(c.ns.char.guideSkips.quests[900])
        self.assertFalse(frame.scan.enabled); self.assertFalse(frame.back.enabled)
        c.drain(); c.ns.Refresh(True)
        self.assertIsNone(c.ns.routeSelection)

    def test_stopping_a_pending_scan_prevents_timer_resurrection(self):
        c, _ = scanning_client()
        c.ns.ScanGuideProgress(); self.assertTrue(c.ns.guideScanning)
        c.ns.StopGuide(True); c.drain()
        self.assertIsNone(c.ns.guideScanning); self.assertIsNone(c.ns.routeSelection)
        self.assertFalse(c.ns.navigation.IsShown(c.ns.navigation))

    def test_stopping_route_planning_cancels_the_job_and_saved_restore(self):
        c, _ = scanning_client(); guide = c.ns.routeSelection
        c.ns.PlanLevelingGuide(guide, False); self.assertTrue(c.ns.routePlanning)
        c.ns.pendingSavedGuide = c.lua.table()
        c.ns.StopGuide(False); c.drain(); c.ns.RestoreSavedGuide()
        self.assertIsNone(c.ns.routePlanning); self.assertIsNone(c.ns.pendingSavedGuide)
        self.assertIsNone(c.ns.routeSelection)
        self.assertTrue(c.ns.navigation.IsShown(c.ns.navigation))

    def test_combat_stop_clears_pending_start_and_regen_does_not_revive_it(self):
        c = navigator(); guide = c.ns.routeSelection
        c.lua.execute('function InCombatLockdown() return true end')
        c.ns.pendingGuideMap, c.ns.pendingPartyRouteStart = guide, guide
        invite = c.lua.table_from({'sender': 'Tester'})
        c.ns.pendingPartyRouteFollow, c.ns.pendingPartyRouteInvite, c.ns.waitingPartyRoute = invite, invite, invite
        c.lua.execute('stoppedFollowCalls=0')
        c.lua.globals().stoppedNS = c.ns
        c.lua.execute('stoppedNS.FollowPartyRoute=function() stoppedFollowCalls=stoppedFollowCalls+1 end')
        c.ns.StopGuide(False)
        self.assertIsNone(c.ns.routeSelection); self.assertIsNone(c.ns.selectedRoute)
        self.assertIsNone(c.ns.pendingPartyRouteFollow); self.assertIsNone(c.ns.pendingPartyRouteInvite)
        self.assertIsNone(c.ns.waitingPartyRoute)
        c.lua.execute('function InCombatLockdown() return false end')
        c.ns.handlers.PLAYER_REGEN_ENABLED(); c.drain()
        self.assertEqual(c.lua.globals().stoppedFollowCalls, 0)
        self.assertIsNone(c.ns.routeSelection); self.assertIsNone(c.ns.pendingPartyRouteStart)
        self.assertTrue(c.ns.navigation.IsShown(c.ns.navigation))

    def test_background_toggle_and_hide_keep_the_guide_and_separate_arrow(self):
        c = navigator(); frame = c.ns.navigation
        before = c.ns.routeSelection.key
        opaque = c.ns.Option('guideOpaque')
        frame.titleToggle.OnMouseUp(frame.titleToggle, 'RightButton')
        self.assertNotEqual(c.ns.Option('guideOpaque'), opaque)
        self.assertEqual(c.ns.routeSelection.key, before)
        c.ns.SetOption('standaloneArrow', True)
        frame.close.OnClick()
        self.assertEqual(c.ns.routeSelection.key, before)
        self.assertFalse(frame.IsShown(frame))
        self.assertTrue(c.ns.standaloneNavigation.IsShown(c.ns.standaloneNavigation))


if __name__ == '__main__':
    unittest.main()
