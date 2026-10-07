"""Dungeon quests respect fresh identities; explicit Start route never opens a list."""
import unittest

from test_addon import Client
from test_050 import solo, dungeon
from test_routes import catalogue, quest, map_canvas


class DungeonActionTests(unittest.TestCase):
    def test_list_refreshes_stale_faction_and_filters_all_incompatible_quests(self):
        c = solo()
        catalogue(c, {900: quest('Horde pickup', side='Horde', categoryPath='dungeons/test-cavern'),
                      901: quest('Alliance pickup', side='Alliance', categoryPath='dungeons/test-cavern'),
                      902: quest('Neutral pickup', side='Both', categoryPath='dungeons/test-cavern')})
        group = c.ns.DungeonGroups()[1]
        c.ns.profile.faction = 'Alliance'  # Deliberately stale cached context.
        c.ns.ShowDungeonQuestList(group)
        text = '\n'.join(r.quest.title for r in c.ns.dungeonWindow.visibleQuests.values())
        self.assertIn('Horde pickup', text)
        self.assertIn('Neutral pickup', text)
        self.assertNotIn('Alliance pickup', text)

    def test_unknown_or_secret_identity_does_not_leak_faction_quests(self):
        c = solo()
        catalogue(c, {900: quest('Horde only', side='Horde', categoryPath='dungeons/test-cavern'),
                      901: quest('Alliance only', side='Alliance', categoryPath='dungeons/test-cavern')})
        group = c.ns.DungeonGroups()[1]
        c.lua.execute('function UnitFactionGroup() return secret end')
        c.ns.ShowDungeonQuestList(group)
        self.assertNotIn('Horde only', '\n'.join(r.quest.title for r in c.ns.dungeonWindow.visibleQuests.values()))
        self.assertNotIn('Alliance only', '\n'.join(r.quest.title for r in c.ns.dungeonWindow.visibleQuests.values()))

    def test_shipped_blackfathom_list_is_faction_specific_for_both_sides(self):
        c = Client(quests=(), use_catalogue=True)
        c.guide_environment(level=25)
        c.lua.execute("function UnitRace() return 'Orc','Orc',2 end;function UnitClass() return 'Shaman','SHAMAN',7 end")
        group = next(g for g in c.ns.DungeonGroups().values() if g.key == 'blackfathom-deeps')
        c.ns.ShowDungeonQuestList(group)
        text = '\n'.join(r.quest.title for r in c.ns.dungeonWindow.visibleQuests.values())
        self.assertIn('Trouble in the Deeps', text)
        self.assertNotIn('Knowledge in the Deeps', text)
        self.assertNotIn('Twilight Falls', text)
        self.assertNotIn('Researching the Corruption', text)
        self.assertNotIn('Alliance', text)
        c.lua.execute("function UnitFactionGroup() return 'Alliance' end;function UnitRace() return 'Human','Human',1 end")
        c.ns.ShowDungeonQuestList(group)
        text = '\n'.join(r.quest.title for r in c.ns.dungeonWindow.visibleQuests.values())
        self.assertIn('Knowledge in the Deeps', text)
        self.assertNotIn('Trouble in the Deeps', text)
        self.assertNotIn('Horde', text)

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

    def test_list_start_button_closes_list_and_starts_route_directly(self):
        c = solo(); map_canvas(c); group = dungeon(c)
        c.ns.ShowDungeonQuestList(group)
        self.assertEqual(c.ns.dungeonWindow.collect.caption.text, 'Start quest route')
        c.ns.dungeonWindow.collect.OnClick(c.ns.dungeonWindow.collect)
        c.drain()
        self.assertEqual(c.ns.routeSelection.key, 'dungeon:test-cavern')
        self.assertFalse(c.ns.dungeonWindow.IsShown(c.ns.dungeonWindow))

    def test_dashboard_dungeon_card_opens_journal_with_direct_quest_route(self):
        c = solo()
        catalogue(c, {900: quest('Unmapped', starts=[], ends=[], objectives=[], categoryPath='dungeons/test-cavern')})
        c.ns.dungeonData=c.lua.table_from({'dungeons':{'test-cavern':{'name':'Test Cavern','aliases':[],
            'areaIDs':[],'questIDs':[900],'entrances':[],'runLevelLow':12,'runLevelHigh':18}}},recursive=True)
        c.ns.SetFilter('dungeons')
        card = c.ns.ui.cards[1]
        self.assertFalse(card.mapButton.IsShown(card.mapButton))
        card.OnClick(card)
        self.assertEqual(c.ns.dungeonViewer.startRoute.caption.text,'Start quest route')
        c.ns.dungeonViewer.startRoute.OnClick()
        self.assertEqual(c.ns.routeSelection.key, 'dungeon:test-cavern')
        self.assertIsNone(c.ns.dungeonWindow)


if __name__ == '__main__':
    unittest.main()
