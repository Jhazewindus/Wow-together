"""Native Forever Browse filtering and the actual RFC missing-coordinate case."""
import unittest

from test_addon import Client
from test_0865 import CLASSIC, REFERENCE
from test_dungeon_player import tick


NATIVE_FINDER = CLASSIC + '''
function InCombatLockdown()return combat==true end
nativeHooks={}; nativeRebuilds=0;providerChanges=0;nativeSelection=nil
function hooksecurefunc(object, method, fn)
 assert(object==LFGBrowseFrame and method=='UpdateResults')
 nativeHooks[#nativeHooks+1]=fn
end
function CreateTreeDataProvider()
 local function node(data)
  local n={data=data,children={}}
  function n:Insert(d)local child=node(d);self.children[#self.children+1]=child;return child end
  return n
 end
 return node(nil)
end
ScrollBoxConstants={RetainScrollPosition=true}
LFGVANILLA_SETTING_BROWSE_SHOW_COLLAPSIBLE_CATEGORIES=true
LFGBrowseFrame.CategoryDropdown=CreateFrame('Frame',nil,LFGBrowseFrame)
LFGBrowseFrame.ScrollBox=CreateFrame('Frame',nil,LFGBrowseFrame)
LFGBrowseFrame.NoResultsFound=CreateFrame('Frame',nil,LFGBrowseFrame)
LFGBrowseFrame.SendMessageButton=CreateFrame('Button',nil,LFGBrowseFrame)
LFGBrowseFrame.GroupInviteButton=CreateFrame('Button',nil,LFGBrowseFrame)
LFGBrowseFrame.selectionBehavior={ClearSelections=function()nativeSelection=nil end}
function LFGBrowseFrame.ScrollBox:GetDataProvider()return self.provider end
function LFGBrowseFrame.ScrollBox:SetDataProvider(p)
 assert(not combat,'provider changed in combat')
 self.provider=p;providerChanges=providerChanges+1
end
function LFGBrowseFrame:UpdateButtonState()
 self.SendMessageButton:SetEnabled(nativeSelection~=nil)
 self.GroupInviteButton:SetEnabled(nativeSelection~=nil)
end
function LFGBrowseFrame:UpdateResults()
 nativeRebuilds=nativeRebuilds+1
 local p=CreateTreeDataProvider()
 for i,id in ipairs(self.results)do p:Insert({index=i,resultID=id})end
 self.ScrollBox:SetDataProvider(p);self:UpdateButtonState()
 for _,fn in ipairs(nativeHooks)do fn()end
end
function shownIDs()
 local ids={}
 local function visit(node)
  if node.data and node.data.resultID then ids[#ids+1]=node.data.resultID end
  for _,child in ipairs(node.children)do visit(child)end
 end
 visit(LFGBrowseFrame.ScrollBox:GetDataProvider())
 return ids
end
-- Group plus three solo players. Role and class must match the same player.
finderInfo[3]={numMembers=1,activityIDs={10}}
finderInfo[4]={numMembers=1,activityIDs={10}}
finderPlayers[3]={{name='Priesty',className='Priest',classFilename='PRIEST',level=15,
 assignedRole='NONE',lfgRoles={healer=true,dps=true}}}
finderPlayers[4]={{name='Magey',className='Mage',classFilename='MAGE',level=15,
 assignedRole='DAMAGER'}}
LFGBrowseFrame.results={1,2,3,4}
LFGBrowseFrame:UpdateResults()
'''


class NativeFinderTests(unittest.TestCase):
    def client(self):
        c=Client(before_load=NATIVE_FINDER)
        c.ns.RefreshGroupFinderRoles()
        return c,c.ns.groupFinderNativeBar

    def ids(self,c):
        return list(c.lua.globals().shownIDs().values())

    def test_controls_inside_native_header_and_no_companion_window(self):
        c,bar=self.client()
        self.assertTrue(bar.IsShown(bar))
        c.lua.execute('assert((...).groupFinderNativeBar:GetParent()==LFGBrowseFrame)',c.ns)
        self.assertEqual(bar.point[1],'TOPLEFT')
        self.assertIsNone(c.ns.groupFinderRoleWindow)
        self.assertEqual(self.ids(c),[1,2,3,4])

    def test_filters_native_players_with_class_role_intersection_and_keeps_groups(self):
        c,bar=self.client()
        bar.roles.options.HEALER.OnClick()
        self.assertEqual(self.ids(c),[1,2,3])
        bar.classes.options[7].OnClick()
        self.assertEqual(self.ids(c),[1,2])
        bar.roles.options.TANK.OnClick()
        self.assertEqual(self.ids(c),[1])
        bar.classes.options[0].OnClick();bar.roles.options['all'].OnClick()
        self.assertEqual(self.ids(c),[1,2,3,4])
        self.assertEqual(list(c.lua.globals().LFGBrowseFrame.results.values()),[1,2,3,4])

    def test_original_indices_and_result_ids_keep_native_selection_accurate(self):
        c,bar=self.client();bar.classes.options[8].OnClick()
        self.assertEqual(self.ids(c),[1,4])
        c.lua.execute('''
          local tree=LFGBrowseFrame.ScrollBox:GetDataProvider()
          local entry=tree.children[2].children[1].data
          assert(entry.resultID==4 and entry.index==4 and entry.category==1)
          nativeSelection=entry.resultID;LFGBrowseFrame:UpdateButtonState()
        ''')
        self.assertTrue(c.lua.globals().LFGBrowseFrame.GroupInviteButton.IsEnabled(c.lua.globals().LFGBrowseFrame.GroupInviteButton))
        bar.classes.options[5].OnClick()
        self.assertIsNone(c.lua.globals().nativeSelection)
        self.assertFalse(c.lua.globals().LFGBrowseFrame.GroupInviteButton.IsEnabled(c.lua.globals().LFGBrowseFrame.GroupInviteButton))

    def test_refresh_uses_new_native_results_without_reordering_or_stale_entries(self):
        c,bar=self.client();bar.roles.options.HEALER.OnClick()
        c.lua.execute('LFGBrowseFrame.results={3,4};LFGBrowseFrame:UpdateResults()')
        c.ns.groupFinderRoleController.OnUpdate(c.ns.groupFinderRoleController,1)
        self.assertEqual(self.ids(c),[3])
        bar.roles.options['all'].OnClick()
        self.assertEqual(self.ids(c),[3,4])
        self.assertEqual(len(c.lua.globals().nativeHooks),1)

    def test_idle_poll_does_not_rebuild_provider_or_clear_selected_player(self):
        c,bar=self.client();bar.roles.options.HEALER.OnClick()
        before=c.lua.globals().providerChanges
        c.lua.execute('nativeSelection=2')
        for _ in range(5):c.ns.RefreshGroupFinderRoles()
        self.assertEqual(c.lua.globals().providerChanges,before)
        self.assertEqual(c.lua.globals().nativeSelection,2)

    def test_declared_role_update_is_applied_without_a_new_search(self):
        c,bar=self.client();bar.roles.options.HEALER.OnClick()
        c.lua.execute('finderPlayers[2][1].lfgRoles.healer=false')
        c.ns.handlers.LFG_LIST_SEARCH_RESULT_UPDATED(2)
        c.ns.groupFinderRoleController.OnUpdate(c.ns.groupFinderRoleController,.25)
        self.assertEqual(self.ids(c),[1,3])

    def test_combat_defers_provider_updates_and_resumes_after_combat(self):
        c,bar=self.client();bar.roles.options.HEALER.OnClick()
        c.lua.execute('combat=true;finderPlayers[2][1].lfgRoles.healer=false')
        before=c.lua.globals().providerChanges
        c.ns.RefreshGroupFinderRoles()
        self.assertEqual(c.lua.globals().providerChanges,before)
        self.assertFalse(bar.roles.IsEnabled(bar.roles))
        c.lua.execute('combat=false');c.ns.handlers.PLAYER_REGEN_ENABLED()
        c.ns.groupFinderRoleController.OnUpdate(c.ns.groupFinderRoleController,.25)
        self.assertEqual(self.ids(c),[1,3])
        self.assertTrue(bar.roles.IsEnabled(bar.roles))

    def test_setting_off_and_native_tab_hide_restore_original_results(self):
        c,bar=self.client();bar.roles.options.HEALER.OnClick()
        c.ns.db.config.groupFinderRoles=False;c.ns.RefreshGroupFinderRoles()
        self.assertFalse(bar.IsShown(bar));self.assertEqual(self.ids(c),[1,2,3,4])
        c.ns.db.config.groupFinderRoles=True;c.ns.RefreshGroupFinderRoles()
        self.assertTrue(bar.IsShown(bar));self.assertEqual(self.ids(c),[1,2,3])
        c.lua.execute('LFGBrowseFrame:Hide()');c.ns.RefreshGroupFinderRoles()
        self.assertFalse(bar.IsShown(bar));self.assertEqual(self.ids(c),[1,2,3,4])

    def test_empty_filtered_results_and_restoring_all(self):
        c,bar=self.client()
        c.lua.execute('LFGBrowseFrame.results={4};LFGBrowseFrame:UpdateResults()')
        bar.roles.options.HEALER.OnClick()
        self.assertEqual(self.ids(c),[])
        self.assertTrue(c.lua.globals().LFGBrowseFrame.NoResultsFound.IsShown(c.lua.globals().LFGBrowseFrame.NoResultsFound))
        bar.roles.options['all'].OnClick()
        self.assertEqual(self.ids(c),[4])
        self.assertFalse(c.lua.globals().LFGBrowseFrame.NoResultsFound.IsShown(c.lua.globals().LFGBrowseFrame.NoResultsFound))

    def test_private_class_unknown_role_and_no_native_method_replacement(self):
        c,bar=self.client()
        original=c.lua.globals().LFGBrowseFrame.UpdateResults
        c.lua.execute('finderPlayers[2][1].classFilename=secret')
        bar.classes.options[7].OnClick();self.assertEqual(self.ids(c),[1])
        c.lua.execute('assert(LFGBrowseFrame.UpdateResults==...)',original)
        self.assertEqual(len(c.lua.globals().nativeHooks),1)

    def test_self_listing_is_not_hidden_or_nested_in_last_category(self):
        c,bar=self.client()
        c.lua.execute('finderInfo[4].hasSelf=true')
        bar.roles.options.HEALER.OnClick()
        self.assertEqual(self.ids(c),[1,2,3,4])
        c.lua.execute('local p=LFGBrowseFrame.ScrollBox:GetDataProvider();assert(p.children[3].data.resultID==4)')

    def test_unsupported_native_provider_never_opens_a_separate_window(self):
        c=Client(before_load=CLASSIC)
        c.ns.RefreshGroupFinderRoles()
        self.assertIsNone(c.ns.groupFinderRoleWindow)
        self.assertIsNone(c.ns.groupFinderNativeBar)
        self.assertIn('no supported',c.ns.groupFinderNativeStatus)

    def test_provider_failure_restores_all_results_and_resets_filter_choices(self):
        c,bar=self.client()
        c.lua.execute('''
          local original=LFGBrowseFrame.ScrollBox.SetDataProvider
          local fail=true
          function LFGBrowseFrame.ScrollBox:SetDataProvider(p)
            if fail then fail=false;error('unsupported provider') end
            return original(self,p)
          end
        ''')
        bar.roles.options.HEALER.OnClick()
        self.assertEqual(self.ids(c),[1,2,3,4])
        self.assertIn('All roles',bar.roles.text)
        self.assertIn('All classes',bar.classes.text)
        bar.roles.options.HEALER.OnClick()
        self.assertEqual(self.ids(c),[1,2,3])

    def test_protected_provider_is_never_modified(self):
        c,bar=self.client()
        c.lua.execute('function LFGBrowseFrame.ScrollBox:IsProtected()return true end')
        before=c.lua.globals().providerChanges
        bar.roles.options.HEALER.OnClick()
        self.assertEqual(c.lua.globals().providerChanges,before)
        self.assertEqual(self.ids(c),[1,2,3,4])

    def test_partial_provider_failure_is_recovered_on_next_poll(self):
        c,bar=self.client()
        c.lua.execute('''
          local original=LFGBrowseFrame.ScrollBox.SetDataProvider
          local calls=0
          function LFGBrowseFrame.ScrollBox:SetDataProvider(p)
            calls=calls+1
            if calls==1 then self.provider=p;error('partial update') end
            if calls==2 then error('temporary restore failure') end
            return original(self,p)
          end
        ''')
        bar.roles.options.HEALER.OnClick()
        c.ns.RefreshGroupFinderRoles()
        self.assertEqual(self.ids(c),[1,2,3,4])


class MissingDungeonPositionTests(unittest.TestCase):
    def test_reported_rfc_nil_xy_instance_389_is_static_not_fake_live_position(self):
        c=Client(use_catalogue=True,before_load=REFERENCE)
        c.lua.execute('UnitPosition=function()return nil,nil,nil,389 end;C_Map.GetBestMapForUnit=function()end')
        c.ns.ShowDungeonViewer('ragefire-chasm',True);f=c.ns.dungeonViewer;tick(f)
        self.assertFalse(f.playerMarker.IsShown(f.playerMarker))
        self.assertEqual(f.refresh.caption.text,'Static map')
        self.assertTrue(f.tiles[1].IsShown(f.tiles[1]))
        self.assertFalse(c.ns.LocateDungeonPlayer(f))
        self.assertIsNone(f.nativePlayer)

    def test_real_coordinates_restore_locate_without_reopening_map(self):
        c=Client(use_catalogue=True,before_load=REFERENCE)
        c.lua.execute('originalPosition=UnitPosition;UnitPosition=function()return nil,nil,nil,389 end')
        c.ns.ShowDungeonViewer('ragefire-chasm',True);f=c.ns.dungeonViewer;tick(f)
        self.assertEqual(f.refresh.caption.text,'Static map')
        c.lua.execute('UnitPosition=originalPosition');tick(f)
        self.assertEqual(f.refresh.caption.text,'Locate me')
        self.assertTrue(f.playerMarker.IsShown(f.playerMarker))


if __name__=='__main__':unittest.main()
