"""Secret-client native UI isolation and public dungeon/finder adapters.

Host Lua 5.1 checks cannot verify actual Forever API delivery or remove taint.
"""
import unittest

from test_addon import Client
import test_0819
from test_0824 import NATIVE
from test_dungeon_player import TRACK, tick


ENTRY = '''
function IsInInstance() return true,'party' end
function GetInstanceInfo()return 'Ragefire Chasm','party',1,nil,nil,nil,nil,389 end
'''
WORLD = '''
C_Map.GetPlayerMapPosition=function()return nil end
function CreateVector2D(x,y)return {x=x,y=y,GetXY=function(self)return self.x,self.y end}end
worldX=120;worldY=-90;worldInstance=389;floorWorld=389;convertedMap=400;convertedX=.3
function UnitPosition()return worldX,worldY,5,worldInstance end
C_Map.GetWorldPosFromMapPos=function(id,vector) assert(id==400);return floorWorld,CreateVector2D(0,0)end
conversions=0
C_Map.GetMapPosFromWorldPos=function(world,vector,map)
 assert(world==389 and vector.x==120 and vector.y==-90 and map==400)
 conversions=conversions+1;return convertedMap,CreateVector2D(convertedX,.6)
end
'''
FINDER = '''
LFGListFrame=CreateFrame('Frame',nil,UIParent);LFGListFrame:Show()
LFGListFrame.SearchPanel=CreateFrame('Frame',nil,LFGListFrame);LFGListFrame.SearchPanel:Show()
LFGListFrame.ApplicationViewer=CreateFrame('Frame',nil,LFGListFrame)
finderReads=0
finderInfo={[1]={name='RFC group',leaderName='Tanky',numMembers=3},[2]={name='Second group',numMembers=1}}
finderPlayers={
 [1]={{name='Tanky',className='Warrior',level=15,assignedRole='TANK'},
      {name='Heals',className='Priest',level=15,assignedRole='HEALER'},
      {name='Damagey',className='Mage',level=16,assignedRole='DAMAGER'}},
 [2]={{name='Mystery',className='Warrior',level=14,assignedRole='NONE'}}}
C_LFGList={
 GetFilteredSearchResults=function()finderReads=finderReads+1;return 2,{1,2}end,
 GetSearchResultInfo=function(id)return finderInfo[id]end,
 GetSearchResultPlayerInfo=function(id,index)return finderPlayers[id][index]end,
 InviteApplicant=function()error('automatic invite')end,
 DeclineApplicant=function()error('automatic decline')end,
 Search=function()error('automatic search')end,
 GetApplicants=function()return {10}end,
 GetApplicantInfo=function()return {numMembers=2,applicationStatus='applied'}end,
 GetApplicantMemberInfo=function(id,index)
  if index==1 then return 'Flexible','PALADIN','Paladin',15,0,0,true,true,false,'TANK' end
  return 'Shooter','HUNTER','Hunter',15,0,0,false,false,true,'DAMAGER'
 end,
}
'''


class SecretTrackerTests(unittest.TestCase):
    def test_secret_aura_client_never_calls_native_selection_or_tracking(self):
        c = test_0819.QuestFocusTests().client()
        c.lua.execute('C_UnitAuras={GetAuraDataByIndex=function()error("must not read auras")end}')
        c.ns.UpdateGuideQuestFocus()
        c.ns.selectedRoute.stops[1].id = 901
        c.ns.UpdateGuideQuestFocus()
        c.lua.globals().combat = True
        c.ns.UpdateGuideQuestFocus()
        c.lua.globals().combat = False
        c.ns.handlers.PLAYER_REGEN_ENABLED()
        self.assertEqual(len(c.lua.globals().selections), 0)
        self.assertEqual(len(c.lua.globals().tracks), 0)
        self.assertIn('secret-aura client', c.ns.guideQuestFocusStatus)
        self.assertTrue(c.ns.selectedRoute)

    def test_late_secret_api_discovery_clears_native_pending_target(self):
        c = test_0819.QuestFocusTests().client()
        c.ns.UpdateGuideQuestFocus()
        c.ns.guideQuestFocusPending = True
        c.lua.execute('C_UnitAuras={GetAuraDataByIndex=function()end}')
        c.ns.UpdateGuideQuestFocus()
        self.assertIsNone(c.ns.guideQuestFocusTarget)
        self.assertIsNone(c.ns.guideQuestFocusPending)
        self.assertEqual(len(c.lua.globals().selections), 1)

    def test_no_blizzard_function_or_tracker_frame_is_replaced_or_hooked(self):
        c = Client(before_load='''
        function ShouldShowMawBuffs()error('native aura reader')end
        auraReader=ShouldShowMawBuffs
        ObjectiveTrackerFrame=CreateFrame('Frame');ObjectiveTrackerFrame:SetScript('OnUpdate',auraReader)
        function hooksecurefunc()error('native hook installed')end
        C_UnitAuras={GetAuraDataByIndex=auraReader}
        ''')
        c.lua.execute('assert(ShouldShowMawBuffs==auraReader);assert(ObjectiveTrackerFrame:GetScript("OnUpdate")==auraReader)')


class DungeonRecoveryTests(unittest.TestCase):
    def test_native_renderer_has_exact_letterboxed_geometry_and_only_the_player(self):
        c = Client(use_catalogue=True, before_load=NATIVE)
        c.lua.execute(TRACK + '''
            C_Map.GetPlayerMapPosition=function()return secret end
            oldCreate=CreateFrame;nativeCreates=0
            function CreateFrame(kind,...)
                local f=oldCreate(kind,...)
                if kind=='UnitPositionFrame' then
                    nativeCreates=nativeCreates+1
                    function f:SetUiMapID(id)self.renderMap=id end
                    function f:ClearUnits()self.units={}end
                    function f:AddUnit(unit,asset,w,h,r,g,b,a,layer,facing)
                        assert(unit=='player' and facing==true and w==26 and h==26)
                        self.units[#self.units+1]=unit
                    end
                    function f:FinalizeUnits()self.finalized=true end
                end
                return f
            end
        ''')
        c.ns.ShowDungeonViewer('ragefire-chasm', True); f = c.ns.dungeonViewer
        self.assertTrue(f.nativePlayer.IsShown(f.nativePlayer))
        self.assertFalse(f.playerMarker.IsShown(f.playerMarker))
        for width, height in ((500,420),(620,400)):
            f.SetSize(f,width,height); f.OnSizeChanged(); tick(f)
            g, native = f.playerGeometry, f.nativePlayer
            self.assertEqual(native.renderMap, 400)
            self.assertEqual(native.width, g.width); self.assertEqual(native.height, g.height)
            self.assertEqual(native.point[4], g.x); self.assertEqual(native.point[5], -g.y)
            self.assertEqual(list(native.units.values()), ['player'])
        self.assertEqual(c.lua.globals().nativeCreates, 1)
        c.lua.globals().trackedMap = 1411; tick(f)
        self.assertFalse(f.nativePlayer.IsShown(f.nativePlayer))

    def test_unsupported_or_failed_native_renderer_falls_back_without_retry(self):
        c = Client(use_catalogue=True, before_load=NATIVE)
        c.lua.execute(TRACK + '''
            oldCreate=CreateFrame;nativeCreates=0
            function CreateFrame(kind,...)
                if kind=='UnitPositionFrame' then nativeCreates=nativeCreates+1;error('unknown frame type')end
                return oldCreate(kind,...)
            end
        ''')
        c.ns.ShowDungeonViewer('ragefire-chasm', True); f = c.ns.dungeonViewer
        self.assertTrue(f.playerMarker.IsShown(f.playerMarker))
        c.ns.RenderDungeonViewer(); tick(f)
        self.assertEqual(c.lua.globals().nativeCreates, 1)
        c.lua.execute('px=secret'); tick(f)
        self.assertFalse(f.playerMarker.IsShown(f.playerMarker))
        self.assertIsNone(f.nativePlayer)

    def test_open_reference_map_upgrades_on_entry_without_prompt(self):
        c = Client(use_catalogue=True)
        c.ns.ShowDungeonViewer('ragefire-chasm', True); f = c.ns.dungeonViewer
        self.assertTrue(f.data.maps[1].reference)
        c.ns.db.config.dungeonMapPrompt = False
        c.lua.execute(NATIVE + TRACK + ENTRY)
        c.ns.handlers.PLAYER_ENTERING_WORLD()
        self.assertEqual(f.playerGeometry.mapID, 400)
        self.assertTrue(f.playerMarker.IsShown(f.playerMarker))
        self.assertEqual(f.floor, 1)

    def test_world_position_fallback_uses_exact_native_map_and_geometry(self):
        c = Client(use_catalogue=True, before_load=NATIVE)
        c.lua.execute(TRACK + WORLD)
        c.ns.ShowDungeonViewer('ragefire-chasm', True); f = c.ns.dungeonViewer
        tick(f)
        self.assertTrue(f.playerMarker.IsShown(f.playerMarker))
        self.assertAlmostEqual((f.playerMarker.point[4]-f.playerGeometry.x)/f.playerGeometry.width, .3)
        self.assertIn('world-to-map', c.ns.dungeonPlayerStatus)
        self.assertGreater(c.lua.globals().conversions, 0)

    def test_world_conversion_rejects_private_wrong_world_and_other_floor(self):
        c = Client(use_catalogue=True, before_load=NATIVE)
        c.lua.execute(TRACK + WORLD)
        c.ns.ShowDungeonViewer('ragefire-chasm', True); f = c.ns.dungeonViewer
        for change in ('worldX=secret', 'worldX=120;floorWorld=0',
                       'floorWorld=389;convertedMap=401', 'convertedMap=400;convertedX=1.2'):
            c.lua.execute(change); tick(f)
            self.assertFalse(f.playerMarker.IsShown(f.playerMarker))
        c.lua.execute('convertedX=.3'); tick(f)
        self.assertTrue(f.playerMarker.IsShown(f.playerMarker))

    def test_confirmed_single_native_floor_can_use_outdoor_best_map_id(self):
        c = Client(use_catalogue=True, before_load=NATIVE)
        c.lua.execute(TRACK + ENTRY + WORLD + 'trackedMap=1454;C_Map.GetMapGroupMembersInfo=function()end')
        c.ns.ShowDungeonViewer('ragefire-chasm', True); f = c.ns.dungeonViewer
        self.assertEqual(len(f.data.maps), 1)
        self.assertTrue(f.playerMarker.IsShown(f.playerMarker))
        c.lua.execute('C_Map.GetBestMapForUnit=function()end'); tick(f)
        self.assertTrue(f.playerMarker.IsShown(f.playerMarker))
        c.lua.execute('function GetInstanceInfo()return "Another Dungeon","party" end'); tick(f)
        self.assertFalse(f.playerMarker.IsShown(f.playerMarker))

    def test_instance_confirmed_orphan_floor_is_discovered_without_journal(self):
        c = Client(use_catalogue=True, before_load=NATIVE)
        c.lua.execute(TRACK + ENTRY + '''
            EJ_GetInstanceByIndex=nil;EJ_GetInstanceInfo=nil
            C_Map.GetMapInfo=function(id)return {name='Ragefire Chasm',mapType=6}end
            C_Map.GetMapGroupMembersInfo=function()end
        ''')
        c.ns.ShowDungeonViewer('ragefire-chasm', True); f = c.ns.dungeonViewer
        self.assertEqual(f.data.maps[1].mapID, 400)
        self.assertTrue(f.playerMarker.IsShown(f.playerMarker))

    def test_reference_map_does_not_attempt_world_conversion(self):
        c = Client(use_catalogue=True)
        c.lua.execute('C_Map={};' + TRACK + ENTRY + WORLD)
        c.ns.ShowDungeonViewer('ragefire-chasm', True); f = c.ns.dungeonViewer
        tick(f)
        self.assertTrue(f.data.maps[1].reference)
        self.assertFalse(f.playerMarker.IsShown(f.playerMarker))
        self.assertEqual(c.lua.globals().conversions, 0)


class FinderRoleTests(unittest.TestCase):
    def client(self):
        return Client(before_load=FINDER)

    def test_filters_declared_player_roles_and_keeps_unknown_separate(self):
        c = self.client()
        for role, names in (('all', ['Tanky','Heals','Damagey','Mystery']),
                            ('TANK', ['Tanky']), ('HEALER', ['Heals']),
                            ('DAMAGER', ['Damagey']), ('unknown', ['Mystery'])):
            result = c.ns.ReadGroupFinderPlayers('search', role)
            rows = result[0] if isinstance(result, tuple) else result
            self.assertEqual([row.name for row in rows.values()], names)

    def test_old_member_api_uses_public_leader_and_does_not_invent_names(self):
        c = self.client()
        c.lua.execute('''
            C_LFGList.GetSearchResultPlayerInfo=nil
            C_LFGList.GetSearchResultMemberInfo=function(id,index)return 'TANK','WARRIOR','Warrior',15 end
        ''')
        rows = c.ns.ReadGroupFinderPlayers('search','TANK')[0]
        self.assertEqual([row.name for row in rows.values()], ['Tanky'])

    def test_search_uses_documented_role_enum_flags_and_skips_duplicate_listings(self):
        c = self.client()
        c.lua.execute('''
            bit={band=function(a,b)return a==b and b or 0 end}
            Enum.LFGRoles={Tank=2,Healer=4,Damage=8}
            finderPlayers[2][1].lfgRoles=4
            C_LFGList.GetFilteredSearchResults=function()return 3,{1,2,2}end
        ''')
        rows = c.ns.ReadGroupFinderPlayers('search','HEALER')[0]
        self.assertEqual([row.name for row in rows.values()], ['Heals','Mystery'])

    def test_multi_role_applicants_match_each_declared_role(self):
        c = self.client()
        for role, name in (('TANK','Flexible'),('HEALER','Flexible'),('DAMAGER','Shooter')):
            result = c.ns.ReadGroupFinderPlayers('applicants', role)
            rows = result[0] if isinstance(result, tuple) else result
            self.assertEqual([row.name for row in rows.values()], [name])

    def test_private_failed_missing_and_delisted_data_is_not_shown(self):
        c = self.client()
        c.lua.execute('finderPlayers[1][1].name=secret;finderInfo[2].isDelisted=true')
        rows = c.ns.ReadGroupFinderPlayers('search', 'all')[0]
        self.assertEqual([row.name for row in rows.values()], ['Heals','Damagey'])
        c.lua.execute('C_LFGList.GetFilteredSearchResults=function()error("unavailable")end')
        rows, message = c.ns.ReadGroupFinderPlayers('search', 'all')
        self.assertEqual(len(rows), 0); self.assertIn('unavailable', message)
        c.lua.execute('C_LFGList=nil')
        rows, message = c.ns.ReadGroupFinderPlayers('search', 'all')
        self.assertEqual(len(rows), 0)

    def test_sidebar_is_owned_and_does_not_mutate_native_frames_or_actions(self):
        c = self.client()
        c.lua.execute('''
            function LFGListFrame:SetScript()error('native script changed')end
            function LFGListFrame:SetParent()error('native parent changed')end
            function LFGListFrame:Hide()error('native hidden')end
            function LFGListFrame.SearchPanel:Hide()error('native rows hidden')end
            function hooksecurefunc()error('native hook installed')end
        ''')
        c.ns.RefreshGroupFinderRoles(); f = c.ns.groupFinderRoleWindow
        self.assertTrue(f.IsShown(f))
        c.lua.execute('assert((...).groupFinderRoleWindow:GetParent()==UIParent)', c.ns)
        f.filter.options.HEALER.OnClick()
        self.assertEqual(f.rows[1].data.name, 'Heals')
        self.assertFalse(f.rows[2].IsShown(f.rows[2]))
        self.assertTrue(c.lua.globals().LFGListFrame.SearchPanel.IsShown(c.lua.globals().LFGListFrame.SearchPanel))

    def test_close_reopen_disable_and_applicant_context(self):
        c = self.client(); c.ns.RefreshGroupFinderRoles(); f = c.ns.groupFinderRoleWindow
        f.close.OnClick(); c.ns.RefreshGroupFinderRoles(); self.assertFalse(f.IsShown(f))
        native = c.lua.globals().LFGListFrame
        native.Hide(native); c.ns.RefreshGroupFinderRoles(); native.Show(native)
        c.ns.RefreshGroupFinderRoles(); self.assertTrue(f.IsShown(f))
        native.SearchPanel.Hide(native.SearchPanel); native.ApplicationViewer.Show(native.ApplicationViewer)
        c.ns.RefreshGroupFinderRoles(); self.assertIn('Applicants', f.source.text)
        self.assertEqual(f.rows[1].data.name, 'Flexible')
        c.ns.db.config.groupFinderRoles = False; c.ns.RefreshGroupFinderRoles()
        self.assertFalse(f.IsShown(f))

    def test_native_events_defer_reads_and_controller_never_polls_hidden_data(self):
        c = self.client(); native = c.lua.globals().LFGListFrame
        controller = c.ns.groupFinderRoleController
        controller.OnUpdate(controller, .25)
        reads = c.lua.globals().finderReads
        c.ns.handlers.LFG_LIST_SEARCH_RESULT_UPDATED(1)
        self.assertEqual(c.lua.globals().finderReads, reads)
        controller.OnUpdate(controller, .25)
        self.assertEqual(c.lua.globals().finderReads, reads + 1)
        native.Hide(native)
        for _ in range(4): controller.OnUpdate(controller, .5)
        self.assertEqual(c.lua.globals().finderReads, reads + 1)

    def test_role_view_paginates_and_refresh_clamps_disappeared_results(self):
        c = self.client()
        c.lua.execute('''
          finderInfo[1].numMembers=9
          for i=4,9 do finderPlayers[1][i]={name='Player '..i,assignedRole='TANK'}end
        ''')
        c.ns.RefreshGroupFinderRoles(); f = c.ns.groupFinderRoleWindow
        self.assertEqual(f.pages, 2); f.next.OnClick(); self.assertEqual(f.page, 2)
        c.lua.execute('finderInfo[1].numMembers=1'); c.ns.RefreshGroupFinderRoles()
        self.assertEqual(f.page, 1); self.assertFalse(f.next.IsEnabled(f.next))


if __name__ == '__main__':
    unittest.main()
