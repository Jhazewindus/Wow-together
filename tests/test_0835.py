"""Responsive dungeon browsing and journal quest actions under Lua 5.1.

Checks use host frames; actual font wrapping and beta artwork need client tests.
"""
import math
import unittest

from test_addon import Client
from test_0811 import browser
from test_0830 import accept
from test_routes import catalogue, guide, map_canvas, quest


def dungeon_client(data=None):
    c = Client(quests=(), use_catalogue=True, default_guide=True)
    c.guide_environment(level=18)
    c.lua.globals().grouped = False
    c.ns.ReadProfile()
    if data is not None:
        for q in data.values():
            q.setdefault('categoryPath', 'dungeons/ragefire-chasm')
        catalogue(c, data)
    c.ns.SetFilter('dungeons')
    return c


class DungeonGridTests(unittest.TestCase):
    def test_two_and_three_column_geometry_at_all_supported_widths(self):
        c = dungeon_client()
        self.assertEqual(c.ns.ui.visibleCards, 28)
        for window_width, columns in ((760, 2), (860, 2), (973, 2), (974, 3), (1080, 3), (1280, 3)):
            with self.subTest(width=window_width):
                c.ns.window.SetSize(c.ns.window, window_width, 640)
                c.ns.Layout()
                content_width = window_width - 74
                tile_width = (content_width - (columns - 1) * 12) / columns
                for index in range(1, c.ns.ui.visibleCards + 1):
                    card = c.ns.ui.cards[index]
                    row, col = divmod(index - 1, columns)
                    self.assertEqual(card.point[1], 'TOPLEFT')
                    self.assertAlmostEqual(card.point[2], col * (tile_width + 12))
                    self.assertEqual(card.point[3], -row * 162)
                    self.assertAlmostEqual(card.width, tile_width)
                    self.assertEqual(card.height, 150)
                    self.assertLessEqual(card.point[2] + card.width, content_width + .001)
                    self.assertEqual(card.title.height, 38)
                    self.assertEqual(card.count.point[1], 'TOPLEFT')
                    self.assertEqual(card.reason.point[3], -96)
                    self.assertFalse(card.detailsButton.IsShown(card.detailsButton))
                    self.assertFalse(card.mapButton.IsShown(card.mapButton))
                    self.assertFalse(card.buyButton.IsShown(card.buyButton))
                    self.assertFalse(card.catchupButton.IsShown(card.catchupButton))
                    if card.dungeonArt and card.dungeonArt.shown:
                        self.assertAlmostEqual(card.dungeonArt.width, card.width - 2)
                        self.assertEqual(card.dungeonArt.height, card.height - 2)
                rows = math.ceil(c.ns.ui.visibleCards / columns)
                self.assertEqual(c.ns.ui.content.height, rows * 162 - 12)

    def test_resize_reflows_without_browser_reads_or_route_generation(self):
        c = dungeon_client()
        c.ns.window.Show(c.ns.window)
        c.ns.ui.resizing = True
        fail = c.lua.eval("function() error('Resize must only lay out existing cards') end")
        for name in ('GuideBrowserChoices', 'DungeonGroups', 'Render', 'UpdateSelectedRoute'):
            c.ns[name] = fail
        c.ns.window.SetSize(c.ns.window, 1080, 800)
        c.ns.window.OnSizeChanged()
        self.assertGreater(c.ns.ui.cards[3].point[2], 0)
        self.assertEqual(c.ns.ui.cards[4].point[3], -162)
        self.assertTrue(c.ns.ui.resizing)

    def test_click_opens_journal_and_preserves_active_guide(self):
        c = dungeon_client({900: quest('Dungeon task')})
        c.ns.ActivateRoute(guide(c))
        key = c.ns.routeSelection.key
        tile = next(card for card in c.ns.ui.cards.values()
                    if card.activity and card.activity.dungeon.key == 'ragefire-chasm')
        tile.OnClick()
        self.assertEqual(c.ns.routeSelection.key, key)
        self.assertTrue(c.ns.dungeonViewer.IsShown(c.ns.dungeonViewer))
        self.assertEqual(c.ns.dungeonViewer.title.text, 'Ragefire Chasm')
        self.assertEqual(tile.category.text, 'DUNGEON')
        self.assertIn('1 quest', tile.reason.text)
        self.assertIsNone(tile.dungeonButton)

    def test_reused_tiles_restore_wide_zone_and_library_layouts(self):
        c = browser()
        card = c.ns.ui.cards[1]
        original_height = card.height
        c.ns.SetFilter('dungeons')
        # Synthetic fixtures have one dungeon definition supplied for this view.
        c.ns.dungeonData = c.lua.table_from({'dungeons': {'test': {
            'name': 'Test Dungeon', 'aliases': [], 'areaIDs': [], 'questIDs': [],
            'runLevelLow': 12, 'runLevelHigh': 18, 'entrances': []}}}, recursive=True)
        c.ns.catalogue = c.lua.table_from({'quests': c.ns.catalogue.quests, 'count': c.ns.catalogue.count})
        c.ns.SetFilter('dungeons')
        self.assertLess(card.width, c.ns.ui.contentWidth)
        c.ns.SetFilter('library')
        self.assertEqual(card.width, c.ns.ui.contentWidth)
        self.assertEqual(card.title.height, 18)
        self.assertEqual(card.count.point[1], 'TOPRIGHT')
        self.assertEqual(card.reason.point[3], -51)
        self.assertEqual(card.detailsButton.point[1], 'BOTTOMLEFT')
        c.ns.SetFilter('guides')
        self.assertEqual(card.width, c.ns.ui.contentWidth)
        self.assertEqual(card.height, original_height)
        self.assertTrue(card.detailsButton.IsShown(card.detailsButton))
        self.assertEqual(card.mapButton.caption.text, 'Show quest list')


class JournalQuestActionsTests(unittest.TestCase):
    def test_actions_follow_current_dungeon_and_do_not_start_while_browsing(self):
        c = dungeon_client({900: quest(), 901: quest(categoryPath='dungeons/wailing-caverns')})
        c.ns.ShowDungeonViewer('ragefire-chasm')
        frame = c.ns.dungeonViewer
        self.assertTrue(frame.startRoute.IsEnabled(frame.startRoute))
        frame.questList.OnClick()
        self.assertEqual(c.ns.dungeonWindow.group.key, 'ragefire-chasm')
        self.assertIsNone(c.ns.routeSelection)
        c.ns.ShowDungeonViewer('wailing-caverns')
        frame.questList.OnClick()
        self.assertEqual(c.ns.dungeonWindow.group.key, 'wailing-caverns')
        captured = []
        c.ns.ShowDungeonQuests = lambda group, start: captured.append((group.key, start))
        frame.startRoute.OnClick()
        self.assertEqual(captured, [('wailing-caverns', True)])
        self.assertEqual(frame.startRoute.caption.text, 'Start quest route')
        self.assertEqual(frame.questList.point[2], -198)
        self.assertEqual(frame.startRoute.point[2], -20)

    def test_new_start_button_reuses_collection_and_handin_guide(self):
        c = dungeon_client({900: quest()})
        map_canvas(c)
        c.ns.ShowDungeonViewer('ragefire-chasm')
        frame = c.ns.dungeonViewer
        frame.startRoute.OnClick(); c.drain()
        self.assertEqual(c.ns.routeSelection.key, 'dungeon:ragefire-chasm')
        self.assertFalse(frame.IsShown(frame))
        self.assertEqual(c.ns.routeSelection.mode, 'dungeon')
        self.assertTrue(any(stop.kind == 'a' for stop in c.ns.selectedRoute.stops.values()))
        accept(c, 900)
        c.lua.execute('C_QuestLog.IsComplete=function(id) return id==900 end')
        c.ns.StopGuide()
        c.ns.ShowDungeonViewer('ragefire-chasm')
        frame.startRoute.OnClick(); c.drain()
        self.assertEqual(c.ns.routeSelection.dungeonPhase, 'return')
        self.assertTrue(any(stop.kind == 't' for stop in c.ns.selectedRoute.stops.values()))

    def test_start_disabled_for_empty_completed_skipped_and_wrong_faction_sets(self):
        for scenario in ('empty', 'completed', 'skipped', 'faction'):
            with self.subTest(scenario=scenario):
                c = dungeon_client({} if scenario == 'empty' else {
                    900: quest(side='Alliance' if scenario == 'faction' else 'Horde')})
                if scenario == 'completed':
                    c.lua.execute('finished[900]=true')
                if scenario == 'skipped':
                    c.ns.db.guideSkips[c.ns.self].quests[900] = True
                c.ns.ShowDungeonViewer('ragefire-chasm')
                frame = c.ns.dungeonViewer
                self.assertFalse(frame.startRoute.IsEnabled(frame.startRoute))
                self.assertTrue(frame.questList.IsEnabled(frame.questList))
                self.assertTrue(frame.IsShown(frame))

    def test_map_only_hides_actions_and_preserves_gameplay_geometry_and_combat(self):
        c = dungeon_client({900: quest()})
        c.ns.ShowDungeonViewer('ragefire-chasm')
        frame = c.ns.dungeonViewer
        self.assertTrue(frame.startRoute.IsShown(frame.startRoute))
        frame.mode.OnClick()
        self.assertFalse(frame.questList.IsShown(frame.questList))
        self.assertFalse(frame.startRoute.IsShown(frame.startRoute))
        frame.SetSize(frame, 540, 460); frame.OnSizeChanged()
        c.lua.globals().combat = True; c.ns.handlers.PLAYER_REGEN_DISABLED()
        self.assertTrue(frame.IsShown(frame))
        c.ns.ShowDungeonViewer('wailing-caverns', True)
        self.assertEqual((frame.width, frame.height), (540, 460))
        frame.mode.OnClick()
        self.assertTrue(frame.questList.IsShown(frame.questList))
        self.assertTrue(frame.startRoute.IsShown(frame.startRoute))
        self.assertFalse(frame.startRoute.IsEnabled(frame.startRoute))

    def test_quest_refresh_disables_finished_collection(self):
        c = dungeon_client({900: quest()})
        c.ns.ShowDungeonViewer('ragefire-chasm')
        frame = c.ns.dungeonViewer
        self.assertTrue(frame.startRoute.IsEnabled(frame.startRoute))
        c.lua.execute('finished[900]=true')
        c.ns.handlers.QUEST_LOG_UPDATE(); c.drain()
        self.assertFalse(frame.startRoute.IsEnabled(frame.startRoute))


if __name__ == '__main__':
    unittest.main()
