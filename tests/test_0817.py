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
    c.lua.execute("function UnitRace() return 'Orc','Orc',2 end; function UnitFactionGroup() return 'Horde','Horde' end")
    c.ns.ReadProfile()
    c.ns.profile.classID, c.ns.profile.raceID = 1, 2
    c.ns.db.config.soloMode = True
    return c


def groups(c):
    return {g.key: g for g in c.ns.DungeonGroups().values()}


def wow_bit(c):
    c.lua.execute('''bit={
      lshift=function(a,b) return a*2^b end,
      band=function(a,b)
        local out,p=0,1; a=a%4294967296; b=b%4294967296
        while a>0 and b>0 do
          if a%2==1 and b%2==1 then out=out+p end
          a=math.floor(a/2); b=math.floor(b/2); p=p*2
        end
        return out
      end
    }''')


class DungeonDataTests(unittest.TestCase):
    def test_lordaeron_item_started_quests_are_dungeon_run_goals_not_blocking_preparation(self):
        c = shipped(20)
        group = groups(c)['ruins-of-lordaeron']
        guide = c.ns.DungeonGuide(group)
        self.assertTrue(guide.collectionDeferred[95204])
        self.assertTrue(guide.collectionDeferred[97288])
        self.assertTrue(guide.collectionDeferred[97289])

        route = c.ns.BuildDungeonRoute(guide, False, False)
        self.assertEqual(route.missing, 0)
        self.assertTrue(route.stops[len(route.stops)].dungeonEntrance)
        self.assertTrue(route.pendingReason)
        self.assertIn('Abominable Head', route.pendingReason)
        self.assertIn('The Baron', route.pendingReason)
        self.assertIn('picked up during the dungeon run', route.pendingReason)

    def test_unmapped_general_quest_start_names_the_item_source_without_inventing_a_route_point(self):
        c = shipped(20)
        reason = c.ns.QuestStartGapReason(97288)
        self.assertIn('Unending Torment', reason)
        self.assertIn('Abominable Head', reason)
        self.assertIn('The Baron', reason)
        self.assertIn('not mapped yet', reason)

    def test_every_available_dungeon_route_keeps_its_entrance_reachable_when_quest_steps_are_missing(self):
        built, entrances = 0, 0
        for faction, race in (('Horde', 2), ('Alliance', 1)):
            c = shipped(60)
            c.ns.profile.faction, c.ns.profile.raceID = faction, race
            for group in groups(c).values():
                guide = c.ns.DungeonGuide(group)
                if not guide:
                    continue
                built += 1
                self.assertTrue(all(guide.collectionInDungeon[record.id] is not None
                                    for record in guide.records.values()),
                                (faction, group.key, 'missing in-dungeon classification'))
                route = c.ns.BuildDungeonRoute(guide, False, False)
                if route.missing:
                    self.assertTrue(route.pendingReason, (faction, group.key, route.missing))
                if c.ns.DungeonEntrance(group):
                    last = route.stops[len(route.stops)] if len(route.stops) else None
                    if not route.entranceBlocked and route.limited == 0:
                        entrances += 1
                        self.assertTrue(last and last.dungeonEntrance,
                                        (faction, group.key, route.missing, route.limited, route.pendingReason))
                    else:
                        self.assertFalse(any(stop.dungeonEntrance and stop.dungeonKey == group.key
                                             for stop in route.stops.values()),
                                         (faction, group.key, route.entranceBlocked, route.limited))
                positions = {}
                for index, stop in enumerate(route.stops.values(), 1):
                    positions.setdefault(stop.id, {})[stop.kind] = index
                for child, parents in guide.collectionDependencies.items():
                    if guide.collectionDeferred[child]:
                        continue
                    pickup = positions.get(child, {}).get('a')
                    for parent in parents.values():
                        turn_in = positions.get(parent, {}).get('t')
                        if pickup and turn_in:
                            self.assertLess(turn_in, pickup, (faction, group.key, parent, child))
        self.assertEqual(built, 41)
        self.assertGreater(entrances, 10)

    def test_wow_identity_bit_masks_allow_all_41_faction_dungeon_routes_to_finish(self):
        built = 0
        for faction, race in (('Horde', 2), ('Alliance', 1)):
            c = shipped(60)
            wow_bit(c)
            c.ns.profile.faction, c.ns.profile.raceID = faction, race
            for group in groups(c).values():
                guide = c.ns.DungeonGuide(group)
                if not guide:
                    continue
                built += 1
                route = c.ns.BuildDungeonRoute(guide, False, False)
                self.assertFalse(route.entranceBlocked, (faction, group.key, route.pendingReason))
                self.assertEqual(route.limited, 0, (faction, group.key, route.pendingReason))
                if c.ns.DungeonEntrance(group):
                    last = route.stops[len(route.stops)] if len(route.stops) else None
                    self.assertTrue(last and last.dungeonEntrance,
                                    (faction, group.key, route.pendingReason))
        self.assertEqual(built, 41)

    def test_cross_dungeon_prerequisite_routes_its_instance_before_the_goal_dungeon(self):
        c = shipped(60)
        guide = c.ns.DungeonGuide(groups(c)['scarlet-monastery'])
        self.assertEqual(list(guide.collectionDependencies[1113].values()), [1109])

        route = c.ns.BuildDungeonRoute(guide, False, False)
        steps = list(route.stops.values())
        prerequisite_entry = next(i for i, stop in enumerate(steps)
                                  if stop.dungeonEntrance and stop.dungeonKey == 'razorfen-kraul')
        goal_entry = next(i for i, stop in enumerate(steps)
                          if stop.dungeonEntrance and stop.dungeonKey == 'scarlet-monastery')
        pickup = next(i for i, stop in enumerate(steps) if stop.id == 1109 and stop.kind == 'a')
        turn_in = next(i for i, stop in enumerate(steps) if stop.id == 1109 and stop.kind == 't')
        child_pickup = next(i for i, stop in enumerate(steps) if stop.id == 1113 and stop.kind == 'a')
        self.assertLess(pickup, prerequisite_entry)
        self.assertLess(prerequisite_entry, turn_in)
        self.assertLess(turn_in, child_pickup)
        self.assertLess(child_pickup, goal_entry)
        self.assertFalse(route.entranceBlocked)

    def test_stockade_chain_routes_the_unsent_letter_item_drop_to_the_deadmines(self):
        c = shipped(30)
        c.ns.profile.faction, c.ns.profile.raceID = 'Alliance', 1
        guide = c.ns.DungeonGuide(groups(c)['the-stockade'])
        route = c.ns.BuildDungeonRoute(guide, False, False)
        steps = list(route.stops.values())
        item_drop = next(i for i, stop in enumerate(steps)
                         if stop.id == 373 and stop.dungeonKey == 'the-deadmines')
        item_return = next(i for i, stop in enumerate(steps) if stop.id == 373 and stop.kind == 't')
        next_pickup = next(i for i, stop in enumerate(steps) if stop.id == 389 and stop.kind == 'a')
        stockade_entry = next(i for i, stop in enumerate(steps)
                              if stop.dungeonEntrance and stop.dungeonKey == 'the-stockade')
        self.assertIn('An Unsent Letter', steps[item_drop].label)
        self.assertIn('Edwin VanCleef', steps[item_drop].label)
        self.assertLess(item_drop, item_return)
        self.assertLess(item_return, next_pickup)
        self.assertLess(next_pickup, stockade_entry)

    def test_unpinned_dungeon_prerequisite_steps_stay_in_sequence_and_do_not_block_the_goal_entrance(self):
        c = shipped(60)
        # WoW supplies bit.band/lshift; the host harness intentionally does not.
        wow_bit(c)
        guide = c.ns.DungeonGuide(groups(c)['blackrock-spire'])
        route = c.ns.BuildDungeonRoute(guide, False, False)
        steps = list(route.stops.values())
        stratholme_work = next(i for i, stop in enumerate(steps)
                               if stop.id == 8945 and stop.dungeonKey == 'stratholme')
        proof_inside = next(i for i, stop in enumerate(steps)
                            if stop.id == 8946 and stop.dungeonKey == 'stratholme')
        proof_return = next(i for i, stop in enumerate(steps) if stop.id == 8946 and stop.kind == 't')
        following_pickup = next(i for i, stop in enumerate(steps) if stop.id == 8947 and stop.kind == 'a')
        goal_entry = next(i for i, stop in enumerate(steps)
                          if stop.dungeonEntrance and stop.dungeonKey == 'blackrock-spire')
        self.assertIn('quest tracker', steps[stratholme_work].label)
        self.assertIn('quest tracker', steps[proof_inside].label)
        self.assertLess(stratholme_work, proof_inside)
        self.assertLess(proof_inside, proof_return)
        self.assertLess(proof_return, following_pickup)
        self.assertLess(following_pickup, goal_entry)
        self.assertTrue(route.partial)
        self.assertFalse(route.entranceBlocked)

    def test_entering_a_dungeon_advances_past_unmapped_prep_steps(self):
        c = shipped(20)
        group = groups(c)['ruins-of-lordaeron']
        guide = c.ns.DungeonGuide(group)
        c.lua.execute("local ns=...; ns.DungeonEntryKey=function() return '" + group.key + "' end", c.ns)
        c.ns.AdvanceDungeonGuide(guide)
        self.assertEqual(guide.dungeonPhase, 'run')

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
        self.assertEqual(count, 341)
        self.assertEqual(c.ns.catalogue.count, 5307)
        # Explicit zone identity folds this formerly separate dungeon card in.
        self.assertIn(92401, list(gs['ruins-of-lordaeron'].ids.values()))
        self.assertIn(92401, data['dungeons']['ruins-of-lordaeron']['questIDs'])
        self.assertIn(92753, list(gs['the-deadmines'].ids.values()))
        self.assertIsNotNone(c.ns.CatalogueQuest(92753))
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
