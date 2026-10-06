"""Loot attribution, lazy item facts and actual guide cancellation in Lua 5.1."""
import json
import sys
import unittest
from pathlib import Path

from test_addon import Client, ROOT
from test_navigation import navigator
from test_074 import scanning_client

sys.path.insert(0, str(ROOT / 'tools'))
from audit_dungeon_loot import reported_tables, season_allowed
from import_vanilla_loot import LiteralReader, vanilla_rows


class LootAuditTests(unittest.TestCase):
    def test_bfd_uses_original_encounters_and_exact_ghamoora_drops(self):
        c = Client(use_catalogue=True)
        data = c.ns.DungeonViewerData('blackfathom-deeps')
        bosses = {b.id: b for b in data.bosses.values()}
        self.assertEqual(set(bosses), {4887, 4831, 4832, 6243, 12902, 12876, 4830, 4829})
        self.assertEqual({i.id for i in bosses[4887].loot.values()}, {6907, 6908, 273839})
        self.assertIn(252798, {i.id for i in bosses[4887].sharedLoot.values()})
        self.assertNotIn(209423, {i.id for i in bosses[4887].loot.values()})

    def test_recipes_and_junk_are_not_presented_as_taragamans_encounter_loot(self):
        c = Client(use_catalogue=True)
        boss = next(b for b in c.ns.DungeonViewerData('ragefire-chasm').bosses.values() if b.id == 11520)
        actual = {i.id for i in boss.loot.values()}
        self.assertTrue({14145, 14148, 14149, 14540}.issubset(actual))
        self.assertNotIn(5370, actual)
        self.assertFalse(any(i.classID == 9 for i in boss.loot.values()))
        self.assertIn(5370, {i.id for i in boss.sharedLoot.values()})

    def test_trash_sources_open_own_loot_without_changing_floor_or_boss_map(self):
        c = Client(use_catalogue=True)
        c.ns.ShowDungeonViewer('blackfathom-deeps'); f = c.ns.dungeonViewer
        before = f.floor, [p.bossID for p in f.pins.values() if p.IsShown(p)]
        row = f.trashRows[1]; self.assertTrue(row.source)
        row.OnClick()
        self.assertEqual(row.source.name, f.bossName.text)
        self.assertTrue(f.lootTitle.text.startswith('Trash loot'))
        self.assertIsNone(f.bossID)
        self.assertTrue(f.lootRows[1].item)
        self.assertEqual(before, (f.floor, [p.bossID for p in f.pins.values() if p.IsShown(p)]))

    def test_chest_rewards_are_kept_under_containers(self):
        c = Client(use_catalogue=True)
        data = c.ns.DungeonViewerData('blackrock-depths')
        chest = next(v for v in data.containers.values() if v.id == 169243)
        self.assertEqual(chest.kind, 'container')
        self.assertTrue(chest.loot)
        self.assertNotIn(chest.id, {v.id for v in data.bosses.values()})
        self.assertFalse(any(p.id == chest.id for m in data.maps.values() for p in m.bosses.values()))

    def test_new_dungeon_reported_loot_and_literal_search(self):
        c = Client(use_catalogue=True)
        data = c.ns.DungeonViewerData('the-hall-of-thanes')
        self.assertEqual(len(data.bosses), 4)
        boss = next(v for v in data.bosses.values() if v.id == 261306)
        self.assertTrue(boss.reported)
        self.assertEqual({i.id for i in boss.loot.values()}, {270227, 271096, 271097})
        self.assertEqual(c.ns.DungeonViewerLoot(boss, 'choker', 'all', 0)[1].id, 270227)
        for key in ('ruins-of-lordaeron', 'excavation-site-wetlands'):
            self.assertGreater(len(c.ns.DungeonViewerData(key).bosses), 0)

    def test_opening_metadata_does_not_decode_every_item_and_item_facts_are_shared(self):
        c = Client(use_catalogue=True)
        data = c.ns.DungeonViewerData('blackfathom-deeps')
        stat = lambda: next(row for row in c.ns.PackedDataStats().values() if row.name == 'dungeon-loot-items')
        self.assertEqual(stat().loadedRows, 0)
        boss = next(v for v in data.bosses.values() if v.id == 4887)
        boss.loot
        self.assertEqual(stat().loadedRows, 3)
        self.assertLess(stat().loadedRows, stat().totalRows)
        item = boss.loot[1]
        self.assertTrue(c.lua.eval('rawequal')(item, c.ns.dungeonJournalData['items'][item.id]))

    def test_every_bundled_relationship_resolves_and_vanilla_coverage_is_complete(self):
        c = Client(use_catalogue=True)
        for key, stored in c.ns.dungeonJournalData.dungeons.items():
            for field in ('bosses', 'trash', 'containers'):
                for source in stored[field].values():
                    for name in ('dropIDs', 'sharedDropIDs'):
                        ids = source[name]
                        if ids:
                            for ident in ids.values():
                                self.assertTrue(c.ns.dungeonJournalData['items'][ident].name)
        manifest = json.loads((ROOT / 'WowTogether/DungeonJournalData.json').read_text())
        self.assertEqual(manifest['counts']['vanillaNPCTables'], 933)
        self.assertEqual(manifest['counts']['vanillaContainerTables'], 95)
        for coverage in manifest['coverage'].values():
            self.assertEqual(coverage['vanillaNPCs'], coverage['vanillaNPCTablesCaptured'])
        self.assertGreater(manifest['counts']['seasonOnlyRowsExcluded'], 10000)

    def test_literal_vanilla_parser_handles_escapes_and_rejects_executable_values(self):
        page = r"new Listview({template:'item',id:'drop',data:[{id:6908,name:'5Ghamoo-ra\'s Bind',classs:4,percent:60}]});"
        row = vanilla_rows(page)[0]
        self.assertEqual(row['name'], "Ghamoo-ra's Bind")
        self.assertEqual(row['quality'], 2)
        for literal in ('{x:fetchSecrets()}', '[os.execute()]', '{x:1+2}', '{x:function(){}}'):
            with self.assertRaises(ValueError):
                LiteralReader(literal).value()

    def test_season_only_relationships_do_not_pass_a_forever_url_check(self):
        self.assertFalse(season_allowed({'itemSeasonPhaseData': {'2': {'1': {}}}}))
        self.assertTrue(season_allowed({'itemSeasonPhaseData': {'0': {'0': {}}, '2': {'1': {}}}}))

    def test_reports_require_an_explicit_encounter_table_not_arbitrary_links(self):
        text = '[table][tr][td][b]Encounter[/b][/td][td][b]Current known drops[/b][/td][/tr][tr][td][npc=1][/td][td][item=2][/td][/tr][/table]'
        page = 'var lv_comments0 = ' + json.dumps([{'id': 30, 'body': text}, {'id': 31, 'body': '[npc=4] drops [item=5]'}])
        report = reported_tables(page)
        self.assertEqual(len(report), 1)
        self.assertEqual(report[0]['commentID'], 30)
        self.assertEqual(report[0]['encounters'][0], (1, [2], False))


class StopGuideTests(unittest.TestCase):
    def test_stop_keeps_empty_window_and_preserves_skip_preferences(self):
        c, _ = scanning_client(); frame = c.ns.navigation
        c.ns.db.guideSkips[c.ns.self] = c.lua.table_from({'quests': {900: True}, 'steps': {}}, recursive=True)
        c.ns.SaveSelectedGuide()
        frame.stop.OnClick()
        self.assertTrue(frame.IsShown(frame))
        self.assertEqual(frame.title.text, 'No guide selected')
        self.assertIsNone(c.ns.routeSelection); self.assertIsNone(c.ns.selectedRoute)
        self.assertIsNone(c.ns.db.guideState[c.ns.self])
        self.assertTrue(c.ns.db.guideSkips[c.ns.self].quests[900])
        self.assertFalse(frame.scan.enabled); self.assertFalse(frame.back.enabled)
        c.drain(); c.ns.Refresh(True)
        self.assertIsNone(c.ns.routeSelection)

    def test_stopping_a_pending_scan_prevents_timer_resurrection(self):
        c, _ = scanning_client()
        c.ns.ScanGuideProgress(); self.assertTrue(c.ns.guideScanning)
        c.ns.StopGuide(True); c.drain()
        self.assertIsNone(c.ns.guideScanning); self.assertIsNone(c.ns.routeSelection)
        self.assertFalse(c.ns.navigation.IsShown(c.ns.navigation))

    def test_stopping_route_planning_cancels_the_job_and_saved_restore(self):
        c, _ = scanning_client(); guide = c.ns.routeSelection
        c.ns.PlanLevelingGuide(guide, False); self.assertTrue(c.ns.routePlanning)
        c.ns.pendingSavedGuide = c.lua.table()
        c.ns.StopGuide(False); c.drain(); c.ns.RestoreSavedGuide()
        self.assertIsNone(c.ns.routePlanning); self.assertIsNone(c.ns.pendingSavedGuide)
        self.assertIsNone(c.ns.routeSelection)
        self.assertTrue(c.ns.navigation.IsShown(c.ns.navigation))

    def test_combat_stop_clears_pending_start_and_regen_does_not_revive_it(self):
        c = navigator(); guide = c.ns.routeSelection
        c.lua.execute('function InCombatLockdown() return true end')
        c.ns.pendingGuideMap, c.ns.pendingPartyRouteStart = guide, guide
        invite = c.lua.table_from({'sender': 'Tester'})
        c.ns.pendingPartyRouteFollow, c.ns.pendingPartyRouteInvite, c.ns.waitingPartyRoute = invite, invite, invite
        c.lua.execute('stoppedFollowCalls=0')
        c.lua.globals().stoppedNS = c.ns
        c.lua.execute('stoppedNS.FollowPartyRoute=function() stoppedFollowCalls=stoppedFollowCalls+1 end')
        c.ns.StopGuide(False)
        self.assertIsNone(c.ns.routeSelection); self.assertIsNone(c.ns.selectedRoute)
        self.assertIsNone(c.ns.pendingPartyRouteFollow); self.assertIsNone(c.ns.pendingPartyRouteInvite)
        self.assertIsNone(c.ns.waitingPartyRoute)
        c.lua.execute('function InCombatLockdown() return false end')
        c.ns.handlers.PLAYER_REGEN_ENABLED(); c.drain()
        self.assertEqual(c.lua.globals().stoppedFollowCalls, 0)
        self.assertIsNone(c.ns.routeSelection); self.assertIsNone(c.ns.pendingPartyRouteStart)
        self.assertTrue(c.ns.navigation.IsShown(c.ns.navigation))

    def test_bg_only_changes_opacity_and_exit_also_stops_standalone_arrow(self):
        c = navigator(); frame = c.ns.navigation
        before = c.ns.routeSelection.key
        opaque = c.ns.Option('guideOpaque')
        frame.background.OnClick()
        self.assertNotEqual(c.ns.Option('guideOpaque'), opaque)
        self.assertEqual(c.ns.routeSelection.key, before)
        c.ns.SetOption('standaloneArrow', True)
        frame.close.OnClick()
        self.assertIsNone(c.ns.routeSelection)
        self.assertFalse(frame.IsShown(frame))
        self.assertFalse(c.ns.standaloneNavigation.IsShown(c.ns.standaloneNavigation))


if __name__ == '__main__':
    unittest.main()
