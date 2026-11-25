"""Secret-client quest tracking and public finder adapters.

Host Lua 5.1 checks cannot verify actual Forever API delivery or remove taint.
"""
import unittest

from test_addon import Client
import test_0819


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
