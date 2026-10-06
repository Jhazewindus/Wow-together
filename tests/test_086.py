"""Beta-reported font signature and startup cascade regression checks."""
import unittest

from lupa.lua51 import LuaError
from test_addon import Client


class StartupFontTests(unittest.TestCase):
    def test_search_boxes_and_shared_labels_use_explicit_font_flags(self):
        c = Client()
        for box in (c.ns.ui.librarySearch, c.ns.ui.guideSearch):
            self.assertEqual(box.fontFile, 'Fonts\\ARIALN.TTF')
            self.assertEqual(box.fontHeight, 12)
            self.assertEqual(box.fontFlags, '')
            self.assertEqual(box.placeholder.fontFlags, '')
        self.assertEqual(c.ns.ui.zone.fontFlags, '')
        self.assertEqual(c.ns.ui.trackerButton.caption.fontFlags, '')
        self.assertIsNotNone(c.ns.active)
        self.assertEqual(c.ns.self, 'Alice-TestRealm')
        self.assertTrue(c.ns.minimapButton.IsShown(c.ns.minimapButton))
        c.ns.minimapButton.OnClick(c.ns.minimapButton, 'LeftButton')
        self.assertTrue(c.ns.window.IsShown(c.ns.window))
        hidden = Client(saved_variables={'minimapHidden': True})
        self.assertIsNotNone(hidden.ns.minimapButton)
        self.assertFalse(hidden.ns.minimapButton.IsShown(hidden.ns.minimapButton))
        hidden.ns.ToggleMinimap()
        self.assertTrue(hidden.ns.minimapButton.IsShown(hidden.ns.minimapButton))

    def test_mock_rejects_the_reported_missing_third_argument(self):
        c = Client()
        with self.assertRaisesRegex(LuaError, "bad argument #3 to 'SetFont'"):
            c.ns.ui.librarySearch.SetFont(c.ns.ui.librarySearch, 'Fonts\\ARIALN.TTF', 12)

    def test_post_load_events_have_quest_state_controls_and_character_identity(self):
        c = Client(saved_variables={'offerKnowledge': {
            'Poging-Twee': {3143: {'complete': True, 'context': 'old', 'offered': {1: True}}}}})
        c.guide_environment(level=12)
        for event in ('PLAYER_LOGIN', 'UPDATE_FACTION', 'QUEST_LOG_UPDATE', 'ZONE_CHANGED_NEW_AREA'):
            c.ns.handlers[event]()
        c.drain()
        self.assertEqual({id for id in c.ns.active}, {1, 2})
        self.assertIsNotNone(c.ns.ui.trackerButton)
        self.assertIsNotNone(c.ns.ui.syncButton)
        self.assertIsNotNone(c.ns.tracker)
        self.assertIsNotNone(c.ns.navigation)
        self.assertTrue(c.ns.minimapButton.IsShown(c.ns.minimapButton))
        self.assertIsNotNone(c.ns.db.offerKnowledge['Poging-Twee'][3143])
        self.assertEqual(len(c.ns.db.offerKnowledge['Alice-TestRealm']), 0)
