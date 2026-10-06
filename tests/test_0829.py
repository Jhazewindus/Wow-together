"""Packed data must preserve every fact, mutation and guide behavior in Lua 5.1."""
import sys
import unittest
import hashlib
import json

from lupa.lua51 import LuaRuntime
from test_addon import Client, ROOT
sys.path.insert(0, str(ROOT / 'tools'))
from pack_data import Packer
from build_quest_dataset import own_lua


class PackedDataTests(unittest.TestCase):
    def fixture(self, rows, lazy=False):
        lua = LuaRuntime(unpack_returned_tuples=True)
        ns = lua.table()
        lua.execute('assert(loadstring(...))(select(2,...))',
            (ROOT / 'WowTogether/DataStore.lua').read_text(), 'WowTogether', ns)
        packer = Packer()
        body = packer.records('fixture', 'ns.rows', rows, lazy_rows=lazy)
        lua.execute('assert(loadstring(...))(select(2,...))', packer.code(body, 'Test data.'), 'WowTogether', ns)
        return lua, ns

    def test_lossless_nested_values_unicode_false_empty_tables_and_float_precision(self):
        values = {'nested': [{'name': 'é Snow\n"\\', 'off': False, 'on': True, 'fraction': .12345678912345678},
                             {5: {'empty': [], 'map': {7: 'seven'}}}]}
        lua, ns = self.fixture({4: {'title': 'Metadata', 'details': values}})
        self.assertEqual(ns.rows[4].title, 'Metadata')
        self.assertEqual(ns.PackedDataStats()[1].decoded, 0)
        detail = ns.rows[4].details
        self.assertEqual(detail.nested[1].name, 'é Snow\n"\\')
        self.assertFalse(detail.nested[1].off)
        self.assertTrue(detail.nested[1].on)
        self.assertEqual(detail.nested[1].fraction, .12345678912345678)
        self.assertEqual(len(detail.nested[2][5].empty), 0)
        self.assertEqual(detail.nested[2][5]['map'][7], 'seven')
        self.assertEqual(ns.PackedDataStats()[1].decoded, 1)
        self.assertEqual(ns.PackedDataStats()[1].packedBytes, 0)

    def test_missing_keys_do_not_unpack_any_details(self):
        _, ns = self.fixture({1: {'title': 'Test', 'details': [1, 2]}})
        self.assertIsNone(ns.rows[1].notPresent)
        self.assertEqual(ns.PackedDataStats()[1].decoded, 0)

    def test_only_requested_field_unpacks_and_identity_survives_collection(self):
        lua, ns = self.fixture({1: {'first': [{'x': .2}], 'second': [{'x': .8}]}})
        lua.globals().testNS = ns
        lua.execute("held=testNS.rows[1].first;held[1].x=.9;collectgarbage('collect');assert(rawequal(held,testNS.rows[1].first))")
        self.assertEqual(ns.rows[1].first[1].x, .9)
        self.assertEqual(ns.PackedDataStats()[1].decoded, 1)
        self.assertEqual(ns.rows[1].second[1].x, .8)

    def test_replacements_including_nil_do_not_restore_old_data(self):
        _, ns = self.fixture({1: {'first': [1], 'second': [2]}})
        ns.rows[1].first = None
        ns.rows[1].second = 'Replacement'
        self.assertIsNone(ns.rows[1].first)
        self.assertEqual(ns.rows[1].second, 'Replacement')
        self.assertEqual(ns.PackedDataStats()[1].packedBytes, 0)

    def test_entity_metadata_and_details_load_separately(self):
        _, ns = self.fixture({1: {'name': 'NPC', 'patrols': [[.2, .3]]}, 2: {'name': 'Other'}}, True)
        self.assertEqual(ns.PackedDataStats()[1].loadedRows, 0)
        self.assertEqual(ns.rows[1].name, 'NPC')
        self.assertEqual(ns.PackedDataStats()[1].loadedRows, 1)
        self.assertEqual(ns.PackedDataStats()[1].decoded, 0)
        self.assertIsNone(ns.rows[100])
        self.assertEqual(ns.rows[1].patrols[1][2], .3)
        self.assertEqual(ns.PackedDataStats()[1].decoded, 1)

    def test_audit_materialization_exposes_all_fields_without_internal_keys(self):
        _, ns = self.fixture({1: {'name': 'NPC', 'patrols': [[.2, .3]]}, 2: {'name': 'Other', 'data': {8: [False]}}}, True)
        ns.MaterializePackedData()
        self.assertEqual(set(ns.rows.keys()), {1, 2})
        self.assertEqual(set(ns.rows[1].keys()), {'name', 'patrols'})
        self.assertEqual(set(ns.rows[2].keys()), {'name', 'data'})
        self.assertFalse(ns.rows[2].data[8][1])

    def test_shipped_startup_leaves_entities_and_dungeons_packed(self):
        c = Client(use_catalogue=True, default_guide=True)
        stats = {row.name: row for row in c.ns.PackedDataStats().values()}
        self.assertEqual(c.ns.catalogue.count, 5230)
        for key in ('entities-npc', 'entities-object', 'entities-item'):
            self.assertEqual(stats[key].loadedRows, 0)
        for key in ('dungeon-journal', 'dungeon-maps'):
            self.assertEqual(stats[key].decoded, 0)
        c.lua.eval('collectgarbage')('collect')
        self.assertLess(c.lua.eval('collectgarbage')('count') / 1024, 32)

    def test_opening_one_dungeon_keeps_other_loot_and_maps_packed(self):
        c = Client(use_catalogue=True)
        c.ns.DungeonViewerData('wailing-caverns')
        stats = {row.name: row for row in c.ns.PackedDataStats().values()}
        for key in ('dungeon-journal', 'dungeon-maps'):
            self.assertGreater(stats[key].decoded, 0)
            self.assertLess(stats[key].decoded, stats[key].total)
        self.assertEqual(c.ns.DungeonViewerData('blackfathom-deeps').name, 'Blackfathom Deeps')

    def test_memory_report_is_read_only_and_capability_guarded(self):
        c = Client(use_catalogue=True)
        c.lua.execute('UpdateAddOnMemoryUsage=nil;GetAddOnMemoryUsage=nil;C_AddOns=nil')
        lines = []
        c.ns.MemoryDiagnostics(lines.append)
        self.assertIn('Addon memory API: unavailable', lines)
        before = [(r.name, r.decoded) for r in c.ns.PackedDataStats().values()]
        c.lua.execute('memoryUpdates=0;C_AddOns={UpdateAddOnMemoryUsage=function() memoryUpdates=memoryUpdates+1 end,GetAddOnMemoryUsage=function() return 40960 end}')
        c.ns.MemoryDiagnostics(lines.append)
        self.assertTrue(any('40.0 MiB' in s for s in lines))
        self.assertEqual(c.lua.globals().memoryUpdates, 1)
        self.assertEqual(before, [(r.name, r.decoded) for r in c.ns.PackedDataStats().values()])
        c.lua.execute('C_AddOns.GetAddOnMemoryUsage=function() return secret end')
        c.ns.MemoryDiagnostics(lines.append)

    def test_all_source_fields_match_pre_packing_fingerprints(self):
        def canonical(value):
            if isinstance(value, dict): return {str(k): canonical(v) for k, v in value.items()}
            if isinstance(value, list): return [canonical(v) for v in value]
            return value
        baseline = json.loads((ROOT / 'tests/memory-data-fingerprints.json').read_text())
        for field, expected in baseline['datasets'].items():
            value = canonical(own_lua(ROOT / 'WowTogether' / expected['file'], field))
            digest = hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
            self.assertEqual(digest, expected['sha256'], field)


if __name__ == '__main__':
    unittest.main()
