"""Contract checks for the optional-module seam, without loading Gold."""
import importlib.util
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from test_addon import Client


ROOT = Path(__file__).resolve().parents[1]


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ModuleAPITests(unittest.TestCase):
    def setUp(self):
        self.client = Client(quests=(), default_guide=True, party_mode='always')
        self.ns = self.client.ns
        self.lua = self.client.lua

    def test_existing_routing_and_utility_contract_is_present(self):
        for name in ('FindTravelPath', 'TravelPointDistance', 'PlayerPoint',
                     'RouteCostModel', 'CatalogueQuest', 'ReadPublic', 'Public',
                     'GuideInteger', 'SafeTitle', 'Option', 'SetOption', 'Print', 'On'):
            self.assertEqual(self.lua.eval('type')(self.ns[name]), 'function', name)
        self.assertEqual(self.ns.GoldAPIVersion, 1)
        self.assertIsNotNone(self.ns.catalogue)
        self.assertIsNotNone(self.ns.RouteCostModel().weights)

    def test_optional_addon_uses_public_api_from_its_own_namespace(self):
        api = self.lua.globals().WowTogetherModuleAPI
        self.assertEqual(api.version, 1)
        self.assertIsNotNone(api.RegisterModule)
        self.ns.catalogue = None
        self.assertIsNone(api.catalogue)
        self.ns.catalogue = self.lua.table_from({'count': 1})
        self.assertEqual(api.catalogue.count, 1)
        self.lua.execute('''
            local addonName, namespace = "WowTogether_Gold", {}
            local ns = _G.WowTogetherModuleAPI
            assert(ns and ns.version == 1 and ns.RegisterModule)
            ns.RegisterModule("Gold", {tab={title="Gold", render=function() end}})
        ''')
        self.assertIsNotNone(self.ns.ui.viewChoice.options['module:gold'])

    def test_false_module_setting_default_survives_nil_store_value(self):
        self.lua.execute('''
            local ns = ...
            ns.RegisterModule("Gold", {settingsGroup={title="Gold", entries={
                {key="gold.enabled", label="Enabled", default=false}},
                get=function() return nil end, set=function() end}})
        ''', self.ns)
        self.assertIs(self.ns.Option('gold.enabled'), False)

    def test_enabled_load_on_demand_addon_is_loaded_after_login(self):
        self.lua.execute('''
            loadedModule = nil
            IsAddOnLoaded = function() return false end
            LoadAddOn = function(name) loadedModule=name; return true end
        ''')
        self.ns.handlers.PLAYER_LOGIN()
        self.assertEqual(self.lua.globals().loadedModule, 'WowTogether_Gold')
        self.assertEqual(self.ns.optionalGoldStatus, 'loaded')

    def test_registration_adds_tab_settings_slash_and_probe(self):
        self.lua.execute('''
            local ns = ...
            optionStore = {}
            rendered, slashed = 0, nil
            ns.RegisterModule("Gold", {
                tab={title="Gold", render=function(page) rendered=rendered+1; assert(page) end},
                settingsGroup={title="Gold", description="Gold settings", entries={
                    {key="gold.recordLoot", label="Record loot", default=true}},
                    get=function(key) return optionStore[key] end,
                    set=function(key, value) optionStore[key]=value end},
                slash=function(text) slashed=text end,
                probe=function(output) output("API ready") end})
        ''', self.ns)
        self.assertIsNotNone(self.ns.ui.viewChoice.options['module:gold'])
        self.assertIsNotNone(self.ns.settings.pages['module:gold'])
        self.assertTrue(self.ns.Option('gold.recordLoot'))
        self.ns.SetOption('gold.recordLoot', False)
        self.assertFalse(self.ns.Option('gold.recordLoot'))
        self.ns.SetFilter('module:gold')
        self.assertTrue(self.ns.ui.content)
        self.assertGreater(self.lua.globals().rendered, 0)
        self.lua.globals().SlashCmdList.WOWTOGETHER('gold prices')
        self.assertEqual(self.lua.globals().slashed, 'prices')
        self.ns.Diagnostics()
        report = self.ns.diagnosticsText.GetText(self.ns.diagnosticsText)
        self.assertIn('Gold:', report)
        self.assertIn('API ready', report)
        with self.assertRaises(Exception):
            self.ns.RegisterModule('Gold', self.lua.table())
        with self.assertRaises(Exception):
            self.ns.RegisterModule('gold', self.lua.table())

    def test_trail_loop_uses_optimal_closed_walk_and_rejects_nonwalk(self):
        self.lua.execute('''
            local ns = ...
            local cost={{0,1,10,1},{1,0,1,10},{10,1,0,1},{1,10,1,0}}
            ns.FindTravelPath=function(a,b,flights)
                assert(flights==false)
                return {seconds=cost[a.id][b.id], legs={{method="walk"}}}
            end
        ''', self.ns)
        points = self.lua.table_from([{'id': i, 'mapID': 1, 'x': i / 10, 'y': .5}
                                      for i in range(1, 5)], recursive=True)
        loop = self.ns.TrailLoop(points)
        self.assertEqual(loop.seconds, 4)
        self.assertEqual(len(loop.legs), 4)
        self.assertEqual(loop.points[1].id, loop.points[5].id)
        self.lua.execute('''local ns=...; ns.FindTravelPath=function()
            return {seconds=1,legs={{method="taxi"}}} end''', self.ns)
        self.assertIsNone(self.ns.TrailLoop(points))

    def test_farm_stop_appears_on_route_and_clears(self):
        self.ns.RegisterModule('Gold', self.lua.table())
        self.ns.selectedRoute = self.lua.table_from({'stops': [
            {'id': 1, 'kind': 'q', 'mapID': 1, 'x': .4, 'y': .5, 'label': 'Quest'}]}, recursive=True)
        stop = self.lua.table_from({'module': 'Gold', 'kind': 'farm', 'mapID': 1,
                                    'x': .2, 'y': .3, 'label': 'Farm Silverleaf',
                                    'reason': 'Gather herbs for your crafting goal.'}, recursive=True)
        self.ns.PushGuideStop(stop)
        self.assertEqual(self.ns.selectedRoute.stops[1].kind, 'farm')
        self.assertEqual(self.ns.StopIcon(self.ns.selectedRoute.stops[1]), self.ns.STEP_SYMBOLS.farm)
        self.assertEqual(self.ns.StopSymbol(self.ns.selectedRoute.stops[1]), 'G')
        presentation = self.ns.GuideStepPresentation(self.ns.selectedRoute.stops[1])
        self.assertEqual(presentation.icon, self.ns.STEP_SYMBOLS.farm)
        self.assertEqual(presentation.what, 'Farm Silverleaf')
        self.assertEqual(presentation.why, 'Gather herbs for your crafting goal')
        self.assertEqual(presentation.status, 'Optional, on the way')
        self.assertEqual(presentation.decision.code, 'module-farm')
        self.ns.UpdateSelectedRoute()
        self.assertEqual(len(self.ns.selectedRoute.stops), 2)
        self.ns.ClearModuleStops('Gold')
        self.assertEqual(self.ns.selectedRoute.stops[1].kind, 'q')

    def test_sync_kind_dispatch_is_after_core_validation_and_unique(self):
        self.lua.execute('''local ns=...; received=nil
            ns.RegisterSyncKind("M", function(message, sender)
                received={message=message,sender=sender}; return true end)''', self.ns)
        with self.assertRaises(Exception):
            self.ns.RegisterSyncKind('M', self.lua.eval('function() end'))
        with self.assertRaises(Exception):
            self.ns.RegisterSyncKind('H', self.lua.eval('function() end'))
        self.ns.UpdateRoster()
        self.ns.Receive('WowTogetherV1', '1|M|payload', 'RAID', 'Bob-Test Realm')
        self.assertIsNone(self.lua.globals().received)
        self.ns.Receive('WowTogetherV1', '1|M|payload', 'PARTY', 'Bob-Test Realm')
        self.assertEqual(self.lua.globals().received.message, '1|M|payload')

    def test_research_hook_appends_json_events(self):
        self.ns.char.questResearch.events[1] = self.lua.table_from(
            {'event': 'accept', 'questID': 1})
        self.lua.execute('''local ns=...; ns.ResearchExportHook(function()
            return {{event="gold-drop", itemID=42, source="measured"}} end)''', self.ns)
        exported = json.loads(self.ns.ExportQuestResearch())
        self.assertEqual(exported['events'][0]['event'], 'accept')
        self.assertEqual(exported['events'][-1],
                         {'event': 'gold-drop', 'itemID': 42, 'source': 'measured'})


class PackagingBoundaryTests(unittest.TestCase):
    def test_boundary_rejects_private_namespace_and_accepts_api(self):
        checker = load_tool('boundary_check')
        self.assertEqual(checker.violations('ns.RegisterModule("Gold", {})'), [])
        self.assertTrue(checker.violations('ns.db = {}'))
        self.assertTrue(checker.violations('ns["char"]'))
        self.assertTrue(checker.violations('ns[key]'))
        self.assertTrue(checker.violations('ns.Gold.Secret()'))
        self.assertTrue(checker.violations('local core = ns; core.db = {}'))
        self.assertTrue(checker.violations('ns\n  .db = {}'))
        self.assertTrue(checker.violations('local root = _G; root.WowTogetherDB = {}'))
        self.assertTrue(checker.violations('_G.WowTogetherDB = {}'))
        self.assertTrue(checker.violations('getglobal("WowTogetherDB")'))
        self.assertEqual(checker.violations(
            'local addonName, namespace = ...\nlocal ns = _G.WowTogetherModuleAPI'), [])

    def test_gold_package_is_optional_and_validated_when_present(self):
        builder = load_tool('build_release')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(builder.optional_gold_sources(root))
            gold = root / 'WowTogether_Gold'
            gold.mkdir()
            (gold / 'WowTogether_Gold.toc').write_text(
                '## Interface: 16001\n## LoadOnDemand: 1\n'
                '## Dependencies: WowTogether\n## SavedVariables: WowTogetherGoldDB\nGold.lua\n')
            (gold / 'Gold.lua').write_text(
                'local addonName, namespace = ...\n'
                'local ns = _G.WowTogetherModuleAPI\n')
            self.assertEqual(builder.optional_gold_sources(root), ['Gold.lua'])
            (gold / 'WowTogether_Gold.toc').write_text('Gold.lua\n')
            with self.assertRaises(ValueError):
                builder.optional_gold_sources(root)

    def test_release_zip_includes_gold_when_package_exists(self):
        builder = load_tool('build_release')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for child in ROOT.iterdir():
                if not child.name.startswith('.') and child.name != 'WowTogether_Gold':
                    (root / child.name).symlink_to(child, target_is_directory=child.is_dir())
            gold = root / 'WowTogether_Gold'
            gold.mkdir()
            (gold / 'WowTogether_Gold.toc').write_text(
                '## Interface: 16001\n## LoadOnDemand: 1\n'
                '## Dependencies: WowTogether\n## SavedVariables: WowTogetherGoldDB\nGold.lua\n')
            (gold / 'Gold.lua').write_text(
                'local addonName, namespace = ...\n'
                'local ns = _G.WowTogetherModuleAPI\n')
            with patch.object(builder, 'ROOT', root):
                with patch('sys.argv', ['build_release.py', '--output', str(root / 'output')]):
                    with contextlib.redirect_stdout(io.StringIO()):
                        builder.main()
            version = next((root / 'output').glob('WowTogether-*.zip'))
            with ZipFile(version) as archive:
                self.assertIn('WowTogether_Gold/WowTogether_Gold.toc', archive.namelist())
                self.assertIn('WowTogether_Gold/Gold.lua', archive.namelist())


if __name__ == '__main__':
    unittest.main()
