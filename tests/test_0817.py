"""Combined dungeon sources, explicit memberships and entrance navigation.

Public fact/host-state checks do not confirm live beta entrance placement.
"""
import json
from pathlib import Path
import sys
import unittest

from test_addon import Client, ROOT
from test_050 import solo, dungeon
from test_068 import maps
from test_057 import plain

sys.path.insert(0, str(ROOT / 'tools'))
from import_dungeons import overview_ranges


def shipped(level=60):
    c = Client(quests=(), use_catalogue=True)
    c.guide_environment(level=level)
    c.ns.ReadProfile()
    c.ns.profile.classID, c.ns.profile.raceID = 1, 2
    c.ns.db.config.soloMode = True
    return c


def groups(c):
    return {g.key: g for g in c.ns.DungeonGroups().values()}


class DungeonDataTests(unittest.TestCase):
    def test_all_classic_complexes_are_mapped_and_all_overview_dungeons_are_present(self):
        c = shipped()
        gs = groups(c)
        self.assertEqual(len(gs), 28)
        classic = [g for g in gs.values() if g.definition.era == 'Classic']
        self.assertEqual(len(classic), 19)
        for g in classic:
            with self.subTest(dungeon=g.key):
                self.assertGreater(len(g.ids), 0)
                self.assertTrue(c.ns.ValidTravelPoint(c.ns.DungeonEntrance(g)))
                self.assertEqual(c.ns.DungeonEntrance(g).source, 'Published Forever entrance area')
                self.assertLessEqual(g.definition.runLevelLow, g.definition.runLevelHigh)
                self.assertEqual(g.level, g.definition.runLevelLow)
        self.assertEqual(sum(bool(c.ns.DungeonEntrance(g)) for g in gs.values()), 23)
        self.assertNotIn('mage', gs)
        self.assertNotIn('orgrimmar', gs)
        self.assertNotIn('molten core', gs)
        self.assertNotIn('ruins of lordaeron', gs)

    def test_membership_matches_bounded_source_lists_without_duplicate_ids_or_lost_quest_records(self):
        c = shipped()
        gs = groups(c)
        data = json.loads((ROOT / 'WowTogether/DungeonData.json').read_text())
        count = 0
        for key, source in data['dungeons'].items():
            ids = list(gs[key].ids.values())
            self.assertEqual(len(ids), len(set(ids)))
            self.assertTrue(set(source['questIDs']).issubset(ids))
            self.assertTrue(all(c.ns.CatalogueQuest(id) is not None for id in source['questIDs']))
            count += len(source['questIDs'])
        self.assertEqual(count, 339)
        self.assertEqual(c.ns.catalogue.count, 5230)
        # Explicit zone identity folds this formerly separate dungeon card in.
        self.assertIn(92401, list(gs['ruins-of-lordaeron'].ids.values()))
        # Unresolved dungeon-tagged class/city/raid records stay in the library.
        self.assertIsNotNone(c.ns.CatalogueQuest(7487))

    def test_wing_ranges_survive_family_merge_and_unmapped_new_dungeons_stay_unknown(self):
        c = shipped()
        gs = groups(c)
        self.assertEqual(len(gs['scarlet-monastery'].definition.wings), 4)
        self.assertEqual(len(gs['maraudon'].definition.wings), 3)
        self.assertEqual(len(gs['blackrock-spire'].definition.wings), 2)
        self.assertEqual(gs['scarlet-monastery'].level, 28)
        self.assertEqual(gs['scarlet-monastery'].maxLevel, 45)
        for key in ('blackmaw-hold', 'kroldok-stronghold', 'the-drowned-city', 'alcaz-prison', 'shapers-terrace'):
            self.assertIsNone(c.ns.DungeonEntrance(gs[key]))
            self.assertIsNone(c.ns.DungeonGuide(gs[key]))
            self.assertIn('not captured', c.ns.DungeonCollectionSummary(gs[key]))
            self.assertFalse(c.ns.DungeonCollectionReadiness(gs[key]).levelReady)

    def test_levels_are_information_not_a_new_pickup_gate(self):
        c = solo()
        group = dungeon(c)
        group.definition = c.lua.table_from({'runLevelLow': 40, 'runLevelHigh': 50, 'entrances': [], 'aliases': [], 'wings': []}, recursive=True)
        result = c.ns.DungeonCollectionReadiness(group)
        self.assertTrue(result.levelReady)
        self.assertEqual(result.pickupLevel, 5)
        self.assertIn('40–50', c.ns.DungeonOverviewSummary(group))
        self.assertIsNotNone(c.ns.DungeonGuide(group))

    def test_sources_and_generator_fail_closed_for_an_incomplete_overview(self):
        data = json.loads((ROOT / 'WowTogether/DungeonData.json').read_text())
        self.assertEqual(data['overview']['url'], 'https://www.wowhead.com/forever/guide/dungeons-overview-locations-details')
        self.assertEqual(len(data['quest_categories']), 23)
        self.assertEqual(data['entrance_source']['license'], 'MIT')
        self.assertEqual(data['level_conflicts']['city-of-dalaran']['chart'], [28, 33])
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'overview.html'
            path.write_text('Dungeons Overview for Forever <script>' + json.dumps('[table][center]Ragefire Chasm (13-18)[/center][/table]') + '</script>')
            with self.assertRaises(ValueError):
                overview_ranges(path)


class EntranceIntegrationTests(unittest.TestCase):
    def test_shipped_entrances_work_without_map_link_api_and_native_aliases_take_precedence(self):
        c = shipped()
        gs = groups(c)
        c.lua.execute('C_Map.GetMapLinksForMap=nil')
        self.assertEqual(c.ns.DungeonEntrance(gs['ragefire-chasm']).mapID, 1454)
        c.lua.execute('''
          checkedMaps={}
          C_Map.GetMapLinksForMap=function(id)
            checkedMaps[id]=true
            if id==1435 then return {{name="The Temple Of Atalhakkar",position={GetXY=function() return .4,.5 end}}} end
            return {}
          end
        ''')
        entrance = c.ns.DungeonEntrance(gs['the-temple-of-atalhakkar'])
        self.assertEqual(entrance.source, 'Client map entrance link')
        self.assertEqual((entrance.mapID, entrance.x, entrance.y), (1435, .4, .5))
        self.assertTrue(c.lua.globals().checkedMaps[1435])

    def test_private_or_invalid_native_coordinates_fall_back_to_the_published_point(self):
        c = shipped()
        group = groups(c)['ragefire-chasm']
        for result in ('secret,secret', '0/0,.4', '-.1,.4', 'math.huge,.4'):
            with self.subTest(value=result):
                c.lua.execute('C_Map.GetMapLinksForMap=function() return {{name="Ragefire Chasm",position={GetXY=function() return ' + result + ' end}}} end')
                self.assertEqual(c.ns.DungeonEntrance(group).source, 'Published Forever entrance area')
        c.lua.execute('C_Map.GetMapLinksForMap=function() return {{name=secret,position=secret}} end')
        self.assertEqual(c.ns.DungeonEntrance(group).source, 'Published Forever entrance area')

    def test_personal_recording_wins_and_does_not_mutate_the_source_data(self):
        c = shipped()
        group = groups(c)['wailing-caverns']
        source = plain(group.definition.entrances[1])
        c.ns.DungeonEntrance(group).x = .99
        self.assertEqual(plain(group.definition.entrances[1]), source)
        c.ns.RecordDungeonEntrance(group)
        self.assertEqual(c.ns.DungeonEntrance(group).source, 'Player-recorded entrance')
        self.assertEqual(plain(group.definition.entrances[1]), source)
        c.ns.db.dungeonEntrances[group.key].x = float('nan')
        self.assertEqual(c.ns.DungeonEntrance(group).source, 'Published Forever entrance area')

    def test_cross_zone_entrance_is_retained_after_pickups_and_shows_travel_instructions(self):
        c = solo()
        maps(c)
        group = dungeon(c, entrance_map=502)
        plan = c.ns.DungeonGuide(group)
        route = c.ns.BuildDungeonRoute(plan, True)
        self.assertEqual(route.mapID, 501)
        self.assertEqual([s.kind for s in route.stops.values()], ['a', 'a', 'q'])
        entry = route.stops[3]
        self.assertEqual(entry.mapID, 502)
        self.assertTrue(entry.dungeonEntrance)
        self.assertEqual(c.ns.GuideStepAction(entry), 'Go to Test Cavern entrance')
        self.assertNotIn('Kill', c.ns.StopInstruction(entry))
        c.ns.ActivateRoute(plan, route)
        c.lua.execute("entries={{questID=900,title='First',isHeader=false},{questID=901,title='Second',isHeader=false}}")
        c.ns.ReadQuests()
        c.ns.UpdateSelectedRoute(c.lua.table())
        self.assertTrue(c.ns.selectedRoute.stops[1].dungeonEntrance)
        self.assertFalse(c.ns.Completed(900))

    def test_browser_opens_clean_quest_cards_without_manual_recording_button(self):
        c = shipped()
        c.ns.SetFilter('dungeons')
        card = c.ns.ui.cards[1]
        self.assertIn('Lv ', card.count.text)
        self.assertIn('quests', card.reason.text)
        self.assertFalse(card.detailsButton.IsShown(card.detailsButton))
        card.OnClick()
        c.ns.dungeonViewer.questList.OnClick()
        self.assertTrue(c.ns.dungeonWindow.IsShown(c.ns.dungeonWindow))
        self.assertIn('Dungeon levels', c.ns.dungeonWindow.subtitle.text)
        self.assertIsNone(c.ns.dungeonWindow.record)
        self.assertGreater(len(c.ns.dungeonWindow.visibleQuests), 0)


if __name__ == '__main__':
    unittest.main()
