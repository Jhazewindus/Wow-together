"""Dungeon portrait/quest markers, exact-floor geometry, and level sentinels."""
import json
import sys
import unittest
from pathlib import Path

from test_addon import Client, ROOT
from test_0824 import NATIVE


class DungeonMarkerTests(unittest.TestCase):
    def client(self, native=False):
        return Client(use_catalogue=True, default_guide=True, before_load=NATIVE if native else None)

    def test_all_definitions_have_position_records_and_classic_floors_are_attributed(self):
        c = self.client()
        source = json.loads((ROOT / 'WowTogether/DungeonMapData.json').read_text())
        self.assertEqual(set(c.ns.dungeonData.dungeons.keys()), set(c.ns.dungeonMapData.dungeons.keys()))
        self.assertEqual(19, source['counts']['referenceDungeons'])
        self.assertEqual(158, source['counts']['mappedBosses'])
        self.assertTrue(all(len(s['sha256']) == 64 for s in source['sources']))
        for key, record in c.ns.dungeonMapData.dungeons.items():
            for floor in record.floors.values():
                self.assertEqual(12, len(floor.tiles))
                for point in list(floor.bosses.values()) + list(floor.quests.values()):
                    self.assertTrue(0 <= point.x <= 1 and 0 <= point.y <= 1)
            if len(record.floors):
                self.assertGreater(source['coverage'][key]['mappedBosses'], 0, key)

    def test_static_portrait_click_from_compact_map_opens_correct_boss_loot(self):
        c = self.client(); before = c.ns.routeSelection
        c.ns.ShowDungeonViewer('ragefire-chasm', True); f = c.ns.dungeonViewer
        self.assertEqual(4, len(f.pins)); self.assertTrue(f.compact)
        pin = next(p for p in f.pins.values() if p.bossID == 11520)
        self.assertTrue(pin.icon.texture.lower().startswith('interface\\encounterjournal\\'))
        self.assertFalse(pin.caption.IsShown(pin.caption))
        pin.OnClick()
        self.assertFalse(f.compact); self.assertEqual('Taragaman the Hungerer', f.bossName.text)
        self.assertTrue(f.lootRows[1].item); self.assertEqual(before, c.ns.routeSelection)

    def test_multi_floor_boss_selection_switches_to_its_actual_reference_floor(self):
        c = self.client(); c.ns.ShowDungeonViewer('maraudon'); f = c.ns.dungeonViewer
        row = next(r for r in f.bossRows.values() if r.boss and r.boss.name == 'Lord Vyletongue')
        row.OnClick(); self.assertEqual(1, f.floor)
        while not any(r.boss and r.boss.name == 'Princess Theradras' for r in f.bossRows.values()):
            self.assertTrue(f.bossPages.next.enabled)
            f.bossPages.next.OnClick()
        # Selecting a known boss on the other floor follows the source floor,
        # even when the currently displayed map was selected manually.
        row = next(r for r in f.bossRows.values() if r.boss and r.boss.name == 'Princess Theradras')
        row.OnClick(); self.assertEqual(2, f.floor)

    def test_city_quest_givers_are_not_drawn_inside_the_dungeon(self):
        c = self.client(); c.ns.ShowDungeonViewer('ragefire-chasm'); f = c.ns.dungeonViewer
        ids = {p.entityID for p in f.data.maps[1].quests.values()}
        self.assertIn(11834, ids); self.assertNotIn(11833, ids); self.assertNotIn(3216, ids)
        maur = next(p for p in f.questPins.values() if p.group.entityID == 11834)
        phases = {(q.id, q.kind) for q in maur.group.quests.values()}
        self.assertIn((5722, 't'), phases); self.assertIn((5724, 'a'), phases)
        maur.OnClick(); w = c.ns.dungeonMapQuestWindow
        self.assertEqual('Maur Grimtotem', w.title.text)
        self.assertEqual('Turn in to Maur Grimtotem', w.rows[1].action.text)

    def test_objective_marker_uses_real_item_drop_relationship(self):
        c = self.client(); c.ns.ShowDungeonViewer('ragefire-chasm'); f = c.ns.dungeonViewer
        target = next(p for p in f.questPins.values() if p.group.entityID == 11520)
        target.OnClick(); w = c.ns.dungeonMapQuestWindow
        self.assertIn('Taragaman', w.title.text)
        self.assertEqual('Slaying the Beast', w.rows[1].title.text)
        self.assertIn('Heart', w.rows[1].action.text)

    def test_native_floor_does_not_inherit_old_points_from_its_name(self):
        c = self.client(True); c.ns.ShowDungeonViewer('ragefire-chasm'); f = c.ns.dungeonViewer
        self.assertEqual(1, len(f.data.maps[1].bosses))
        self.assertEqual(1, len(f.data.maps[1].quests))
        point = f.data.maps[1].quests[1]
        self.assertEqual(5761, point.id); self.assertAlmostEqual(.4, point.x); self.assertAlmostEqual(.6, point.y)
        self.assertNotIn(11834, {p.group.entityID for p in f.questPins.values() if p.IsShown(p)})

    def test_exact_tile_identity_merges_static_facts_and_native_boss_wins(self):
        c = self.client(True); c.lua.globals().testNS = c.ns
        c.lua.execute('''
          C_Map.GetMapGroupMembersInfo=function() return {{mapID=400,name='Main floor'}} end
          C_Map.GetMapArtLayerTextures=function() return testNS.dungeonMapData.dungeons['ragefire-chasm'].floors[1].tiles end
        ''')
        c.ns.ShowDungeonViewer('ragefire-chasm'); f = c.ns.dungeonViewer
        self.assertEqual(4, len(f.data.maps[1].bosses))
        taragaman = next(p for p in f.data.maps[1].bosses.values() if p.id == 11520)
        self.assertTrue(taragaman.native); self.assertAlmostEqual(.4, taragaman.x)
        targets = [p for p in f.data.maps[1].quests.values() if p.id == 5761]
        self.assertEqual(1, len(targets)); self.assertAlmostEqual(.4, targets[0].x)

    def test_completion_faction_class_and_accepted_pickup_filter_markers(self):
        c = Client(quests=(5724,), use_catalogue=True, default_guide=True)
        c.guide_environment(level=15); c.lua.globals().testNS = c.ns
        c.lua.execute("function UnitClass() return 'Shaman','SHAMAN',7 end; function UnitRace() return 'Orc','Orc',2 end; testNS.ReadProfile()")
        c.ns.ShowDungeonViewer('ragefire-chasm'); f = c.ns.dungeonViewer
        maur = next(p for p in f.questPins.values() if p.group.entityID == 11834 and p.IsShown(p))
        self.assertNotIn((5724, 'a'), {(q.id,q.kind) for q in maur.group.quests.values()})
        c.lua.execute("finished[5722]=true; testNS.handlers.QUEST_LOG_UPDATE()")
        c.drain()
        self.assertFalse(any(p.IsShown(p) and p.group.entityID == 11834 for p in f.questPins.values()))
        point = c.lua.table_from({'id': 214, 'kind': 'q'})
        self.assertFalse(c.ns.DungeonMapQuestVisible(point))
        c.lua.execute('''
          bit={lshift=function(a,b) return a*2^b end,band=function(a,b)
            local place,result=1,0
            while a>0 and b>0 do
              if a%2==1 and b%2==1 then result=result+place end
              a,b,place=math.floor(a/2),math.floor(b/2),place*2
            end
            return result
          end}
        ''')
        c.lua.execute("testNS.catalogue.quests[214].side='Both'; testNS.catalogue.quests[214].allowedRaceIDs=nil; testNS.catalogue.quests[214].raceMask=0; testNS.catalogue.quests[214].classMask=1")
        self.assertFalse(c.ns.DungeonMapQuestVisible(point))

    def test_quest_toggle_pools_pins_and_saves_across_dungeons(self):
        c = self.client(); c.ns.ShowDungeonViewer('ragefire-chasm'); f = c.ns.dungeonViewer
        count = len(f.questPins); self.assertGreater(count, 0)
        f.questPins[1].OnClick(); self.assertTrue(c.ns.dungeonMapQuestWindow.IsShown(c.ns.dungeonMapQuestWindow))
        f.questsToggle.OnClick()
        self.assertFalse(c.ns.db.dungeonViewerUI.showQuests)
        self.assertFalse(any(p.IsShown(p) for p in f.questPins.values()))
        self.assertFalse(any(p.leader and p.leader.IsShown(p.leader) for p in f.questPins.values()))
        self.assertFalse(c.ns.dungeonMapQuestWindow.IsShown(c.ns.dungeonMapQuestWindow))
        c.ns.ShowDungeonViewer('wailing-caverns'); self.assertFalse(f.showQuests)
        c.ns.ShowDungeonViewer('ragefire-chasm'); f.questsToggle.OnClick()
        self.assertEqual(count, len(f.questPins))

    def test_decluttered_quest_icons_point_back_to_the_exact_target(self):
        c = self.client(); c.ns.ShowDungeonViewer('ragefire-chasm', True); f = c.ns.dungeonViewer
        maur = next(p for p in f.questPins.values() if p.group.entityID == 11834 and p.IsShown(p))
        self.assertTrue(maur.leader.IsShown(maur.leader))
        m = f.data.maps[1]; scale = min(f.map.width / m.width, f.map.height / m.height)
        ox, oy = (f.map.width - m.width * scale) / 2, (f.map.height - m.height * scale) / 2
        self.assertAlmostEqual(ox + maur.group.x * m.width * scale, maur.leader.startPoint[3])
        self.assertAlmostEqual(-oy - maur.group.y * m.height * scale, maur.leader.startPoint[4])
        self.assertAlmostEqual(maur.point[4], maur.leader.endPoint[3])
        maur.OnClick(); w = c.ns.dungeonMapQuestWindow
        self.assertLess(w.height, 300); self.assertFalse(w.next.IsShown(w.next))

    def test_map_failure_hides_all_portraits_and_quest_icons(self):
        c = self.client(); c.ns.ShowDungeonViewer('ragefire-chasm'); f = c.ns.dungeonViewer
        c.lua.execute("getmetatable(CreateFrame('Frame')).__index.SetTexture=function(self,asset) if type(asset)=='string' and asset:find('WorldMap') then return false end; self.texture=asset; return true end")
        c.ns.RenderDungeonViewer()
        self.assertTrue(f.empty.IsShown(f.empty))
        self.assertFalse(any(p.IsShown(p) for p in list(f.pins.values()) + list(f.questPins.values())))

    def test_small_map_quest_icons_do_not_cover_bosses_or_other_quest_icons(self):
        c = self.client(); c.ns.ShowDungeonViewer('ragefire-chasm', True); f = c.ns.dungeonViewer
        f.SetSize(f, 380, 330); f.OnSizeChanged(f, 380, 330)
        bosses = [p for p in f.pins.values() if p.IsShown(p)]
        quests = [p for p in f.questPins.values() if p.IsShown(p)]
        self.assertGreater(len(quests), 5)
        for index, pin in enumerate(quests):
            x, y = pin.point[4], pin.point[5]
            for boss in bosses:
                self.assertTrue(abs(x - boss.point[4]) >= 26 or abs(y - boss.point[5]) >= 26)
            for other in quests[:index]:
                self.assertTrue(abs(x - other.point[4]) >= 20 or abs(y - other.point[5]) >= 20)

    def test_secret_native_positions_are_not_compared_or_placed(self):
        c = self.client(True)
        c.lua.execute("C_EncounterJournal.GetEncountersOnMap=function() return {{encounterID=77,mapX=secret,mapY=.5},{encounterID=77,mapX=.5,mapY=secret}} end")
        c.ns.ShowDungeonViewer('ragefire-chasm'); f = c.ns.dungeonViewer
        self.assertEqual(0,len(f.pins)); self.assertEqual(0,len(f.questPins))

    def test_bfd_placeholder_levels_never_appear_as_real_levels(self):
        c = self.client(); c.ns.ShowDungeonViewer('blackfathom-deeps'); f = c.ns.dungeonViewer
        for boss in f.data.bosses.values():
            self.assertTrue(boss.level is None or 1 <= boss.level <= 255)
        self.assertTrue(all('9999' not in (r.detail.text or '') for r in f.bossRows.values()))
        c.ns.dungeonJournalData.dungeons['blackfathom-deeps'].bosses[1].level = 9999
        c.ns.RefreshDungeonViewer(True)
        self.assertIsNone(f.data.bosses[1].level)


if __name__ == '__main__':
    unittest.main()
