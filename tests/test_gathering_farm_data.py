"""The real gathering data reaches the farms: fishing zones carry catch rates, not just names."""
import os
import re
import unittest

from test_addon import Client
import test_leveling_path as T

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def zone_names():
    """Map IDs and zone names, read from the spawn data's own headers."""
    names, folder = {}, os.path.join(ROOT, 'WowTogether_GoldSpawnData', 'zones')
    for name in sorted(os.listdir(folder)):
        head = open(os.path.join(folder, name), encoding='utf-8').read(1500)
        found = re.search(r"farmSpawnDataByMap\[(\d+)\] = \{mapID = \d+, zoneName = '((?:[^'\\]|\\.)*)'", head)
        if found:
            names[int(found.group(1))] = found.group(2).replace("\\'", "'")
    return names


def search(long_source=False):
    c = Client(quests=(), use_catalogue=True, party_mode='never', saved_variables={'config': {'levelingPath': False}})
    c.guide_environment(level=35)
    c.lua.execute(T.SCENE, c.ns, 35, 0.3, 'Horde', 1424, 'Hillsbrad Foothills')
    c.lua.execute('local names = ...; C_Map.GetMapInfo = function(id) if names[id] then return {name = names[id], mapType = 3, parentMapID = 1} end end',
                  c.lua.table_from(zone_names()))
    c.ns.ReadProfile(); c.drain()
    load = c.lua.eval('function(source, name, addon, namespace) local chunk, problem = loadstring(source, name); '
                      'if not chunk then error(problem) end; return chunk(addon, namespace) end')
    for folder in ('WowTogether_GoldData', 'WowTogether_GatheringPositionData'):
        for line in open(os.path.join(ROOT, folder, folder + '.toc'), encoding='utf-8'):
            line = line.strip()
            if line.endswith('.lua'):
                load(open(os.path.join(ROOT, folder, line), encoding='utf-8').read(), line, folder, c.ns)
    c.lua.execute('''local ns, longSource = ...
        function debugprofilestop() return os.clock() * 1000 end
        ns.EnsureOptionalData = function() return true end
        for id, entry in pairs({[356] = {"Fishing", 160}, [186] = {"Mining", 140}, [182] = {"Herbalism", 150}}) do
            ns.gatheringData[id] = {id = id, name = entry[1], skill = entry[2], maximum = 225}
        end
        ns.ReadProfessionSkills = function() end
        if longSource then
            ns.GatheringFarmYield = function()
                return {{itemID = 6308, chance = 50, quantity = 1, source = string.rep('x', 600)}}
            end
        end
        gathered = nil
        WowTogetherModuleAPI.GatheringFarmSearch({limit = 50}, function(rows) gathered = rows end)''', c.ns, long_source)
    pump = c.lua.eval('function() local list = timers; timers = {}; for _, cb in ipairs(list) do cb() end; return #timers end')
    rounds = 0
    while c.lua.globals().gathered is None and pump() > 0 and rounds < 50000:
        rounds += 1
    return c


def rated(c, profession):
    """(zones returned, zones with at least one item that has a chance and a quantity)."""
    return tuple(c.lua.eval('''function(profession)
        local zones, good = 0, 0
        for _, row in ipairs(gathered or {}) do
            if row.profession == profession then
                for _, zone in ipairs(row.zones) do
                    zones = zones + 1
                    for _, item in ipairs(zone.loot or {}) do
                        if item.chance and item.quantity then good = good + 1; break end
                    end
                end
            end
        end
        return zones, good
    end''')(profession))


class YieldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = search()

    def test_fishing_zones_come_back_with_catch_rates(self):
        # Every fish was rejected because its source note was longer than the limit for a source note.
        zones, with_rates = rated(self.c, 'Fishing')
        self.assertGreaterEqual(zones, 8)
        self.assertGreaterEqual(with_rates, 6)

    def test_mining_and_herb_zones_come_back_with_yields_too(self):
        self.assertGreaterEqual(rated(self.c, 'Mining')[1], 3)
        self.assertGreaterEqual(rated(self.c, 'Herbalism')[1], 3)

    def test_no_yield_record_has_a_source_note_too_long_to_be_accepted(self):
        longest = self.c.lua.eval('''function(ns)
            local longest = 0
            for _, row in ipairs(gathered or {}) do
                for _, zone in ipairs(row.zones or {}) do
                    for _, item in ipairs(zone.loot or {}) do
                        if type(item.source) == "string" and #item.source > longest then longest = #item.source end
                    end
                end
            end
            return longest
        end''')(self.c.ns)
        self.assertGreater(longest, 0)
        self.assertLessEqual(longest, 480)                                          # The limit in ModuleAPI.lua's safeSource.

    def test_a_long_item_source_is_truncated_without_dropping_the_yield(self):
        c = search(long_source=True)
        result = c.lua.eval('''function()
            for _, row in ipairs(gathered or {}) do
                for _, zone in ipairs(row.zones or {}) do
                    for _, item in ipairs(zone.loot or {}) do
                        if item.itemID == 6308 and item.chance == 50 then return #item.source end
                    end
                end
            end
            return 0
        end''')()
        self.assertEqual(result, 480)


if __name__ == '__main__':
    unittest.main()


class FishingPaceTests(unittest.TestCase):
    """A fishing farm is costed at a fishing pace, and at the player's own pace once they have one."""

    def gold(self, saved=None):
        import gold_host
        c = search()
        space = gold_host.load_gold(c, saved)
        c.lua.execute('''
            local known = GetItemInfo
            function GetItemInfo(id)
                if known(id) then return known(id) end
                return "Item " .. id, "|Hitem:" .. id .. ":|h[Item " .. id .. "]|h", 1, 30, 25, "Trade Goods", "Other", 20, "", "Interface\\\\Icons\\\\INV_Misc_QuestionMark", 12
            end
            C_Item.GetItemInfo = GetItemInfo''')
        space.GoldFarms.RefreshSearches()
        pump = c.lua.eval('function() local list = timers; timers = {}; for _, cb in ipairs(list) do cb() end; return #timers end')
        rounds = 0
        while pump() > 0 and rounds < 60000:
            rounds += 1
        return c, space

    def fishing(self, space):
        result = space.GoldFarms.Suggestions(20, 'Fishing')
        rows = result[0] if isinstance(result, tuple) else result
        return list(rows.values())

    def test_fishing_is_not_costed_at_one_catch_every_two_minutes(self):
        c, space = self.gold()
        farms = self.fishing(space)
        self.assertGreaterEqual(len(farms), 5)
        for farm in farms:
            self.assertEqual((farm.pace, farm.paceAssumed, farm.paceUnit), (150, True, 'catches'))

    def test_the_players_own_fishing_pace_is_used_once_they_have_fished(self):
        # 400 catches in 3000 seconds of recorded fishing: 480 an hour (a number no assumption would give).
        saved = {'trackerHistory': [{'zone': 'Stranglethorn Vale', 'seconds': 3000, 'total': 5000, 'perHour': 6000,
                                     'kind': 'Fishing', 'harvests': 400, 'items': {6359: 400}, 'coin': 0}]}
        c, space = self.gold(saved)
        assumed_c, assumed_space = self.gold()
        own = {farm.zone: farm for farm in self.fishing(space)}
        assumed = {farm.zone: farm for farm in self.fishing(assumed_space)}
        zone = sorted(own)[0]
        self.assertEqual((own[zone].pace, own[zone].paceAssumed), (480, False))
        self.assertAlmostEqual(own[zone].estimate / assumed[zone].estimate, 480 / 150, places=3)

    def test_mining_keeps_its_slower_assumption(self):
        c, space = self.gold()
        result = space.GoldFarms.Suggestions(5, 'Mining')
        rows = list((result[0] if isinstance(result, tuple) else result).values())
        self.assertGreaterEqual(len(rows), 1)
        self.assertEqual((rows[0].pace, rows[0].paceAssumed, rows[0].paceUnit), (30, True, 'harvests'))


def loop_length(points):
    """How far it is round the points, visiting the nearest unvisited one each time. 1.0 is the width of the zone map."""
    left, total = list(points), 0.0
    first = current = left.pop(0)
    while left:
        nearest = min(left, key=lambda p: (p[0] - current[0]) ** 2 + (p[1] - current[1]) ** 2)
        total += ((nearest[0] - current[0]) ** 2 + (nearest[1] - current[1]) ** 2) ** 0.5
        left.remove(nearest); current = nearest
    return total + ((first[0] - current[0]) ** 2 + (first[1] - current[1]) ** 2) ** 0.5


class RouteTests(FishingPaceTests):
    """Known pool and node positions make a loop today; the player's own finds replace them later."""

    def farm_in(self, space, kind, zone):
        result = space.GoldFarms.Suggestions(40, kind)
        rows = list((result[0] if isinstance(result, tuple) else result).values())
        return next((row for row in rows if row.zone == zone), None)

    def test_a_fishing_zone_with_known_pools_offers_a_loop(self):
        c, space = self.gold()
        farm = self.farm_in(space, 'Fishing', 'Hillsbrad Foothills')
        self.assertIsNotNone(farm)
        self.assertTrue(farm.routable)                                              # It said "zone only" before.
        self.assertTrue(farm.seededRoute)
        self.assertEqual(farm.knownSpots, 40)                                       # Every pool the data has for the zone.

    def test_start_hands_every_known_pool_to_the_route_engine_which_sizes_the_loop_to_the_respawn(self):
        c, space = self.gold()
        farm = self.farm_in(space, 'Fishing', 'Hillsbrad Foothills')
        started = space.GoldFarms.Start(farm.key)                                   # The real loop, through the real engine.
        self.assertTrue(started[0] if isinstance(started, tuple) else started)
        made = c.ns.lastModuleLoopPlan
        self.assertEqual(made.available, 40)                                        # Every known pool was offered.
        # A pool takes over a minute to fish out and about six to come back, so a handful
        # of pools fills the six minutes: the loop is a few pools, not twenty-four.
        self.assertEqual(made.respawn, 360)
        self.assertGreaterEqual(made.stops, 3)
        self.assertLess(made.stops, 12)
        self.assertGreaterEqual(made.lapSeconds, 360)                               # The first pool is back when you return.
        self.assertIsNotNone(space.GoldFarms.ActiveSession())

    def test_the_engines_loop_is_shorter_than_the_first_spots_on_the_list(self):
        c, space = self.gold()
        for zone, expected in ((1424, 40), (1434, 60)):
            pools = c.lua.eval('function(ns, id) return ns.GatheringFarmPoints("Fishing", "x", id) end')(c.ns, zone)
            every = [(p.x, p.y) for p in pools.values()]
            self.assertEqual(len(every), expected)
            result = c.ns.PlanLoop(pools)
            loop = result[0] if isinstance(result, tuple) else result
            chosen = [(p.x, p.y) for p in list(loop.points.values())[:-1]]
            self.assertEqual(len(chosen), 24)
            self.assertLess(loop_length(chosen), loop_length(every[:24]))
        # Stranglethorn's sixty pools: the loop is well under the first-24 loop.
        self.assertLess(loop_length(chosen), loop_length(every[:24]) * 0.7)

    def test_a_farm_says_how_long_its_lap_is_before_it_is_started(self):
        c, space = self.gold()
        farm = self.farm_in(space, 'Fishing', 'Hillsbrad Foothills')
        lap = space.GoldFarms.LoopPlan(farm.key)
        self.assertEqual(lap.available, 40)
        self.assertLess(lap.stops, 12)
        self.assertGreaterEqual(lap.lapSeconds, 360)
        self.assertEqual((lap.respawn, lap.respawnNote, lap.respawnLearned), (360, 'assumed', False))

    def test_mining_and_herbs_get_loops_where_positions_are_known(self):
        c, space = self.gold()
        loops = 0
        for kind in ('Mining', 'Herbalism'):
            result = space.GoldFarms.Suggestions(40, kind)
            loops += sum(1 for row in (result[0] if isinstance(result, tuple) else result).values() if row.routable)
        self.assertGreaterEqual(loops, 5)


class SessionCardTests(FishingPaceTests):
    """Starting a gathering farm really begins a session: the session card accepts it."""

    def start(self, kind, zone=None):
        c, space = self.gold()
        result = space.GoldFarms.Suggestions(40, kind)
        rows = list((result[0] if isinstance(result, tuple) else result).values())
        farm = next(row for row in rows if zone is None or row.zone == zone)
        c.lua.execute('WowTogetherModuleAPI.StartModuleLoop = function(owner, spec) if spec.onStart then spec.onStart() end; return true end')
        space.GoldFarms.Start(farm.key)
        return c, space, farm

    def test_a_fishing_farm_from_the_real_data_opens_its_session(self):
        # In play: "Gold: cannot open the session card: Invalid farm-session data."
        c, space, farm = self.start('Fishing', 'Hillsbrad Foothills')
        printed = ' '.join(str(line) for line in c.lua.globals().printed.values())
        self.assertNotIn('cannot open the session card', printed)
        active = space.GoldFarms.ActiveSession()
        self.assertIsNotNone(active)
        self.assertEqual(active.label, 'Fishing in Hillsbrad Foothills')

    def test_so_do_mining_and_herb_farms(self):
        for kind in ('Mining', 'Herbalism'):
            c, space, farm = self.start(kind)
            printed = ' '.join(str(line) for line in c.lua.globals().printed.values())
            self.assertNotIn('cannot open the session card', printed, kind)
            self.assertIsNotNone(space.GoldFarms.ActiveSession(), kind)


class RespawnLearningTests(FishingPaceTests):
    """How long a spot takes to come back starts as an assumption and is corrected by what the player finds."""

    def farm_and_stats(self, visited, hits):
        c, space = self.gold()
        result = space.GoldFarms.Suggestions(40, 'Fishing')
        farm = next(row for row in (result[0] if isinstance(result, tuple) else result).values() if row.zone == 'Hillsbrad Foothills')
        c.lua.execute('local space, key, visited, hits = ...; space.db.loopStats[key] = {visited = visited, hits = hits}',
                      space, farm.key, visited, hits)
        candidate = c.lua.eval('function(key) return {id = key, kind = "gathering", profession = "Fishing"} end')(farm.key)
        return c, space, farm, candidate

    def test_too_many_empty_stops_means_the_spots_take_longer_so_the_loop_grows(self):
        c, space, farm, candidate = self.farm_and_stats(visited=20, hits=8)          # Something at 40% of stops.
        before = space.GoldFarms.LoopPlan(farm.key).stops
        space.GoldFarms.SettleLoopStats(candidate)
        respawn, _, note, learned = space.GoldFarms.LoopTiming(candidate)
        self.assertEqual((respawn, learned), (540, True))                           # Six minutes became nine.
        self.assertEqual(note, 'from your laps: something at 40% of stops')
        c.lua.execute('local space = ...; space.GoldFarms.RefreshSearches()', space)
        pump = c.lua.eval('function() local list = timers; timers = {}; for _, cb in ipairs(list) do cb() end; return #timers end')
        rounds = 0
        while pump() > 0 and rounds < 60000:
            rounds += 1
        self.assertGreater(space.GoldFarms.LoopPlan(farm.key).stops, before)        # A longer loop next time.

    def test_nearly_every_stop_having_something_means_it_can_be_shorter(self):
        c, space, farm, candidate = self.farm_and_stats(visited=30, hits=30)
        space.GoldFarms.SettleLoopStats(candidate)
        self.assertEqual(space.GoldFarms.LoopTiming(candidate)[0], 306)             # 360 less fifteen per cent.

    def test_a_few_stops_are_not_enough_to_change_anything(self):
        c, space, farm, candidate = self.farm_and_stats(visited=12, hits=1)
        space.GoldFarms.SettleLoopStats(candidate)
        self.assertEqual(space.GoldFarms.LoopTiming(candidate)[:1] + (space.GoldFarms.LoopTiming(candidate)[2],), (360, 'assumed'))

    def test_it_never_moves_beyond_half_or_three_times_the_assumption(self):
        c, space, farm, candidate = self.farm_and_stats(visited=20, hits=0)
        for _ in range(6):
            space.GoldFarms.SettleLoopStats(candidate)
            c.lua.execute('local space, key = ...; space.db.loopStats[key].visited, space.db.loopStats[key].hits = 20, 0', space, farm.key)
        self.assertEqual(space.GoldFarms.LoopTiming(candidate)[0], 1080)            # Three times six minutes, no more.


class OwnSpotRouteTests(FishingPaceTests):
    """A zone the addon has no positions for gets a route from the places the player has fished."""

    def swamp(self, spots):
        saved = {'spots': {'Fishing': {1435: [{'x': x, 'y': y, 'n': n} for x, y, n in spots]}}}
        c, space = self.gold(saved)
        result = space.GoldFarms.Suggestions(40, 'Fishing')
        rows = list((result[0] if isinstance(result, tuple) else result).values())
        return c, space, next(row for row in rows if row.zone == 'Swamp of Sorrows')

    def test_the_addon_has_no_pool_positions_for_swamp_of_sorrows(self):
        c, space, farm = self.swamp([])
        self.assertFalse(farm.routable)
        self.assertEqual(farm.ownSpots, 0)

    def test_two_spots_are_not_a_route_yet_and_the_row_can_say_how_many(self):
        c, space, farm = self.swamp([(0.40, 0.40, 12), (0.45, 0.42, 7)])
        self.assertFalse(farm.routable)
        self.assertEqual(farm.ownSpots, 2)

    def test_three_spots_of_your_own_make_a_route(self):
        c, space, farm = self.swamp([(0.40, 0.40, 12), (0.45, 0.42, 7), (0.50, 0.38, 3)])
        self.assertTrue(farm.routable)
        self.assertEqual((farm.ownSpots, farm.seededRoute), (3, False))
        started = space.GoldFarms.Start(farm.key)
        self.assertTrue(started[0] if isinstance(started, tuple) else started)
        self.assertEqual(c.ns.lastModuleLoopPlan.available, 3)                      # The loop is those three spots.

    def test_your_own_spots_come_before_the_known_ones_where_both_exist(self):
        saved = {'spots': {'Fishing': {1424: [{'x': 0.30, 'y': 0.70, 'n': 9}]}}}
        c, space = self.gold(saved)
        result = space.GoldFarms.Suggestions(40, 'Fishing')
        farm = next(row for row in (result[0] if isinstance(result, tuple) else result).values() if row.zone == 'Hillsbrad Foothills')
        self.assertEqual((farm.ownSpots, farm.knownSpots), (1, 40))
        self.assertTrue(farm.routable)
