"""Verified native floor/player tracking; not an actual Forever client test."""
import unittest

from test_addon import Client
from test_0824 import NATIVE
from test_063 import primitive


TRACK = '''
trackedMap=400; px=.25; py=.75; facing=1.2; positionReads=0
C_Map.GetBestMapForUnit=function(unit) assert(unit=='player'); return trackedMap end
C_Map.GetPlayerMapPosition=function(map,unit)
    assert(map==trackedMap and unit=='player'); positionReads=positionReads+1
    return {GetXY=function()return px,py end}
end
function GetPlayerFacing()return facing end
'''


def player_map():
    c = Client(use_catalogue=True, before_load=NATIVE)
    c.lua.execute(TRACK)
    c.ns.ShowDungeonViewer('ragefire-chasm', True)
    return c, c.ns.dungeonViewer


def tick(frame, elapsed=.1):
    frame.map.OnUpdate(frame.map, elapsed)


class DungeonPlayerTests(unittest.TestCase):
    def test_native_position_uses_letterboxed_art_and_resize_geometry(self):
        c, f = player_map()
        self.assertTrue(f.playerMarker.IsShown(f.playerMarker))
        for width, height in ((500, 420), (620, 400)):
            f.SetSize(f, width, height); f.OnSizeChanged(); tick(f)
            g, p = f.playerGeometry, f.playerMarker.point
            self.assertEqual(p[1], 'CENTER')
            self.assertAlmostEqual((p[4] - g.x) / g.width, .25)
            self.assertAlmostEqual((-p[5] - g.y) / g.height, .75)
        self.assertTrue(f.playerMarker.arrow.IsShown(f.playerMarker.arrow))

    def test_movement_repaints_only_the_marker_and_throttles_reads(self):
        c, f = player_map()
        c.lua.execute('local ns=...; ns.RenderDungeonViewer=function()error("movement redrew journal")end; '
                      'ns.DungeonViewerData=function()error("movement reloaded data")end', c.ns)
        before = c.lua.globals().positionReads
        tick(f, .03); tick(f, .03)
        self.assertEqual(c.lua.globals().positionReads, before)
        c.lua.globals().px = .6
        tick(f, .04)
        self.assertEqual(c.lua.globals().positionReads, before + 1)
        self.assertAlmostEqual((f.playerMarker.point[4]-f.playerGeometry.x)/f.playerGeometry.width, .6)

    def test_follow_floor_advances_once_without_changing_selected_loot(self):
        c, f = player_map(); boss = f.bossID
        c.lua.globals().trackedMap = 401
        tick(f)
        self.assertEqual(f.floor, 2)
        self.assertEqual(f.playerGeometry.mapID, 401)
        self.assertEqual(f.bossID, boss)
        self.assertTrue(f.playerMarker.IsShown(f.playerMarker))

    def test_browsing_other_floor_stays_selected_until_locate_clicked(self):
        c, f = player_map()
        f.floorMenu.options[2].OnClick()
        self.assertEqual(f.floor, 2)
        self.assertFalse(f.followPlayer)
        tick(f)
        self.assertEqual(f.floor, 2)
        self.assertFalse(f.playerMarker.IsShown(f.playerMarker))
        self.assertIn('another floor', c.ns.dungeonPlayerStatus)
        f.refresh.OnClick()
        self.assertEqual(f.floor, 1)
        self.assertTrue(f.followPlayer)
        self.assertTrue(f.playerMarker.IsShown(f.playerMarker))

    def test_boss_click_disables_follow_to_preserve_browsing(self):
        c, f = player_map()
        f.bossRows[1].OnClick()
        self.assertFalse(f.followPlayer)
        c.lua.globals().trackedMap = 401
        tick(f)
        self.assertEqual(f.floor, 1)
        self.assertFalse(f.playerMarker.IsShown(f.playerMarker))

    def test_reference_image_never_borrows_native_coordinates(self):
        c = Client(use_catalogue=True)
        c.lua.execute('C_Map={};' + TRACK)
        c.ns.ShowDungeonViewer('ragefire-chasm', True); f = c.ns.dungeonViewer
        self.assertTrue(f.data.maps[1].reference)
        f.data.maps[1].mapID = 400
        c.ns.RenderDungeonViewer(); tick(f)
        self.assertFalse(f.playerMarker.IsShown(f.playerMarker))
        self.assertEqual(c.lua.globals().positionReads, 0)

    def test_wrong_native_map_never_queries_or_keeps_old_position(self):
        c, f = player_map()
        before = c.lua.globals().positionReads
        c.lua.globals().trackedMap = 1411
        tick(f)
        self.assertFalse(f.playerMarker.IsShown(f.playerMarker))
        self.assertEqual(c.lua.globals().positionReads, before)

    def test_private_nil_bad_and_out_of_bounds_values_hide_marker(self):
        c, f = player_map()
        for value in (None, c.lua.globals().secret, -1, 2, float('inf'), float('nan')):
            with self.subTest(value=str(value)):
                c.lua.globals().px = value
                tick(f)
                self.assertFalse(f.playerMarker.IsShown(f.playerMarker))
        c.lua.execute('px=0;py=0'); tick(f)
        self.assertFalse(f.playerMarker.IsShown(f.playerMarker))

    def test_failed_or_missing_native_api_is_a_static_map(self):
        c, f = player_map()
        for source in ('C_Map.GetPlayerMapPosition=nil',
                       'C_Map.GetPlayerMapPosition=function()error("restricted position")end',
                       'C_Map.GetPlayerMapPosition=function()return secret end'):
            c.lua.execute(source); tick(f)
            self.assertFalse(f.playerMarker.IsShown(f.playerMarker))
            self.assertTrue(f.tiles[1].IsShown(f.tiles[1]))

    def test_facing_is_live_and_private_facing_becomes_a_position_dot(self):
        c, f = player_map()
        c.lua.execute('marker=...; function marker.arrow:SetRotation(v)self.angle=v end', f.playerMarker)
        c.lua.globals().facing = 2.1; tick(f)
        self.assertEqual(f.playerMarker.arrow.angle, 2.1)
        c.lua.globals().facing = c.lua.globals().secret; tick(f)
        self.assertTrue(f.playerMarker.IsShown(f.playerMarker))
        self.assertFalse(f.playerMarker.arrow.IsShown(f.playerMarker.arrow))
        self.assertTrue(f.playerMarker.dot.IsShown(f.playerMarker.dot))

    def test_missing_map_tile_hides_marker_and_keeps_loot(self):
        c, f = player_map()
        c.lua.execute('getmetatable(CreateFrame("Frame")).__index.SetTexture=function()return false end')
        c.ns.RenderDungeonViewer(); tick(f)
        self.assertTrue(f.empty.IsShown(f.empty))
        self.assertFalse(f.playerMarker.IsShown(f.playerMarker))
        self.assertIsNone(f.playerGeometry)
        self.assertTrue(f.lootRows[1].item)

    def test_quest_marker_toggle_does_not_disable_player_tracking(self):
        c, f = player_map()
        f.questsToggle.OnClick(); tick(f)
        self.assertFalse(f.showQuests)
        self.assertTrue(f.playerMarker.IsShown(f.playerMarker))

    def test_combat_keeps_map_and_public_position_but_rejects_secret_position(self):
        c, f = player_map(); c.lua.globals().combat = True
        tick(f)
        self.assertTrue(f.IsShown(f))
        self.assertTrue(f.playerMarker.IsShown(f.playerMarker))
        c.lua.globals().px = c.lua.globals().secret
        tick(f)
        self.assertTrue(f.IsShown(f))
        self.assertFalse(f.playerMarker.IsShown(f.playerMarker))

    def test_hidden_viewer_does_not_poll_and_guide_progress_is_untouched(self):
        c, f = player_map()
        before = primitive(c.ns.db.guideState), primitive(c.ns.db.guideSkips)
        reads = c.lua.globals().positionReads
        f.Hide(f); f.OnHide(); tick(f)
        self.assertEqual(c.lua.globals().positionReads, reads)
        self.assertFalse(f.playerMarker.IsShown(f.playerMarker))
        self.assertEqual((primitive(c.ns.db.guideState), primitive(c.ns.db.guideSkips)), before)


if __name__ == '__main__':
    unittest.main()
