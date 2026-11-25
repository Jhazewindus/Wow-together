"""Forever finder structure adapters.

Host Lua 5.1 checks validate transforms and UI ownership, not beta alignment.
"""
import unittest

from test_addon import Client
from test_0864 import FINDER


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

    def test_classic_header_has_both_dropdowns_without_reparenting_native_frames(self):
        from test_0866 import NATIVE_FINDER
        c = Client(before_load=NATIVE_FINDER)
        c.lua.execute('''
          function LFGParentFrame:SetScript()error('native hook')end
          function LFGBrowseFrame:SetScript()error('native hook')end
          function LFGBrowseFrame:SetParent()error('native reparent')end
          function LFGBrowseFrame:Hide()error('native hide')end
        ''')
        c.ns.RefreshGroupFinderRoles(); f = c.ns.groupFinderNativeBar
        self.assertTrue(f.IsShown(f)); self.assertIsNone(c.ns.groupFinderRoleWindow)
        f.roles.options.HEALER.OnClick(); f.classes.options[7].OnClick()
        self.assertEqual(list(c.lua.globals().shownIDs().values()), [1,2])
        self.assertEqual(f.classes.width, 120)

    def test_classic_tab_changes_close_reopen_and_native_activity_refresh(self):
        from test_0866 import NATIVE_FINDER
        c = Client(before_load=NATIVE_FINDER); c.ns.RefreshGroupFinderRoles(); f = c.ns.groupFinderNativeBar
        c.lua.execute('LFGBrowseFrame.ActivityDropdown.selectedValues={20};LFGBrowseFrame.results={2};LFGBrowseFrame:UpdateResults()')
        c.ns.RefreshGroupFinderRoles(); self.assertEqual(list(c.lua.globals().shownIDs().values()), [2])
        c.lua.execute('LFGBrowseFrame:Hide()'); c.ns.RefreshGroupFinderRoles()
        self.assertFalse(f.IsShown(f))
        c.lua.execute('LFGBrowseFrame:Show()'); c.ns.RefreshGroupFinderRoles()
        self.assertTrue(f.IsShown(f))
        c.lua.execute('LFGParentFrame:Hide()'); c.ns.RefreshGroupFinderRoles()
        self.assertFalse(f.IsShown(f))
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
