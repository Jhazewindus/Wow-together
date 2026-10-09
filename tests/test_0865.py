"""Classic reference projection and Forever finder structure adapters.

Host Lua 5.1 checks validate transforms and UI ownership, not beta alignment.
"""
import unittest

from test_addon import Client
from test_dungeon_player import tick
from test_0864 import ENTRY, FINDER


REFERENCE = ENTRY + '''
worldX=-329.80895;worldY=268.155;worldInstance=389;worldReads=0
function UnitPosition()worldReads=worldReads+1;return worldX,worldY,3,worldInstance end
function GetPlayerFacing()return 1.2 end
C_Map={GetBestMapForUnit=function()return 1454 end,
 GetPlayerMapPosition=function()error('reference used native UI coordinates')end,
 GetMapPosFromWorldPos=function()error('reference borrowed native geometry')end}
'''
CLASSIC = FINDER + '''
LFGListFrame=nil
LFGParentFrame=CreateFrame('Frame',nil,UIParent);LFGParentFrame:Show()
LFGBrowseFrame=CreateFrame('Frame',nil,LFGParentFrame);LFGBrowseFrame:Show()
LFGBrowseFrame.ActivityDropdown={selectedValues={}}
finderInfo[1].activityIDs={10};finderInfo[2].activityIDs={20}
finderPlayers[1][1].classFilename='WARRIOR'
finderPlayers[1][2].classFilename='PRIEST'
finderPlayers[1][3].classFilename='MAGE'
finderPlayers[2][1].classFilename='SHAMAN'
finderPlayers[1][1].assignedRole='NONE';finderPlayers[1][1].lfgRoles={tank=true,healer=false,dps=true}
finderPlayers[1][2].assignedRole='NONE';finderPlayers[1][2].lfgRoles={tank=false,healer=true,dps=false}
finderPlayers[2][1].assignedRole='NONE';finderPlayers[2][1].lfgRoles={tank=false,healer=true,dps=true}
'''


def reference_map():
    c = Client(use_catalogue=True, before_load=REFERENCE)
    c.ns.ShowDungeonViewer('ragefire-chasm', True)
    return c, c.ns.dungeonViewer


class ReferencePlayerTests(unittest.TestCase):
    def test_ragefire_reference_uses_published_world_bounds_without_native_map(self):
        c, f = reference_map()
        b = f.data.maps[1].worldBounds
        self.assertEqual(b.instanceMapID, 389)
        self.assertEqual(b.sourceID, 136)
        self.assertTrue(f.playerMarker.IsShown(f.playerMarker))
        self.assertIsNone(f.nativePlayer)
        self.assertIn('reference-world', c.ns.dungeonPlayerStatus)
        self.assertAlmostEqual((f.playerMarker.point[4] - f.playerGeometry.x) / f.playerGeometry.width, .25)
        self.assertAlmostEqual((-f.playerMarker.point[5] - f.playerGeometry.y) / f.playerGeometry.height, .75)

    def test_reference_movement_and_resize_preserve_image_alignment(self):
        c, f = reference_map()
        for width, height in ((500, 420), (980, 600)):
            f.SetSize(f, width, height); f.OnSizeChanged(); tick(f)
            self.assertAlmostEqual((f.playerMarker.point[4] - f.playerGeometry.x) / f.playerGeometry.width, .25)
        c.lua.globals().worldY = -138.2202
        tick(f)
        self.assertAlmostEqual((f.playerMarker.point[4] - f.playerGeometry.x) / f.playerGeometry.width, .8)

    def test_wrong_instance_outdoor_and_private_world_values_never_keep_marker(self):
        c, f = reference_map()
        for change in ('worldInstance=0', 'worldInstance=389;worldX=secret',
                       'worldX=1000001', 'worldX=100', 'worldX=-329.80895;worldY=secret',
                       'worldY=268.155;function IsInInstance()return false end'):
            with self.subTest(change=change):
                c.lua.execute(change); tick(f)
                self.assertFalse(f.playerMarker.IsShown(f.playerMarker))

    def test_unsupported_world_api_leaves_reference_image_and_loot_available(self):
        c, f = reference_map()
        for change in ('UnitPosition=nil', 'UnitPosition=function()error("private")end',
                       'UnitPosition=function()return nil end'):
            c.lua.execute(change); tick(f)
            self.assertFalse(f.playerMarker.IsShown(f.playerMarker))
            self.assertTrue(f.tiles[1].IsShown(f.tiles[1]))
        self.assertTrue(len(f.data.bosses))

    def test_probe_reports_public_instance_coordinates_and_hides_secret_values(self):
        c, f = reference_map()
        lines = []
        c.ns.DungeonPlayerDiagnostics(lines.append, f)
        self.assertIn('instance 389', lines[0])
        self.assertIn('DungeonMap 136', lines[0])
        c.lua.globals().worldX = c.lua.globals().secret
        lines = []
        c.ns.DungeonPlayerDiagnostics(lines.append, f)
        self.assertIn('unavailable/restricted', lines[0])

    def test_hidden_reference_map_does_not_poll_and_combat_keeps_public_marker(self):
        c, f = reference_map()
        c.lua.globals().combat = True; tick(f)
        self.assertTrue(f.playerMarker.IsShown(f.playerMarker))
        f.Hide(f); f.OnHide(); reads = c.lua.globals().worldReads
        tick(f)
        self.assertEqual(c.lua.globals().worldReads, reads)

    def test_ambiguous_floors_hide_marker_even_when_manually_browsing_one(self):
        c, f = reference_map()
        c.lua.execute('local f=...;f.data.maps[2]=f.data.maps[1]', f)
        tick(f)
        self.assertFalse(f.playerMarker.IsShown(f.playerMarker))
        self.assertIn('Overlapping', c.ns.dungeonPlayerStatus)
        self.assertFalse(c.ns.LocateDungeonPlayer(f))

    def test_missing_rectangle_is_not_inferred_from_reference_map_or_bosses(self):
        c, f = reference_map()
        f.data.maps[1].worldBounds = None
        c.ns.RenderDungeonViewer(); tick(f)
        self.assertFalse(f.playerMarker.IsShown(f.playerMarker))
        self.assertIsNone(f.playerGeometry)

    def test_locate_switches_only_to_unique_reference_floor(self):
        c, f = reference_map()
        c.lua.execute('''local f=...;local m=f.data.maps[1];local b=m.worldBounds
          f.data.maps[2]={reference=true,name='Other floor',width=m.width,height=m.height,
            tileWidth=m.tileWidth,tileHeight=m.tileHeight,tiles=m.tiles,bosses={},quests={},
            worldBounds={left=1000,right=2000,bottom=1000,top=2000,instanceMapID=389}}
        ''', f)
        f.floor, f.followPlayer = 2, False
        c.ns.RenderDungeonViewer(); tick(f)
        self.assertFalse(f.playerMarker.IsShown(f.playerMarker))
        self.assertEqual(f.floor, 2)
        self.assertTrue(c.ns.LocateDungeonPlayer(f))
        c.ns.RenderDungeonViewer(); tick(f)
        self.assertEqual(f.floor, 1)
        self.assertTrue(f.playerMarker.IsShown(f.playerMarker))


class ForeverFinderTests(unittest.TestCase):
    def client(self):
        return Client(before_load=CLASSIC)

    def names(self, c, role='all', class_id=0, activities=None, mode='classic'):
        rows, _ = c.ns.ReadGroupFinderPlayers(mode, role, class_id, activities)
        return [row.name for row in rows.values()]

    def test_forever_structure_roles_include_multi_role_solo_listings(self):
        c = self.client()
        self.assertEqual(self.names(c, 'TANK'), ['Tanky'])
        self.assertEqual(self.names(c, 'HEALER'), ['Heals', 'Mystery'])
        self.assertEqual(self.names(c, 'DAMAGER'), ['Tanky', 'Damagey', 'Mystery'])

    def test_class_and_role_intersection_uses_public_class_filename(self):
        c = self.client()
        self.assertEqual(self.names(c, 'HEALER', 7), ['Mystery'])
        self.assertEqual(self.names(c, 'TANK', 7), [])
        self.assertEqual(self.names(c, 'all', 8), ['Damagey'])
        self.assertEqual(self.names(c, 'HEALER', 2, mode='applicants'), ['Flexible'])
        c.lua.execute('finderPlayers[2][1].classFilename=secret')
        self.assertEqual(self.names(c, 'HEALER', 7), [])
        self.assertEqual(self.names(c, 'HEALER'), ['Heals', 'Mystery'])

    def test_classic_activity_selection_and_self_results_are_respected(self):
        c = self.client()
        activities = c.lua.table_from([20])
        self.assertEqual(self.names(c, activities=activities), ['Mystery'])
        c.lua.execute('finderInfo[2].hasSelf=true')
        self.assertEqual(self.names(c, activities=activities), [])

    def test_classic_sidebar_appears_with_both_dropdowns_and_never_changes_native_ui(self):
        c = self.client()
        c.lua.execute('''
          function LFGParentFrame:SetScript()error('native hook')end
          function LFGBrowseFrame:SetScript()error('native hook')end
          function LFGBrowseFrame:SetParent()error('native reparent')end
          function LFGBrowseFrame:Hide()error('native hide')end
        ''')
        c.ns.RefreshGroupFinderRoles(); f = c.ns.groupFinderRoleWindow
        self.assertTrue(f.IsShown(f)); self.assertEqual(f.context, 'classic')
        f.filter.options.HEALER.OnClick(); f.classFilter.options[7].OnClick()
        self.assertEqual(f.rows[1].data.name, 'Mystery')
        self.assertFalse(f.rows[2].IsShown(f.rows[2]))
        self.assertEqual(f.classFilter.width, 130)

    def test_classic_tab_changes_close_reopen_and_native_activity_refresh(self):
        c = self.client(); c.ns.RefreshGroupFinderRoles(); f = c.ns.groupFinderRoleWindow
        c.lua.execute('LFGBrowseFrame.ActivityDropdown.selectedValues={20}')
        c.ns.RefreshGroupFinderRoles(); self.assertEqual(f.rows[1].data.name, 'Mystery')
        c.lua.execute('LFGBrowseFrame:Hide()'); c.ns.RefreshGroupFinderRoles()
        self.assertFalse(f.IsShown(f))
        c.lua.execute('LFGBrowseFrame:Show()'); c.ns.RefreshGroupFinderRoles()
        self.assertTrue(f.IsShown(f))
        f.close.OnClick(); c.ns.RefreshGroupFinderRoles(); self.assertFalse(f.IsShown(f))
        c.lua.execute('LFGParentFrame:Hide()'); c.ns.RefreshGroupFinderRoles()
        c.lua.execute('LFGParentFrame:Show()'); c.ns.RefreshGroupFinderRoles()
        self.assertTrue(f.IsShown(f))

    def test_secret_role_structure_and_private_flags_are_not_interpreted(self):
        c = self.client()
        c.lua.execute('finderPlayers[2][1].lfgRoles=secret')
        self.assertEqual(self.names(c, 'HEALER'), ['Heals'])
        self.assertEqual(self.names(c, 'unknown'), ['Mystery'])
        c.lua.execute('finderPlayers[2][1].lfgRoles={tank=secret,healer="true",dps=true}')
        self.assertEqual(self.names(c, 'TANK'), ['Tanky'])
        self.assertEqual(self.names(c, 'DAMAGER', 7), ['Mystery'])


if __name__ == '__main__':
    unittest.main()
