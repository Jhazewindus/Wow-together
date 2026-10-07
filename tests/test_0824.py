"""Offline dungeon viewer and read-only beta adapters. No real client execution."""
import json, unittest
from pathlib import Path
from test_addon import Client, ROOT

NATIVE = r'''
function InCombatLockdown() return combat == true end
function EJ_GetInstanceByIndex(index)
 if index == 1 then return 100, 'Ragefire Chasm', nil, nil, 1001 end
end
function EJ_GetInstanceInfo(id) return 'Ragefire Chasm', nil, 1002, nil, nil, nil, 400 end
function EJ_GetEncounterInfoByIndex(index, instance)
 assert(instance==100)
 if index==1 then return 'Taragaman the Hungerer', nil, 77 end
end
function EJ_GetEncounterInfo(id) if id==77 then return 'Taragaman the Hungerer' end end
function EJ_GetCreatureInfo(index,id) return 1,'Taragaman the Hungerer',nil,1,222 end
function EJ_SelectInstance() error('viewer must not select journal state') end
function EJ_SetCurrentTier() error('viewer must not change tiers') end
function EJ_SelectEncounter() error('viewer must not select encounters') end
C_Map={
 GetBestMapForUnit=function() return 1411 end,
 GetMapInfo=function(id) return {name='Durotar'} end,
 GetMapGroupID=function(id) return 901 end,
 GetMapGroupMembersInfo=function(id) return {{mapID=400,name='Main floor'}, {mapID=401,name='Lower floor'}} end,
 GetMapArtLayers=function(id) return {{layerWidth=1002,layerHeight=668,tileWidth=256,tileHeight=256}} end,
 GetMapArtLayerTextures=function(id) return {11,12,13,14,15,16,17,18,19,20,21,22} end,
}
C_EncounterJournal={GetEncountersOnMap=function(id) return {{encounterID=77,mapX=.4,mapY=.6},{encounterID=78,mapX=.2,mapY=.3}} end}
'''

class DungeonViewerTests(unittest.TestCase):
    def client(self, native=False):
        return Client(use_catalogue=True, default_guide=True, before_load=NATIVE if native else None)
    def test_snapshot_has_attributed_facts_and_no_external_assets(self):
        c=self.client(); data=c.ns.dungeonJournalData
        self.assertEqual(28,len(list(data.dungeons.keys())))
        self.assertEqual(22,data.counts.dungeonsWithBosses)
        self.assertGreater(data.counts.lootEntries,1000)
        for key,entry in data.dungeons.items():
            self.assertTrue(c.ns.dungeonData.dungeons[key])
            for boss in entry.bosses.values():
                self.assertGreater(boss.id,0)
                if boss.portrait:self.assertTrue(boss.portrait.startswith('Interface\\'))
                for id in boss.dropIDs.values():
                    item = data['items'][id]
                    self.assertTrue(item.name);self.assertGreater(item.id,0)
                    if item.icon:self.assertTrue(item.icon.startswith('Interface\\Icons\\'))
            for m in entry.maps.values():
                self.assertEqual(12,len(m.tiles))
                self.assertTrue(all(p.startswith('Interface\\') for p in m.tiles.values()))
        manifest=json.loads((ROOT/'WowTogether/DungeonJournalData.json').read_text())
        self.assertEqual(933,len(manifest['vanillaNPCSources']))
        self.assertEqual(95,len(manifest['vanillaContainerSources']))
        self.assertTrue(all('sha256' in r for r in manifest['bossSources'].values()))
    def test_opens_from_anywhere_without_starting_or_mutating_quest_route(self):
        c=self.client(); before=c.ns.routeSelection
        c.ns.ShowDungeonViewer('ragefire-chasm');f=c.ns.dungeonViewer
        self.assertTrue(f.IsShown(f));self.assertEqual('Ragefire Chasm',f.title.text)
        self.assertEqual(4,len(f.data.bosses));self.assertEqual(before,c.ns.routeSelection)
        next(row for row in f.bossRows.values() if row.boss and row.boss.id == 11520).OnClick()
        self.assertTrue(f.lootRows[1].item)
    def test_boss_click_switches_loot_and_quest_list_is_separate(self):
        c=self.client();c.ns.ShowDungeonViewer('ragefire-chasm');f=c.ns.dungeonViewer
        first=f.bossID;f.bossRows[2].OnClick()
        self.assertNotEqual(first,f.bossID);self.assertEqual(f.bossRows[2].boss.name,f.bossName.text)
        f.questList.OnClick();self.assertTrue(c.ns.dungeonWindow)
    def test_client_floors_portraits_and_matching_boss_positions_take_precedence(self):
        c=self.client(True);c.ns.ShowDungeonViewer('ragefire-chasm');f=c.ns.dungeonViewer
        self.assertEqual(2,len(f.data.maps));self.assertEqual(400,f.data.maps[1].mapID)
        self.assertFalse(f.data.maps[1].reference);self.assertEqual('Main floor',f.floorMenu.caption.text)
        self.assertEqual(1,len(f.data.maps[1].bosses))
        self.assertEqual(11520,f.pins[1].bossID)
        f.pins[1].OnClick();self.assertEqual('Taragaman the Hungerer',f.bossName.text)
        self.assertEqual(222,f.portrait.texture)
        f.floorMenu.options[2].OnClick();self.assertEqual(2,f.floor)
    def test_late_journal_availability_upgrades_an_already_open_viewer(self):
        c=self.client();c.ns.ShowDungeonViewer('ragefire-chasm');f=c.ns.dungeonViewer
        self.assertTrue(f.data.maps[1].reference)
        c.lua.execute(NATIVE);c.ns.RefreshDungeonArtwork()
        self.assertEqual(400,f.data.maps[1].mapID)
        self.assertEqual(11520,f.pins[1].bossID)

    def test_compact_map_resizes_and_boss_click_opens_full_loot_view(self):
        c=self.client(True);c.ns.ShowDungeonViewer('ragefire-chasm');f=c.ns.dungeonViewer
        f.mode.OnClick();self.assertTrue(f.compact);self.assertFalse(f.bossPanel.IsShown(f.bossPanel))
        f.SetSize(f,420,310);f.OnSizeChanged()
        self.assertEqual(396,f.map.width);self.assertGreater(f.map.height,0)
        f.pins[1].OnClick();self.assertFalse(f.compact);self.assertEqual('Taragaman the Hungerer',f.bossName.text)
    def test_combat_does_not_hide_map_and_resize_remains_available(self):
        c=self.client(True);c.ns.ShowDungeonViewer('ragefire-chasm');f=c.ns.dungeonViewer
        c.lua.globals().combat=True;f.mode.OnClick();f.SetSize(f,460,330);f.OnSizeChanged()
        self.assertTrue(f.IsShown(f));self.assertTrue(f.tiles[1].IsShown(f.tiles[1]))
        c.ns.handlers.PLAYER_REGEN_ENABLED();self.assertTrue(f.IsShown(f))
    def test_missing_tile_hides_entire_map_and_keeps_boss_loot(self):
        c=self.client();c.ns.ShowDungeonViewer('ragefire-chasm');f=c.ns.dungeonViewer
        c.lua.execute("getmetatable(CreateFrame('Frame')).__index.SetTexture=function(self,asset) if type(asset)=='string' and asset:find('WorldMap') then return false end; self.texture=asset; return true end")
        next(row for row in f.bossRows.values() if row.boss and row.boss.id == 11520).OnClick()
        c.ns.RenderDungeonViewer();self.assertTrue(f.empty.IsShown(f.empty));self.assertFalse(f.tiles[1].IsShown(f.tiles[1]));self.assertTrue(f.lootRows[1].item)
    def test_private_bad_map_data_and_portraits_fall_back(self):
        c=self.client(True)
        c.lua.execute("C_Map.GetMapArtLayers=function() return {{layerWidth=secret,layerHeight=668,tileWidth=256,tileHeight=256}} end; EJ_GetCreatureInfo=function() return nil,nil,nil,nil,secret end")
        c.ns.ShowDungeonViewer('ragefire-chasm');f=c.ns.dungeonViewer
        self.assertTrue(f.data.maps[1].reference);self.assertNotEqual(222,f.portrait.texture)
    def test_loot_search_and_category_are_literal_and_paginated(self):
        c=self.client();boss=c.ns.dungeonJournalData.dungeons['ragefire-chasm'].bosses[1]
        result=c.ns.DungeonViewerLoot(boss,'[','all');self.assertEqual(0,len(result))
        equipment=c.ns.DungeonViewerLoot(boss,'','equipment')
        self.assertTrue(all(i.classID in (2,4) for i in equipment.values()))
        c.ns.ShowDungeonViewer('blackrock-depths');f=c.ns.dungeonViewer
        f.search.SetText(f.search,'not-a-real-item');f.search.OnTextChanged(f.search)
        self.assertTrue(f.lootEmpty.IsShown(f.lootEmpty))
    def test_item_cache_is_requested_once_and_event_refreshes_public_tooltip(self):
        c=self.client();c.lua.execute('itemRequests={}; C_Item={GetItemInfo=function() end,RequestLoadItemDataByID=function(id) itemRequests[id]=(itemRequests[id] or 0)+1 end}')
        c.ns.ShowDungeonViewer('ragefire-chasm');f=c.ns.dungeonViewer;item=f.lootRows[1].item.id
        c.ns.RenderDungeonViewer();self.assertEqual(1,c.lua.globals().itemRequests[item])
        c.lua.execute('C_Item.GetItemInfo=function(id) return "Cached item", "|cffffffff|Hitem:"..id..":0|h[Cached item]|h|r",3,18,13,nil,nil,nil,nil,1234 end')
        c.ns.handlers.ITEM_DATA_LOAD_RESULT(item,True)
        self.assertEqual('Cached item',f.lootRows[1].item.name);self.assertEqual(1234,f.lootRows[1].icon.texture)
        c.lua.execute('C_Item.GetItemInfo=function(id) return secret,secret,secret,nil,secret,nil,nil,nil,nil,secret end')
        c.ns.handlers.ITEM_DATA_LOAD_RESULT(item,True);self.assertNotEqual('Cached item',f.lootRows[1].item.name)
    def test_unknown_new_dungeon_stays_browsable_with_honest_empty_state(self):
        c=self.client();c.ns.ShowDungeonViewer('blackmaw-hold');f=c.ns.dungeonViewer
        self.assertTrue(f.IsShown(f));self.assertEqual(0,len(f.data.bosses));self.assertEqual(0,len(f.data.maps));self.assertTrue(f.empty.IsShown(f.empty));self.assertTrue(f.lootEmpty.IsShown(f.lootEmpty))
    def test_new_dungeon_can_use_native_encounters_without_inventing_loot(self):
        c=self.client(True)
        c.lua.execute("EJ_GetInstanceByIndex=function(i) if i==1 then return 200,'Blackmaw Hold',nil,nil,1 end end; EJ_GetInstanceInfo=function() return 'Blackmaw Hold',nil,nil,nil,nil,nil,400 end; EJ_GetEncounterInfoByIndex=function(i) if i==1 then return 'Native beta boss',nil,123 end end")
        c.ns.RefreshDungeonArtwork();c.ns.ShowDungeonViewer('blackmaw-hold');f=c.ns.dungeonViewer
        self.assertEqual('Native beta boss',f.data.bosses[1].name);self.assertTrue(f.data.bosses[1].native);self.assertEqual(0,len(f.data.bosses[1].loot))
    def test_map_size_position_and_background_are_shared_and_persisted(self):
        c=self.client();c.ns.ShowDungeonViewer('ragefire-chasm',True);f=c.ns.dungeonViewer
        f.SetSize(f,460,340);f.OnSizeChanged()
        c.lua.globals().testViewer=f
        c.lua.execute('testViewer.GetLeft=function()return 137 end;testViewer.GetTop=function()return 782 end')
        f.grip.OnMouseUp();f.background.OnClick()
        c.ns.ShowDungeonViewer('wailing-caverns',True)
        self.assertEqual((460,340),(f.width,f.height))
        state=c.ns.db.dungeonViewerUI
        self.assertEqual(137,state.left);self.assertEqual(782,state.top);self.assertTrue(state.transparent)
        saved={'dungeonViewerUI':{'compactSize':[460,340],'fullSize':[1000,600],'left':137,'top':782,'transparent':True}}
        second=Client(use_catalogue=True,default_guide=True,saved_variables=saved)
        second.ns.ShowDungeonViewer('shadowfang-keep',True);new=second.ns.dungeonViewer
        self.assertEqual((460,340),(new.width,new.height));self.assertTrue(new.transparent)
        self.assertEqual('TOPLEFT',new.point[1]);self.assertEqual(137,new.point[4]);self.assertEqual(782,new.point[5])
        second.ns.ShowDungeonViewer('ragefire-chasm');self.assertEqual((1000,600),(new.width,new.height))
        self.assertFalse(new.compact)

    def test_entry_prompt_once_per_entry_and_option_does_not_disable_manual_view(self):
        c=self.client();c.lua.execute("inDungeon=true; function IsInInstance() return inDungeon,'party' end; function GetInstanceInfo() return 'Ragefire Chasm','party',1,nil,nil,nil,nil,389 end")
        c.ns.CheckDungeonViewerEntry();p=c.ns.dungeonEntryPrompt
        self.assertEqual('Open map?',p.title.text);p.later.OnClick();c.ns.CheckDungeonViewerEntry();self.assertFalse(p.IsShown(p))
        c.lua.globals().inDungeon=False;c.ns.CheckDungeonViewerEntry();c.lua.globals().inDungeon=True;c.ns.CheckDungeonViewerEntry();self.assertTrue(p.IsShown(p))
        p.open.OnClick();self.assertTrue(c.ns.dungeonViewer.IsShown(c.ns.dungeonViewer));self.assertTrue(c.ns.dungeonViewer.compact)
        c.ns.db.config.dungeonMapPrompt=False;c.lua.globals().inDungeon=False;c.ns.CheckDungeonViewerEntry();c.lua.globals().inDungeon=True;c.ns.CheckDungeonViewerEntry();self.assertFalse(p.IsShown(p))
        c.ns.ShowDungeonViewer('wailing-caverns');self.assertEqual('Wailing Caverns',c.ns.dungeonViewer.title.text);self.assertFalse(c.ns.dungeonViewer.compact)
    def test_entry_waits_for_combat_and_ignores_raid_or_private_instance(self):
        c=self.client();c.lua.execute("combat=true;function InCombatLockdown() return combat end; function IsInInstance() return true,'party' end; function GetInstanceInfo() return 'Ragefire Chasm','party',1,nil,nil,nil,nil,389 end")
        c.ns.CheckDungeonViewerEntry();self.assertIsNone(c.ns.dungeonEntryPrompt)
        c.lua.globals().combat=False;c.ns.handlers.PLAYER_REGEN_ENABLED();self.assertTrue(c.ns.dungeonEntryPrompt.IsShown(c.ns.dungeonEntryPrompt))
        c.lua.execute("IsInInstance=function() return true,'raid' end");c.ns.CheckDungeonViewerEntry();self.assertFalse(c.ns.dungeonEntryPrompt.IsShown(c.ns.dungeonEntryPrompt))
        c.lua.execute("IsInInstance=function() return true,'party' end;GetInstanceInfo=function()return secret,secret end");c.ns.CheckDungeonViewerEntry();self.assertFalse(c.ns.dungeonEntryPrompt.IsShown(c.ns.dungeonEntryPrompt))
    def test_dungeon_buttons_pool_correctly_and_no_route_is_started_by_card_click(self):
        c=self.client();c.ns.SetFilter('dungeons');card=c.ns.ui.cards[1]
        self.assertIsNone(card.dungeonButton);self.assertFalse(card.detailsButton.IsShown(card.detailsButton));self.assertFalse(card.mapButton.IsShown(card.mapButton))
        before=c.ns.routeSelection;card.OnClick();self.assertEqual(before,c.ns.routeSelection);self.assertTrue(c.ns.dungeonViewer)
        c.ns.SetFilter('library');self.assertIsNone(card.dungeonButton);self.assertEqual('BOTTOMLEFT',card.detailsButton.point[1]);self.assertEqual(c.ns.ui.contentWidth,card.width)

if __name__=='__main__':unittest.main()
