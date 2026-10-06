"""Guide artwork must ship completely, stay behind controls and survive pooled cards."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import zipfile

from test_addon import Client, ROOT
from test_0811 import browser
from test_063 import order, zone
from test_061 import run_plan

MEDIA = ROOT / 'WowTogether' / 'Media' / 'GuideThemes'


class GuideArtworkTests(unittest.TestCase):
    def test_assets_are_power_of_two_rgba_with_a_quiet_text_area(self):
        manifest = json.loads((MEDIA / 'manifest.json').read_text())
        self.assertEqual(len(manifest['textures']), 16)
        self.assertEqual(hashlib.sha256((MEDIA / manifest['source']).read_bytes()).hexdigest(), manifest['source_sha256'])
        for item in manifest['textures']:
            data = (MEDIA / item['file']).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), item['sha256'])
            self.assertEqual(data[2], 2)  # Uncompressed true-color TGA.
            self.assertEqual(struct.unpack_from('<HH', data, 12), (512, 128))
            self.assertEqual(data[16], 32)
            self.assertEqual(data[17] & 15, 8)
            pixels = data[18 + data[0]:18 + data[0] + 512 * 128 * 4]
            for row in (0, 64, 127):
                alpha = pixels[(row * 512) * 4 + 3:(row * 512 + 512) * 4:4]
                self.assertTrue(all(a == 0 for a in alpha[:150]))
                self.assertGreater(alpha[-1], 0)
                self.assertLessEqual(max(alpha), 87)

    def test_zone_matching_does_not_depend_on_current_location_or_localized_names(self):
        c = Client(); c.ns.profile = c.lua.table_from({'mapID': 1411})
        c.lua.execute("C_Map={GetMapInfo=function() error('Themes must not query native maps') end}")
        for map_id, expected in ((1440, 'woodland'), (1412, 'prairie'), (1411, 'canyon'),
                                 (1413, 'savanna'), (1446, 'desert'), (1452, 'snow')):
            guide = c.lua.table_from({'homeMapID': map_id, 'zone': 'localized name'})
            self.assertEqual(c.ns.GuideCardTheme(guide), expected)
        guide = c.lua.table_from({'key': 'level-zone:kalimdor/zephras-isle', 'zone': 'localized name'})
        self.assertEqual(c.ns.GuideCardTheme(guide), 'coast')
        guide = c.lua.table_from({'key': 'level-zone:new/unmapped-zone'})
        self.assertEqual(c.ns.GuideCardTheme(guide), 'ruins')
        secret = c.lua.globals().secret
        self.assertIsNone(c.ns.GuideCardTheme(secret))
        self.assertEqual(c.ns.GuideCardTheme(c.lua.table_from({'homeMapID': secret, 'key': secret, 'zone': secret})), 'ruins')

    def test_reused_guide_card_clears_art_for_plain_quest_views(self):
        c = browser(); card = c.ns.ui.cards[1]
        self.assertTrue(card.zoneArt.IsShown(card.zoneArt))
        self.assertEqual(card.zoneArt.drawLayer, 'ARTWORK')
        self.assertEqual(card.zoneArt.drawSublevel, -7)
        c.ns.SetFilter('library')
        self.assertGreater(c.ns.ui.visibleCards, 0)
        self.assertFalse(c.ns.ui.cards[1].zoneArt.IsShown(c.ns.ui.cards[1].zoneArt))
        c.ns.SetFilter('guides')
        self.assertTrue(c.ns.ui.cards[1].zoneArt.IsShown(c.ns.ui.cards[1].zoneArt))

    def test_resize_reuses_texture_and_leaves_fixed_route_and_credit_unchanged(self):
        c = browser(); g = zone(c); c.ns.ShowGuideOnMap(g); run_plan(c)
        before = order(c.ns.routeSelection)
        card = c.ns.ui.cards[1]; art = card.zoneArt
        before_crop = tuple(art.texCoord.values())
        c.ns.window.SetWidth(c.ns.window, 1120); c.ns.Layout()
        after_crop = tuple(art.texCoord.values())
        self.assertEqual(art.texture, c.ns.ui.cards[1].zoneArt.texture)
        self.assertNotEqual(before_crop, after_crop)
        self.assertTrue(all(0 <= value <= 1 for value in after_crop))
        self.assertEqual(order(c.ns.routeSelection), before)
        self.assertFalse(c.ns.Completed(900))
        c.ns.Refresh()
        self.assertEqual(order(c.ns.routeSelection), before)

    def test_every_shipped_guide_and_dungeon_resolves_to_a_packaged_texture(self):
        c = Client(quests=(), use_catalogue=True); c.guide_environment(level=25)
        c.ns.guideLevel = 'all'
        for faction in ('Horde', 'Alliance'):
            c.ns.profile.faction = faction
            for g in c.ns.GuideBrowserChoices().values():
                theme = c.ns.GuideCardTheme(g)
                self.assertTrue((MEDIA / (theme + '.tga')).exists(), g.key)
        for dungeon in c.ns.DungeonGroups().values():
            self.assertTrue((MEDIA / (c.ns.GuideCardTheme(None, dungeon) + '.tga')).exists())

    def test_release_contains_all_texture_files_and_editable_source(self):
        with tempfile.TemporaryDirectory() as destination:
            subprocess.run(['python3', str(ROOT / 'tools' / 'build_release.py'), '--output', destination],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            path = next(Path(destination).glob('WowTogether-*.zip'))
            with zipfile.ZipFile(path) as archive:
                for asset in MEDIA.iterdir():
                    self.assertEqual(archive.read('WowTogether/Media/GuideThemes/' + asset.name), asset.read_bytes())
                self.assertIsNone(archive.testzip())


if __name__ == '__main__':
    unittest.main()
