"""Every distinct presentation kind resolves to its authored texture."""
import unittest

from test_navigation import navigator


class StepIconMappingTests(unittest.TestCase):
    def test_action_and_travel_kinds_map_to_their_own_generated_icons(self):
        client = navigator()
        expected = {
            "accept": "accept", "turnin": "turnin", "turninIncomplete": "turnin-pending",
            "kill": "kill", "collect": "collect", "use": "use", "talk": "talk",
            "travel": "travel", "fly": "fly", "hearth": "hearth", "teleport": "teleport",
            "ship": "ship", "party": "party", "wait": "wait", "farm": "farm", "dungeon": "dungeon",
        }
        for kind, name in expected.items():
            with self.subTest(kind=kind):
                symbol = client.ns.STEP_SYMBOLS[kind]
                self.assertEqual(symbol.icon, name)
                self.assertEqual(client.ns.STEP_ICON_TEXTURES[name],
                                 f"Interface\\AddOns\\WowTogether\\Media\\Icons\\{name}")
                self.assertIsNotNone(symbol.available)
                self.assertTrue(symbol.glyph.isascii())
                glyph, texture = client.ns.StepSymbolFor(kind)
                self.assertEqual(glyph, symbol.glyph)
                self.assertEqual(texture, symbol.texture if symbol.available else None)

    def test_travel_presentation_kinds_select_the_specific_transport_icon(self):
        client = navigator()
        aliases = {
            "travel-walk": "travel", "travel-fly": "fly", "travel-hearth": "hearth",
            "travel-teleport": "teleport", "travel-ship": "ship", "trainer": "talk",
            "corpse": "travel",
        }
        for presentation_kind, symbol_kind in aliases.items():
            with self.subTest(presentation_kind=presentation_kind):
                self.assertEqual(client.ns.StepSymbolFor(presentation_kind)[0],
                                 client.ns.STEP_SYMBOLS[symbol_kind].glyph)

    def test_generic_hud_icons_are_available_through_the_same_checked_table(self):
        client = navigator()
        for name in ("pause", "menu", "close", "scan"):
            with self.subTest(name=name):
                self.assertEqual(client.ns.STEP_ICON_TEXTURES[name],
                                 f"Interface\\AddOns\\WowTogether\\Media\\Icons\\{name}")
                if client.ns.StepIconTexture(name):
                    self.assertEqual(client.ns.StepIconTexture(name), client.ns.STEP_ICON_TEXTURES[name])


if __name__ == "__main__":
    unittest.main()
