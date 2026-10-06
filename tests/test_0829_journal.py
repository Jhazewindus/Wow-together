"""Journal boss floors, class loot choices and foreground stacking in Lua 5.1."""
import unittest

from test_addon import Client


FRAME_ORDER = '''
local methods=getmetatable(CreateFrame('Frame')).__index
function methods:SetFrameStrata(value) self.strata=value end
function methods:SetToplevel(value) self.topLevel=value end
function methods:Raise() self.raised=(self.raised or 0)+1 end
'''


class JournalInteractionTests(unittest.TestCase):
    def client(self, native_class="return 'Mage','MAGE',8"):
        return Client(use_catalogue=True, default_guide=True,
                      before_load=FRAME_ORDER + '\nfunction UnitClass() ' + native_class + ' end')

    def test_default_class_and_choice_survive_switching_dungeons(self):
        c = self.client(); c.ns.ShowDungeonViewer('ragefire-chasm'); f = c.ns.dungeonViewer
        self.assertEqual(8, f['class']); self.assertEqual('Mage', f.lootClass.caption.text)
        f.lootClass.options[1].OnClick()
        self.assertEqual(1, f['class']); self.assertEqual('Warrior', f.lootClass.caption.text)
        c.ns.ShowDungeonViewer('wailing-caverns')
        self.assertEqual(1, f['class']); self.assertEqual('Warrior', f.lootClass.caption.text)

    def test_unavailable_or_private_class_defaults_to_all_classes(self):
        for native in ('return nil', 'return secret,secret,secret', "return 'Unknown','UNKNOWN',123"):
            with self.subTest(native=native):
                c = self.client(native); c.ns.ShowDungeonViewer('ragefire-chasm')
                self.assertEqual(0, c.ns.dungeonViewer['class'])
                self.assertEqual('All classes', c.ns.dungeonViewer.lootClass.caption.text)

    def test_class_choice_intersects_type_and_search_and_resets_pagination(self):
        c = self.client(); c.ns.ShowDungeonViewer('ragefire-chasm'); f = c.ns.dungeonViewer
        c.lua.globals().testNS = c.ns
        c.lua.execute('''
          testNS.dungeonViewer.data.bosses[1].loot={
            {id=1,name='Gold cloth',classID=4,subclass=1,slot=5,quality=2},
            {id=2,name='Gold plate',classID=4,subclass=4,slot=5,quality=2},
            {id=3,name='Gold quest',classID=12,quality=2},
            {id=4,name='Silver cloth',classID=4,subclass=1,slot=5,quality=2}}
        ''')
        f.search.SetText(f.search, 'Gold'); f.search.OnTextChanged(f.search)
        f.lootType.options['equipment'].OnClick()
        self.assertEqual('Boss loot • 1', f.lootTitle.text)
        self.assertEqual('Gold cloth', f.lootRows[1].item.name)
        f.lootPage = 5; f.lootClass.options[1].OnClick()
        self.assertEqual(1, f.lootPage); self.assertEqual('Boss loot • 2', f.lootTitle.text)
        f.lootClass.options[0].OnClick()
        self.assertEqual('Boss loot • 2', f.lootTitle.text)
        f.lootType.options['other'].OnClick()
        self.assertEqual('Gold quest', f.lootRows[1].item.name)

    def test_weapon_and_armor_types_filter_without_hiding_shared_unknown_or_other_loot(self):
        c = self.client()
        boss = c.lua.table_from({'loot': [
            {'id': 1, 'name': 'Plate', 'classID': 4, 'subclass': 4, 'slot': 5},
            {'id': 2, 'name': 'Mail', 'classID': 4, 'subclass': 3, 'slot': 5},
            {'id': 3, 'name': 'Leather', 'classID': 4, 'subclass': 2, 'slot': 5},
            {'id': 4, 'name': 'Cloth', 'classID': 4, 'subclass': 1, 'slot': 5},
            {'id': 5, 'name': 'Shield', 'classID': 4, 'subclass': 6, 'slot': 14},
            {'id': 6, 'name': 'Sword', 'classID': 2, 'subclass': 7},
            {'id': 7, 'name': 'Wand', 'classID': 2, 'subclass': 19},
            {'id': 8, 'name': 'Totem', 'classID': 4, 'subclass': 9},
            {'id': 9, 'name': 'Ring', 'classID': 4, 'subclass': 4, 'slot': 11},
            {'id': 10, 'name': 'Cloak', 'classID': 4, 'subclass': 2, 'slot': 16},
            {'id': 11, 'name': 'Unknown armor', 'classID': 4},
            {'id': 12, 'name': 'New beta type', 'classID': 2, 'subclass': 99},
            {'id': 13, 'name': 'Quest item', 'classID': 12},
        ]}, recursive=True)
        def ids(class_id):
            return {i.id for i in c.ns.DungeonViewerLoot(boss, '', 'all', class_id).values()}
        common = {9, 10, 11, 12, 13}
        self.assertEqual(common | {4, 6, 7}, ids(8))  # Mage
        self.assertEqual(common | {2, 3, 4, 5, 8}, ids(7))  # Shaman
        self.assertEqual(common | {1, 2, 3, 4, 5, 6}, ids(1))  # Warrior
        self.assertEqual(set(range(1, 14)), ids(0))
        self.assertEqual(set(range(1, 14)), ids(None))

    def test_private_item_type_is_preserved_without_comparison(self):
        c = self.client(); c.lua.globals().testNS = c.ns
        self.assertTrue(c.lua.execute('return testNS.DungeonLootClassAllowed({classID=4,subclass=secret},8)'))
        self.assertTrue(c.lua.execute('return testNS.DungeonLootClassAllowed({classID=2,subclass=secret},8)'))

    def test_boss_selection_follows_actual_points_even_with_stale_floor_or_shared_map_id(self):
        c = self.client(); c.ns.ShowDungeonViewer('maraudon'); f = c.ns.dungeonViewer
        c.lua.globals().testNS = c.ns
        c.lua.execute('''
          local f=testNS.dungeonViewer
          f.data.bosses[1].mapFloor=1
          f.data.maps={
            {mapID=55,name='Upper',width=1002,height=668,tileWidth=256,tileHeight=256,tiles={},bosses={}},
            {mapID=55,name='Lower',width=1002,height=668,tileWidth=256,tileHeight=256,tiles={},
              bosses={{id=f.data.bosses[1].id,x=.5,y=.5}}}}
          f.floor=1
          testNS.RenderDungeonViewer()
        ''')
        f.bossRows[1].OnClick()
        self.assertEqual(2, f.floor); self.assertEqual('Lower', f.floorMenu.caption.text)
        self.assertEqual(f.bossID, f.pins[1].bossID)

    def test_native_point_wins_over_an_old_reference_and_unknown_floor_is_not_guessed(self):
        c = self.client()
        data = c.lua.table_from({'maps': [
            {'mapID': 55, 'bosses': [{'id': 100, 'x': .2, 'y': .2}]},
            {'mapID': 55, 'bosses': [{'id': 100, 'x': .8, 'y': .8, 'native': True}]},
        ]}, recursive=True)
        self.assertEqual(2, c.ns.DungeonBossFloor(data, c.lua.table_from({'id': 100, 'mapFloor': 1}), 1))
        self.assertEqual(2, c.ns.DungeonBossFloor(data, c.lua.table_from({'id': 101, 'mapID': 55}), 2))
        self.assertEqual(1, c.ns.DungeonBossFloor(data, c.lua.table_from({'id': 101}), 1))

    def test_journal_is_above_main_and_raises_when_reopened_in_both_modes(self):
        c = self.client(); c.ns.window.Show(c.ns.window)
        self.assertEqual('HIGH', c.ns.window.strata)
        c.ns.ShowDungeonViewer('ragefire-chasm'); f = c.ns.dungeonViewer
        self.assertEqual('DIALOG', f.strata); self.assertTrue(f.topLevel); self.assertEqual(1, f.raised)
        f.Hide(f); c.ns.ShowDungeonViewer('wailing-caverns', True)
        self.assertTrue(f.compact); self.assertEqual('DIALOG', f.strata); self.assertEqual(2, f.raised)

    def test_class_and_floor_controls_remain_usable_in_combat_after_resize(self):
        c = self.client(); c.ns.ShowDungeonViewer('maraudon'); f = c.ns.dungeonViewer
        c.lua.execute('function InCombatLockdown() return true end')
        f.SetSize(f, 940, 500); f.OnSizeChanged()
        f.lootClass.options[7].OnClick(); f.floorMenu.options[2].OnClick()
        self.assertEqual(7, f['class']); self.assertEqual(2, f.floor)
        self.assertTrue(f.IsShown(f)); self.assertLessEqual(f.lootRowsVisible, 3)
        self.assertGreater(f.search.width, 0)


if __name__ == '__main__':
    unittest.main()
