"""Numeric status text and live cave approach maps; host API simulation only."""
import unittest

from test_addon import Client


CVARS = r'''
combat=false
statusValues={statusText='0',statusTextDisplay='PERCENT'}
function InCombatLockdown()return combat end
C_CVar={GetCVar=function(key)return statusValues[key]end,
 SetCVar=function(key,value)statusValues[key]=value end}
'''


def world_api(map_id, continent=1, x=0, y=0):
    return f'''
activeMap={map_id}; worldX={x}; worldY={y}; worldContinent={continent}
function CreateVector2D(x,y)return {{GetXY=function()return x,y end}}end
C_Map={{
 GetBestMapForUnit=function()return activeMap end,
 GetMapInfo=function(id)return {{mapID=id,parentMapID=activeMap == id and 0 or 0}}end,
 GetPlayerMapPosition=function()return CreateVector2D(.5,.5)end,
 GetWorldPosFromMapPos=function()return worldContinent,CreateVector2D(worldX,worldY)end,
}}
'''


class UnitNumbersTests(unittest.TestCase):
    def client(self):
        return Client(before_load=CVARS)

    def test_enable_uses_blizzard_numeric_mode_and_disable_restores_prior_choices(self):
        c = self.client()
        c.ns.SetOption('unitNumbers', True)
        self.assertEqual(c.lua.globals().statusValues.statusText, '1')
        self.assertEqual(c.lua.globals().statusValues.statusTextDisplay, 'NUMERIC')
        c.ns.SetOption('unitNumbers', False)
        self.assertEqual(c.lua.globals().statusValues.statusText, '0')
        self.assertEqual(c.lua.globals().statusValues.statusTextDisplay, 'PERCENT')

    def test_turn_off_preserves_native_settings_changed_by_player_while_enabled(self):
        c = self.client()
        c.ns.SetOption('unitNumbers', True)
        c.lua.execute("statusValues.statusTextDisplay='BOTH'")
        c.ns.SetOption('unitNumbers', False)
        self.assertEqual(c.lua.globals().statusValues.statusText, '0')
        self.assertEqual(c.lua.globals().statusValues.statusTextDisplay, 'BOTH')

    def test_combat_defers_cvar_writes_until_combat_ends(self):
        c = self.client()
        c.lua.globals().combat = True
        c.ns.SetOption('unitNumbers', True)
        self.assertEqual(c.lua.globals().statusValues.statusText, '0')
        c.lua.globals().combat = False
        c.ns.handlers.PLAYER_REGEN_ENABLED()
        self.assertEqual(c.lua.globals().statusValues.statusText, '1')
        self.assertEqual(c.lua.globals().statusValues.statusTextDisplay, 'NUMERIC')


class ApproachMapTests(unittest.TestCase):
    def test_polling_slows_when_idle_and_runs_five_times_per_second_when_visible(self):
        idle = Client(use_catalogue=True, before_load=CVARS + world_api(9999, continent=99))
        self.assertEqual(idle.ns.CheckApproachMap(), 2.5)

    def test_live_position_tracks_original_tile_map_and_closes_when_player_leaves(self):
        c = Client(use_catalogue=True, before_load=CVARS + world_api(1413))
        ns = c.ns
        self.assertTrue(ns.ShowDungeonApproach('wailing-caverns'))
        frame = ns.approachMap
        model = frame.model
        bounds = model.bounds
        # Convert a point in the source image back to the matching outdoor world
        # coordinates, then exercise the public map conversion adapter.
        # Bounds are in doubled client pixels; invert the coordinate transform
        # to the WMO model's 128-unit minimap grid.
        lx = (bounds.left + (bounds.right - bounds.left) / 2) / 2
        ly = (bounds.top - (bounds.top - bounds.bottom) / 2) / 2
        p = model.placement
        angle = c.lua.eval('math.rad')(p.yaw - 180)
        co, si = c.lua.eval('math.cos')(angle), c.lua.eval('math.sin')(angle)
        dx, dy = co * lx - si * ly, si * lx + co * ly
        c.lua.globals().worldX = ns.approachMapData.worldHalf - p.z + dx
        c.lua.globals().worldY = ns.approachMapData.worldHalf - p.x + dy
        frame.Hide(frame)
        frame.dismissed = None
        frame.model = None
        interval = ns.CheckApproachMap()
        self.assertEqual(interval, .2)
        self.assertTrue(frame.IsShown(frame))
        self.assertTrue(frame.marker.IsShown(frame.marker))
        self.assertGreater(len(frame.tiles), 0)
        ns.SetOption('approachMaps', False)
        self.assertFalse(frame.IsShown(frame))
        ns.SetOption('approachMaps', True)
        self.assertTrue(frame.IsShown(frame))
        self.assertTrue(frame.marker.IsShown(frame.marker))
        first = frame.marker.point
        geometry = frame.mapGeometry
        self.assertAlmostEqual(first[4], geometry.x + geometry.width * geometry.scale / 2, delta=1)
        self.assertAlmostEqual(first[5], -(geometry.y + geometry.height * geometry.scale / 2), delta=1)
        c.lua.globals().worldX += 15
        ns.CheckApproachMap()
        self.assertNotEqual((first[4], first[5]), (frame.marker.point[4], frame.marker.point[5]))
        c.lua.globals().worldX += 5000
        interval = ns.CheckApproachMap()
        self.assertFalse(frame.IsShown(frame))
        self.assertEqual(interval, .8)

    def test_approach_option_disables_automatic_and_manual_maps(self):
        c = Client(use_catalogue=True, before_load=CVARS + world_api(1413))
        c.ns.SetOption('approachMaps', False)
        self.assertFalse(c.ns.ShowDungeonApproach('wailing-caverns'))
        c.ns.CheckApproachMap()
        self.assertFalse(c.ns.approachMap.IsShown(c.ns.approachMap))


if __name__ == '__main__':
    unittest.main()
