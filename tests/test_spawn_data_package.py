"""Spawn points for every zone come from one package: one folder, one file per zone."""
import os
import unittest

from test_addon import Client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE = 'WowTogether_GoldSpawnData'


def toc_files(folder):
    lines = open(os.path.join(ROOT, folder, folder + '.toc'), encoding='utf-8').read().splitlines()
    return [line.strip().replace('\\', '/') for line in lines if line.strip().endswith('.lua')]


def client():
    """A client whose LoadAddOn runs a package's files the way the game does."""
    c = Client(quests=(), default_guide=True, party_mode='never')
    c.drain()
    sources = {}
    for folder in os.listdir(ROOT):
        toc = os.path.join(ROOT, folder, folder + '.toc')
        if folder.startswith('WowTogether_') and os.path.isfile(toc):
            sources[folder] = [open(os.path.join(ROOT, folder, name), encoding='utf-8').read() for name in toc_files(folder)]
    c.lua.execute('''
        local sources = ...
        loads = {}
        C_AddOns = C_AddOns or {}
        local function load(name)
            loads[#loads + 1] = name
            local files = sources[name]
            if not files then return false, "MISSING" end
            for _, source in ipairs(files) do
                local chunk, problem = loadstring(source, name)
                if not chunk then error(problem) end
                chunk(name, {})
            end
            return true
        end
        C_AddOns.LoadAddOn = load
        LoadAddOn = load
        function debugprofilestop() return os.clock() * 1000 end
    ''', c.lua.table_from(sources, recursive=True))
    return c


class PackageTests(unittest.TestCase):
    def test_there_is_one_spawn_data_folder_with_a_file_for_every_zone_it_lists(self):
        folders = sorted(name for name in os.listdir(ROOT) if name.startswith('WowTogether_GoldSpawnData'))
        self.assertEqual(folders, [PACKAGE])                                       # Not one folder per zone.
        listed = toc_files(PACKAGE)
        self.assertGreaterEqual(len(listed), 30)
        for name in listed:
            self.assertTrue(name.startswith('zones/'))
            self.assertTrue(os.path.isfile(os.path.join(ROOT, PACKAGE, name)), name)
        on_disk = sorted('zones/' + name for name in os.listdir(os.path.join(ROOT, PACKAGE, 'zones')))
        self.assertEqual(sorted(listed), on_disk)                                  # Nothing listed is missing; nothing present is unlisted.

    def test_asking_for_two_zones_loads_the_package_once(self):
        c = client(); g = c.lua.globals()
        self.assertTrue(c.ns.EnsureOptionalData('WowTogether_GoldSpawnData_1434'))
        self.assertTrue(c.ns.EnsureOptionalData('WowTogether_GoldSpawnData_1418'))
        self.assertEqual(list(g.loads.values()), [PACKAGE])
        self.assertEqual(c.ns.farmSpawnDataByMap[1434].zoneName, 'Stranglethorn Vale')

    def test_a_zone_that_is_not_in_the_package_is_refused_without_loading_again(self):
        c = client(); g = c.lua.globals()
        c.ns.EnsureOptionalData('WowTogether_GoldSpawnData_1434')
        self.assertFalse(c.ns.EnsureOptionalData('WowTogether_GoldSpawnData_999999'))
        self.assertFalse(c.ns.EnsureOptionalData('WowTogether_GoldSpawnData_999999'))
        self.assertEqual(list(g.loads.values()), [PACKAGE])

    def test_a_missing_package_is_tried_once_not_once_per_zone(self):
        c = client(); g = c.lua.globals()
        c.lua.execute('local load = LoadAddOn; local function gone(name) loads[#loads + 1] = name; return false, "MISSING" end; LoadAddOn = gone; C_AddOns.LoadAddOn = gone')
        self.assertFalse(c.ns.EnsureOptionalData('WowTogether_GoldSpawnData_1434'))
        self.assertFalse(c.ns.EnsureOptionalData('WowTogether_GoldSpawnData_1418'))
        self.assertEqual(list(g.loads.values()), [PACKAGE])

    def test_a_farm_gets_its_spawn_points_through_the_module_interface(self):
        c = client(); g = c.lua.globals()
        c.ns.EnsureOptionalData('WowTogether_GoldSpawnData_1434')
        # Creature 1059 is the first record in the Stranglethorn file.
        c.lua.execute('points = nil; accepted = {WowTogetherModuleAPI.FarmPriorSpawnSearch(1059, 1434, function(found) points = found end)}')
        self.assertTrue(g.accepted[1], g.accepted[2])
        c.drain()
        self.assertGreaterEqual(len(list(g.points.values())), 1)
        self.assertEqual(g.points[1].mapID, 1434)


if __name__ == '__main__':
    unittest.main()
