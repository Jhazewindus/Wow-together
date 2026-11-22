"""Guide resizing preserves guidance; Exit now stops it at the user's request."""
import unittest

from test_navigation import navigator
from test_074 import scanning_client


class GuideWindowTests(unittest.TestCase):
    def test_resize_reflows_attached_panels_and_controls_without_replanning(self):
        c = navigator(); frame = c.ns.navigation
        stop = frame.state.stop.id
        c.lua.globals().resizeNS = c.ns
        c.lua.execute('resizeNS.GenerateFixedGuide=function() error("resize replanned guide") end')
        frame.SetSize(frame, 540, 260); frame.OnSizeChanged(frame)
        self.assertEqual(frame.title.width, 432)  # Reserve the pause, hub and hide icons.
        self.assertEqual(frame.status.width, 444)
        self.assertEqual(frame.status.height, 18)  # The structured instruction stays a single line at every saved frame size.
        self.assertEqual(frame.context.height, 14)
        self.assertIsNone(frame.tip.width)  # Tips are rendered by the separate shared chip strip.
        self.assertEqual(frame.questItem.width, 540)
        self.assertEqual(frame.work.width, 540)
        self.assertEqual(frame.work.scroll.width, 524)
        self.assertEqual(frame.skipStep.point[2], 132)
        self.assertEqual(frame.next.point[2], 406)
        self.assertEqual(frame.state.stop.id, stop)

    def test_resize_handle_saves_size_and_position_and_restores_them(self):
        c = navigator(); frame = c.ns.navigation
        c.lua.execute('function navPoint() return "CENTER",UIParent,"CENTER",31,-42 end')
        frame.GetPoint = c.lua.globals().navPoint
        frame.SetSize(frame, 520, 230)
        frame.grip.OnMouseUp(frame.grip, 'LeftButton')
        self.assertEqual(c.ns.db.arrowSize.width, 520)
        self.assertEqual(c.ns.db.arrowSize.height, 230)
        self.assertEqual(c.ns.db.arrowPosition.x, 31)
        c.ns.CreateNavigation()
        self.assertEqual(c.ns.navigation.width, 520)
        self.assertGreaterEqual(c.ns.navigation.height, 230)
        self.assertEqual(c.ns.db.arrowSize.height, 230)  # Text growth does not overwrite the chosen size.
        self.assertEqual(c.ns.navigation.point[4], 31)

    def test_hide_keeps_guide_running_and_new_start_reopens_window(self):
        c, _ = scanning_client(); frame = c.ns.navigation
        guide, route = c.ns.routeSelection, c.ns.selectedRoute
        frame.close.OnClick(frame.close)
        self.assertFalse(frame.IsShown(frame))
        self.assertTrue(c.ns.Option('routeArrow'))
        c.ns.Refresh(True); c.ns.UpdateNavigation()
        self.assertFalse(frame.IsShown(frame))
        self.assertEqual(c.ns.routeSelection.key, guide.key)
        self.assertIsNotNone(c.ns.selectedRoute)
        c.ns.OpenGuideWindow(); c.ns.UpdateNavigation()
        self.assertTrue(frame.IsShown(frame))
        self.assertEqual(c.ns.routeSelection.key, guide.key)

    def test_step_icon_stays_on_card_when_standalone_arrow_is_enabled(self):
        c = navigator(); frame = c.ns.navigation
        c.ns.SetOption('standaloneArrow', True)
        frame.SetSize(frame, 500, 200); frame.OnSizeChanged(frame)
        self.assertTrue(frame.icon.IsShown(frame.icon))  # Step icon stays on the card; direction is a separate frame.
        self.assertEqual(frame.status.width, 404)
        self.assertEqual(frame.distance.width, 404)
        self.assertEqual(frame.status.point[2], 82)
        c.ns.SetOption('standaloneArrow', False)
        self.assertEqual(frame.status.width, 404)

    def test_small_large_and_private_saved_sizes_are_handled(self):
        c = navigator()
        c.ns.db.arrowSize = c.lua.table_from({'width': 50, 'height': 9999})
        c.ns.CreateNavigation()
        self.assertEqual((c.ns.navigation.width, c.ns.navigation.height), (360, 480))
        c.ns.db.arrowSize.width = c.lua.globals().secret
        c.ns.CreateNavigation()
        self.assertEqual(c.ns.navigation.width, 360)
        self.assertGreaterEqual(c.ns.navigation.height, 168)  # Invalid saved size falls back, then fits text.
        c.ns.navigation.SetSize(c.ns.navigation, 100, 40)
        c.ns.navigation.OnSizeChanged(c.ns.navigation)
        self.assertEqual((c.ns.navigation.width, c.ns.navigation.height), (360, 168))

    def test_resize_and_close_owned_window_work_in_combat(self):
        c = navigator(); frame = c.ns.navigation
        c.lua.execute('function InCombatLockdown() return true end')
        frame.SetSize(frame, 450, 190); frame.OnSizeChanged(frame)
        frame.close.OnClick(frame.close)
        self.assertEqual(frame.width, 450)
        self.assertFalse(frame.IsShown(frame))
        self.assertIsNotNone(c.ns.routeSelection)


if __name__ == '__main__':
    unittest.main()
