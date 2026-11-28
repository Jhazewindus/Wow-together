"""Dungeon quests respect fresh identities; explicit Start route never opens a list."""
from pathlib import Path
import sys
import unittest
import json
import copy

from test_addon import Client
from test_050 import solo, dungeon
from test_routes import catalogue, quest, map_canvas
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from build_quest_dataset import own_lua
from import_warcraftdb import apply_corrections

ROOT = Path(__file__).resolve().parents[1]


class DungeonActionTests(unittest.TestCase):
    def test_blackfathom_prerequisites_are_reviewed_and_route_is_not_blocked(self):
        dungeon_data = own_lua(ROOT / 'WowTogether' / 'DungeonData.lua', 'dungeonData')
        quest_data = own_lua(ROOT / 'WowTogether_QuestData' / 'QuestCatalogue.lua', 'catalogue')['quests']
        dungeon_quests = dungeon_data['dungeons']['blackfathom-deeps']['questIDs']
        self.assertEqual(len(dungeon_quests), 13)
        for quest_id in dungeon_quests:
            with self.subTest(quest_id=quest_id):
                self.assertTrue(quest_data[quest_id]['prerequisitesRead'])

        self.assertNotIn('previousQuest', quest_data[6563])
        self.assertEqual(quest_data[6564]['previousQuest'], 6562)
        self.assertEqual(quest_data[6565]['previousQuest'], 6564)
        for quest_id in (78916, 78917):
            record = quest_data[quest_id]
            self.assertNotIn('previousQuest', record)
            self.assertNotIn('prerequisiteAny', record)
            self.assertNotIn('prerequisiteAll', record)
            self.assertFalse(record.get('prerequisitesUnverified', False))

        for faction in ('Alliance', 'Horde'):
            c = Client(quests=(), use_catalogue=True)
            c.guide_environment(level=30)
            c.lua.execute(f"function UnitFactionGroup() return '{faction}' end")
            c.ns.ReadProfile()
            for quest_id in (78916, 78917):
                self.assertTrue(c.ns.CataloguePrerequisitesAllowed(quest_id, c.ns.profile))

            group = next(g for g in c.ns.DungeonGroups().values() if g.key == 'blackfathom-deeps')
            route = c.ns.BuildDungeonRoute(c.ns.DungeonGuide(group), False, False)
            self.assertFalse(route.entranceBlocked)
            self.assertTrue(any(stop.dungeonEntrance for stop in route.stops.values()))

    def test_current_dungeon_lists_and_reviewed_prerequisites_are_shipped(self):
        data = json.loads((ROOT / 'WowTogether' / 'DungeonData.json').read_text())
        quest_data = own_lua(ROOT / 'WowTogether_QuestData' / 'QuestCatalogue.lua', 'catalogue')['quests']
        memberships = {ident for dungeon in data['dungeons'].values() for ident in dungeon['questIDs']}
        self.assertEqual(len(memberships), 380)
        self.assertTrue(all(ident in quest_data for ident in memberships))
        for ident in (93404, 93604, 94968, 94984, 94997, 95789, 97130, 97197):
            self.assertIn(ident, memberships)
            self.assertTrue(quest_data[ident]['prerequisitesRead'])
        self.assertEqual(quest_data[2842]['previousQuest'], 2841)
        self.assertEqual(quest_data[93404]['previousQuest'], 93594)
        self.assertEqual(quest_data[94984]['previousQuest'], 94907)
        self.assertEqual(quest_data[94997]['previousQuest'], 94983)
        self.assertNotIn('previousQuest', quest_data[6563])
        self.assertNotIn('previousQuest', quest_data[2846])
        self.assertFalse(quest_data[2846].get('prerequisitesUnverified', False))
        self.assertEqual(quest_data[95682]['previousQuest'], 95663)
        self.assertFalse(quest_data[95682].get('prerequisitesUnverified', False))
        self.assertEqual(quest_data[97291]['previousQuest'], 97290)
        self.assertEqual(quest_data[97292]['previousQuest'], 97291)
        unread = {ident for ident in memberships if not quest_data[ident].get('prerequisitesRead')}
        self.assertEqual(unread, set())
        starts = quest_data[97130]['starts']
        self.assertEqual({p['entityID'] for p in starts}, {31439})
        self.assertEqual({p['mapID'] for p in starts}, {1416})
        reviewed = {6563: copy.deepcopy(quest_data[6563])}
        apply_corrections(reviewed, allow_partial_additions=True)
        apply_corrections(reviewed, allow_partial_additions=True)
        self.assertNotIn('previousQuest', reviewed[6563])
        audit = json.loads((ROOT / 'research' / 'dungeon-prerequisite-audit-2026-11-07' / 'audit.json').read_text())
        self.assertEqual(audit['scope']['deniedQuestPages'], 17)
        self.assertEqual(audit['scope']['genericCategoryPages'], [
            'alcaz-prison', 'blackmaw-hold', 'shapers-terrace'])

    def test_explicit_start_selects_mapped_dungeon_without_list_or_route_prompt(self):
        c = solo(); map_canvas(c); group = dungeon(c)
        c.ns.ShowDungeonQuests(group, True)
        c.drain()
        self.assertEqual(c.ns.routeSelection.key, 'dungeon:test-cavern')
        self.assertIsNone(c.ns.dungeonWindow)
        self.assertIsNone(c.ns.startGuidePrompt)
        self.assertGreater(len(c.ns.selectedRoute.stops), 0)

    def test_unmapped_start_keeps_dungeon_selected_without_the_old_fallback_popup(self):
        c = solo()
        catalogue(c, {900: quest('Unmapped', starts=[], ends=[], objectives=[], categoryPath='dungeons/test-cavern')})
        group = c.ns.DungeonGroups()[1]
        c.ns.ShowDungeonQuests(group, True)
        c.drain()
        self.assertEqual(c.ns.routeSelection.key, 'dungeon:test-cavern')
        self.assertIsNone(c.ns.dungeonWindow)
        self.assertFalse(c.ns.selectedRoute.complete)

    def test_dashboard_dungeon_card_opens_journal_with_direct_quest_route(self):
        c = solo()
        catalogue(c, {900: quest('Unmapped', starts=[], ends=[], objectives=[], categoryPath='dungeons/test-cavern')})
        c.ns.dungeonData=c.lua.table_from({'dungeons':{'test-cavern':{'name':'Test Cavern','aliases':[],
            'areaIDs':[],'questIDs':[900],'entrances':[],'runLevelLow':12,'runLevelHigh':18}}},recursive=True)
        c.ns.SetFilter('dungeons')
        card = c.ns.ui.cards[1]
        self.assertFalse(card.mapButton.IsShown(card.mapButton))
        card.OnClick(card)
        self.assertEqual(c.ns.instancePage.collect.caption.text,'Start quest route')
        c.ns.instancePage.collect.OnClick()
        self.assertEqual(c.ns.routeSelection.key, 'dungeon:test-cavern')
        self.assertIsNone(c.ns.dungeonWindow)


if __name__ == '__main__':
    unittest.main()
