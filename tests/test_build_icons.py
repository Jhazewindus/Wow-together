"""Contracts for the authored, reproducible HUD icon assets."""
from pathlib import Path
import importlib.util
import struct
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_icons", ROOT / "tools" / "build_icons.py")
build_icons = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_icons)


class GeneratedIconTests(unittest.TestCase):
    def test_svg_set_and_style_match_the_brief(self):
        paths = sorted(build_icons.SOURCE.glob("*.svg"))
        self.assertEqual({path.stem for path in paths}, set(build_icons.NAMES))
        for path in paths:
            source = path.read_text(encoding="utf-8")
            self.assertIn('viewBox="0 0 24 24"', source)
            self.assertIn('stroke="#e8e2d3"', source)
            self.assertIn('stroke-width="1.8"', source)
            self.assertIn('stroke-linecap="round"', source)
            self.assertIn('stroke-linejoin="round"', source)
            self.assertNotIn("fill=\"#", source)

    def test_tga_is_64px_rgba_uncompressed_and_straight_alpha(self):
        body = build_icons.render_tga(build_icons.SOURCE / "kill.svg")
        self.assertEqual(len(body), 18 + 64 * 64 * 4)
        self.assertEqual(body[2], 2)
        self.assertEqual(struct.unpack("<HH", body[12:16]), (64, 64))
        self.assertEqual(body[16], 32)
        self.assertEqual(body[17], 0x28)
        image = Image.open(__import__("io").BytesIO(body)).convert("RGBA")
        self.assertEqual(image.size, (64, 64))
        rgba = image.tobytes("raw", "RGBA")
        pixels = [rgba[offset:offset + 4] for offset in range(0, len(rgba), 4)]
        partially_covered = [pixel for pixel in pixels if 0 < pixel[3] < 255]
        self.assertTrue(partially_covered, "icons need anti-aliased edges")
        self.assertTrue(all(pixel[:3] == bytes((232, 226, 211)) for pixel in partially_covered),
                        "edge RGB stays unpremultiplied under straight alpha")

    def test_outputs_are_byte_stable_and_check_passes(self):
        first = build_icons.expected_files()
        second = build_icons.expected_files()
        self.assertEqual(first, second)
        self.assertTrue(build_icons.build(check=True))

    def test_owned_lua_files_use_only_supported_latin_glyphs(self):
        allowed = set("·•–—…’")
        owned = (
            "AuctionGuide.lua", "ProfessionShopping.lua", "DungeonMapQuests.lua",
            "DungeonViewer.lua", "GroupFinderRoles.lua", "Progress.lua",
            "ProfessionPlanner.lua", "GuideXP.lua", "Routes.lua",
            "GuideQuestList.lua", "GuideText.lua", "ModuleAPI.lua",
        )
        for name in owned:
            with self.subTest(name=name):
                source = (ROOT / "WowTogether" / name).read_text(encoding="utf-8")
                invalid = sorted({char for char in source if ord(char) > 0xFF and char not in allowed})
                self.assertEqual(invalid, [])


if __name__ == "__main__":
    unittest.main()
