"""HUD title controls and the secondary Glance renderer."""
import unittest

from test_navigation import navigator


class HudTitleTests(unittest.TestCase):
    def test_title_controls_pause_open_hub_and_hide_without_stopping(self):
        c = navigator(); frame = c.ns.navigation
        guide = c.ns.routeSelection
        frame.close.OnClick()
        self.assertFalse(frame.IsShown(frame))
        self.assertEqual(c.ns.routeSelection.key, guide.key)
        c.ns.OpenGuideWindow()
        self.assertTrue(frame.IsShown(frame))
        frame.menu.OnClick()
        self.assertTrue(c.ns.window.IsShown(c.ns.window))
        self.assertEqual(c.ns.filter, 'recommended')

    def test_step_counter_toggles_one_line_glance_and_back(self):
        c = navigator(); frame = c.ns.navigation
        frame.stepButton.OnClick()
        self.assertTrue(c.ns.Option('guideGlance'))
        self.assertTrue(frame.glance)
        self.assertFalse(frame.context.IsShown(frame.context))
        self.assertFalse(frame.distance.IsShown(frame.distance))
        self.assertTrue(frame.status.text)
        frame.stepButton.OnClick()
        self.assertFalse(c.ns.Option('guideGlance'))
        self.assertFalse(frame.glance)
        self.assertTrue(frame.status.IsShown(frame.status))

    def test_shared_step_icon_table_has_probed_texture_or_glyph_for_every_kind(self):
        c = navigator()
        symbols = c.ns.STEP_SYMBOLS
        coreKinds = {'accept', 'turnin', 'turninIncomplete', 'kill', 'collect', 'use', 'talk', 'travel',
                     'fly', 'hearth', 'teleport', 'ship', 'party', 'wait', 'farm', 'dungeon'}
        self.assertTrue(coreKinds.issubset(set(symbols.keys())))
        self.assertEqual(coreKinds, set(symbols.keys()))
        for key in coreKinds:
            symbol = symbols[key]
            self.assertTrue(symbol.glyph)
            self.assertIsNotNone(symbol.available)
        self.assertTrue(c.ns.stepIconStatus.startswith('Step icons: '))


if __name__ == '__main__':
    unittest.main()
