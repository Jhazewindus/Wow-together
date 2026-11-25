"""Contract checks for the optional-module seam, without loading Gold."""
import importlib.util
import contextlib
import io
import json
import tempfile
import unittest
import re
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

    def test_ns_function_owners_are_not_overridden_across_files(self):
        definitions = re.compile(
            r'^\s*function\s+ns\.([A-Za-z_]\w*)\s*\('
            r'|^\s*ns\.([A-Za-z_]\w*)\s*=\s*function\s*\(', re.MULTILINE)
        assignments = re.compile(r'^\s*ns\.([A-Za-z_]\w*)\s*=', re.MULTILINE)
        owners, writes = {}, {}
        for path in ROOT.rglob('*.lua'):
            if '.git' in path.parts:
                continue
            source = path.read_text(encoding='utf-8')
            for first, second in definitions.findall(source):
                owners.setdefault(first or second, set()).add(path.resolve())
            for name in assignments.findall(source):
                writes.setdefault(name, set()).add(path.resolve())
        violations = {
            name: (owner_paths, write_paths - owner_paths)
            for name, owner_paths in owners.items()
            if len(owner_paths) == 1
            and (write_paths := writes.get(name, set())) - owner_paths
        }
        self.assertEqual(violations, {})

    def test_existing_routing_and_utility_contract_is_present(self):
        for name in ('FindTravelPath', 'TravelPointDistance', 'PlayerPoint',
                     'RouteCostModel', 'CatalogueQuest', 'ReadPublic', 'Public',
                     'GuideInteger', 'SafeTitle', 'Option', 'SetOption', 'Print', 'On'):
            self.assertEqual(self.lua.eval('type')(self.ns[name]), 'function', name)
        self.assertEqual(self.ns.GoldAPIVersion, 2)
        self.assertIsNotNone(self.ns.catalogue)
        self.assertIsNotNone(self.ns.RouteCostModel().weights)

    def test_public_module_api_surface_and_version_match_the_gold_contract(self):
        api = self.lua.globals().WowTogetherModuleAPI
        expected = {'version', 'STEP_SYMBOLS', 'RegisterModule', 'FindTravelPath',
                    'TravelPointDistance', 'PlayerPoint', 'TrailLoop', 'RouteCostModel',
                    'PushGuideStop', 'ClearModuleStops', 'RegisterSyncKind',
                    'CatalogueQuest', 'ReadPublic', 'Public', 'GuideInteger',
                    'SafeTitle', 'Option', 'SetOption', 'Print', 'On',
                    'ResearchExportHook', 'StartFarmCandidateScan', 'QueueModuleSync',
                    'PublishGoldFunction',
                    'AuctionQuote', 'FarmPriorSearch', 'FarmPriorSpawnSearch', 'StartModuleLoop', 'StopModuleLoop',
                    'SetFarmSession', 'RequestFarmSessionRefresh', 'GatheringFarmSearch',
                    'RegisterGatheringObserver', 'UIPanel', 'UILabel', 'UIButton',
                    'UIButtonTone', 'UIClose', 'UIHelp', 'UIDivider', 'UIColors',
                    'AuctionHouseVisible', 'AuctionHouseAnchor', 'RouteInCombat', 'After',
                    'OpenModulePage', 'StartFullPriceScan', 'StopFullPriceScan',
                    'FullPriceScanRunning', 'FullPriceScanSupported', 'BrowsePriceCount',
                    'ReadGoldSavedData', 'WriteGoldSavedData', 'GoldExternalPriceSources',
                    'GoldExternalPrice', 'GoldSpellName', 'GoldIsFishingLoot', 'GoldLootSourceInfo', 'PlanLoop', 'PlayerSpot'}
        self.assertEqual({key for key, _ in api.items()}, expected)
        self.assertEqual(api.version, 2)
        self.assertEqual(self.ns.GoldAPIVersion, 2)

    def test_module_auction_quote_is_read_only_and_does_not_call_gold_price_hook(self):
        api = self.lua.globals().WowTogetherModuleAPI
        self.lua.execute('serverClock=100000; function GetServerTime() return serverClock end')
        self.ns.StoreAuctionQuote(420, self.lua.table_from([[25, 2]], recursive=True), True)
        self.assertTrue(api.PublishGoldFunction('Price', self.lua.eval('function() error("must not run") end'))[0])
        price, age = api.AuctionQuote(420)
        self.assertEqual(price, 25)
        self.assertEqual(age, 0)
        self.assertIsNone(api.AuctionQuote(421))
        self.assertIsNone(api.AuctionQuote(-1))

    def test_farm_prior_search_validates_and_uses_clock_budget_from_module_namespace(self):
        api = self.lua.globals().WowTogetherModuleAPI
        self.lua.execute('''
            local addonName, addonNamespace = "WowTogether_Gold", {}
            moduleAPI = _G.WowTogetherModuleAPI
            priorDone = nil
        ''')
        external = self.lua.globals().moduleAPI
        self.assertEqual(external.FarmPriorSearch(self.lua.table_from({
            'minLevel': 10, 'maxLevel': 15, 'limit': 5}), self.lua.eval('function() end'))[0], False)
        self.assertIn('frame clock', external.FarmPriorSearch(self.lua.table_from({
            'minLevel': 10, 'maxLevel': 15, 'limit': 5}), self.lua.eval('function() end'))[1])
        self.assertEqual(self.ns.farmPriorData.count, 2850)
        self.assertEqual(external.FarmPriorSearch(self.lua.table_from({
            'minLevel': 0, 'maxLevel': 15, 'limit': 5}), self.lua.eval('function() end'))[0], False)
        self.ns.farmPriorData = self.lua.table_from({'records': [{
            'npcID': 77, 'name': 'Test wolf', 'minLevel': 11, 'maxLevel': 12,
            'confidence': 'legacy, unconfirmed',
            'mapID': 501, 'zoneName': 'Test Coast',
            'spawnPointCount': 1,
            'skinnable': False, 'skinningLoot': [],
            'loot': [{'itemID': 88, 'chance': 12.5, 'quantity': 2, 'source': 'test loot'}],
            'sources': {'npcID': 'test NPC ID', 'name': 'test name', 'level': 'test levels',
                'mapID': 'test map', 'zoneName': 'test zone',
                'loot': 'test loot', 'skinnable': 'test skinnable', 'skinningLoot': 'test skinning loot'}}]}, recursive=True)
        self.lua.execute('''
            clockTick=0
            function debugprofilestop() clockTick=clockTick+.1; return clockTick end
            priorDone=function(rows) priorResult=rows end
        ''')
        accepted = external.FarmPriorSearch(self.lua.table_from({
            'minLevel': 10, 'maxLevel': 15, 'mapID': 501, 'limit': 5}),
            self.lua.globals().priorDone)
        self.assertTrue(accepted)
        timers = self.lua.globals().timers
        while len(timers):
            callback = timers[1]
            self.lua.execute('table.remove(timers, 1)')
            callback()
        result = self.lua.globals().priorResult[1]
        self.assertEqual(result.npcID, 77)
        self.assertEqual(result.loot[1].itemID, 88)
        self.assertEqual(result.loot[1].source, 'test loot')
        self.assertEqual(result.loot[1].quantity, 2)
        self.assertEqual(result.spawnPointCount, 1)
        result.loot[1].chance = 99
        self.assertEqual(self.ns.farmPriorData.records[1].loot[1].chance, 12.5)

    def test_load_on_demand_legacy_farm_index_returns_loot_but_defers_spawn_points(self):
        api = self.lua.globals().WowTogetherModuleAPI
        self.lua.execute('''
            clockTick=0
            function debugprofilestop() clockTick=clockTick+.1; return clockTick end
            loadedFarmRows=nil
        ''')
        accepted = api.FarmPriorSearch(self.lua.table_from({'minLevel': 1, 'maxLevel': 60, 'limit': 1}),
            self.lua.eval('function(rows) loadedFarmRows=rows end'))
        self.assertTrue(accepted)
        while len(self.lua.globals().timers):
            callback = self.lua.globals().timers[1]
            self.lua.execute('table.remove(timers, 1)')
            callback()
        record = self.lua.globals().loadedFarmRows[1]
        self.assertEqual(record.confidence, 'legacy, unconfirmed')
        self.assertGreaterEqual(record.spawnPointCount, 1)
        self.assertIsNone(record.spawnPoints)
        self.assertGreaterEqual(record.loot[1].quantity, 1)
        self.assertIn('CMaNGOS', record.loot[1].source)

    def test_spawn_points_load_from_only_the_selected_zone_package(self):
        api = self.lua.globals().WowTogetherModuleAPI
        self.lua.execute('''
            clockTick=0
            function debugprofilestop() clockTick=clockTick+.1; return clockTick end
            loadedFarmPoints=nil
        ''')
        accepted = api.FarmPriorSpawnSearch(3, 1431,
            self.lua.eval('function(points) loadedFarmPoints=points end'))
        self.assertTrue(accepted)
        while len(self.lua.globals().timers):
            callback = self.lua.globals().timers[1]
            self.lua.execute('table.remove(timers, 1)')
            callback()
        points = self.lua.globals().loadedFarmPoints
        self.assertEqual(len(points), 9)
        self.assertTrue(all(points[index].mapID == 1431 for index in range(1, len(points) + 1)))
        self.assertIn('converted legacy world coordinate', points[1].source)

    def test_gathering_search_returns_only_valid_source_backed_zone_facts_to_external_namespace(self):
        api = self.lua.globals().WowTogetherModuleAPI
        self.lua.execute('''
            local ns=...
            ns.profile={level=12,faction="Alliance",mapID=501,zone="Test Coast"}
            ns.GatheringFarmFactCount=function() return 1 end
            ns.GatheringFarmFact=function(index)
                if index~=1 then return nil end
                return {professionID=186,profession="Mining",node="Copper Vein",requiredSkill=1,ownSkill=40,
                    zone="Test Coast",zoneMinLevel=1,zoneMaxLevel=10,loot={{itemID=2770,source="test item source"}},
                    sources={profession="test profession",node="test node",skill="test skill",zone="test zone",
                        mapID="test map",yield="test yield"}}
            end
            ns.KnownZoneMaps=function() return {[501]=true} end
            ns.MapName=function(mapID) return mapID == 501 and "Test Coast" or ("Map " .. mapID) end
            clockTick=0
            function debugprofilestop() clockTick=clockTick+.1; return clockTick end
            gatheringDone=nil
        ''', self.ns)
        self.lua.execute('local addonName, addonNamespace = "WowTogether_Gold", {}; externalAPI = _G.WowTogetherModuleAPI')
        external = self.lua.globals().externalAPI
        self.assertFalse(external.GatheringFarmSearch(self.lua.table_from({'profession': 'Gold', 'limit': 5}),
            self.lua.eval('function() end'))[0])
        self.assertFalse(external.GatheringFarmSearch(self.lua.table_from({'profession': 'Mining', 'limit': 51}),
            self.lua.eval('function() end'))[0])
        self.assertTrue(external.GatheringFarmSearch(self.lua.table_from({'profession': 'Mining', 'limit': 5}),
            self.lua.eval('function(rows) gatheringResult=rows end')))
        self.client.drain()
        rows = self.lua.globals().gatheringResult
        self.assertEqual(len(rows), 1)
        row = rows[1]
        self.assertEqual(row.node, 'Copper Vein')
        self.assertEqual(row.ownSkill, 40)
        self.assertEqual(row.zones[1].mapID, 501)
        self.assertEqual(row.loot[1].itemID, 2770)
        self.assertEqual(row.sources['yield'], 'test yield')

    def test_gathering_observer_gets_validated_copied_events_and_can_unsubscribe(self):
        api = self.lua.globals().WowTogetherModuleAPI
        self.ns.RegisterModule('Gold', self.lua.table())
        self.lua.execute('''
            externalAPI=_G.WowTogetherModuleAPI
            observed=nil
            unsubscribe=nil
            function onGathered(event)
                observed=event
                event.x=0
            end
        ''')
        accepted, unsubscribe = self.lua.globals().externalAPI.RegisterGatheringObserver('Gold', self.lua.globals().onGathered)
        self.assertTrue(accepted)
        self.lua.execute('''
            local ns=...
            gatheringEvent={professionID=186,profession="Mining",mapID=501,x=.4,y=.6,itemID=2770,
                quantity=2,source="gather-node",observedAt=4}
            ns.RunHooks("gatheringObserved", gatheringEvent)
        ''', self.ns)
        self.assertEqual(self.lua.globals().observed.profession, 'Mining')
        self.assertEqual(self.lua.globals().observed.quantity, 2)
        self.assertEqual(self.lua.globals().gatheringEvent.x, .4)
        self.assertTrue(unsubscribe())
        self.lua.globals().observed = None
        self.ns.RunHooks('gatheringObserved', self.lua.table_from({'professionID': 186, 'profession': 'Mining',
            'mapID': 501, 'x': .4, 'y': .6, 'itemID': 2770, 'quantity': 1, 'source': 'gather-node'}))
        self.assertIsNone(self.lua.globals().observed)

    def test_module_loop_starts_closes_walk_route_and_reports_stop(self):
        api = self.lua.globals().WowTogetherModuleAPI
        self.ns.RegisterModule('Gold', self.lua.table())
        self.lua.execute('''
            local ns=...
            ns.routeSelection=nil
            ns.TravelPointDistance=function() return 7 end
            ns.RouteInCombat=function() return false end
            ns.DrawRoute=function() end
            ns.AttachRouteProvider=function() end
            ns.OpenGuideWindow=function() end
            loopStoppedReason=nil
            loopStarted=0
        ''', self.ns)
        spec = self.lua.table_from({'title': 'Wolf loop', 'points': [
            {'mapID': 501, 'x': .3, 'y': .4, 'label': 'Hunt wolves', 'reason': 'Collect hides.'},
            {'mapID': 501, 'x': .6, 'y': .4, 'label': 'Hunt more wolves', 'reason': 'Stay near the den.'}],
            'onStop': self.lua.eval('function(reason) loopStoppedReason=reason end'),
            'onStart': self.lua.eval('function() loopStarted=loopStarted+1 end')}, recursive=True)
        self.assertTrue(api.StartModuleLoop('Gold', spec))
        self.assertEqual(self.lua.globals().loopStarted, 1)
        self.assertEqual(self.ns.routeSelection.mode, 'module')
        self.assertEqual(self.ns.selectedRoute.stops[1].kind, 'farm')
        self.assertTrue(api.StopModuleLoop('Gold'))
        self.assertEqual(self.lua.globals().loopStoppedReason, 'stopped by module')
        self.assertFalse(api.StopModuleLoop('Gold', 'unexpected')[0])

    def test_module_loop_stops_survive_a_full_refresh(self):
        api = self.lua.globals().WowTogetherModuleAPI
        self.ns.RegisterModule('Gold', self.lua.table())
        self.lua.execute('''
            local ns=...
            ns.routeSelection=nil
            ns.TravelPointDistance=function() return 7 end
            ns.RouteInCombat=function() return false end
            ns.DrawRoute=function() end; ns.AttachRouteProvider=function() end
            ns.OpenGuideWindow=function() end
            originalCreateFrame=CreateFrame
            function CreateFrame(...)
                moduleLoopFrame=originalCreateFrame(...)
                return moduleLoopFrame
            end
            perfEvents={}
            ns.PerfBegin=function(name) perfEvents[#perfEvents+1]="begin:"..name; return name end
            ns.PerfEnd=function(name, started) perfEvents[#perfEvents+1]="end:"..started end
        ''', self.ns)
        spec = self.lua.table_from({'title': 'Three-stop loop', 'points': [
            {'mapID': 501, 'x': .2, 'y': .2, 'label': 'First', 'reason': 'First reason.'},
            {'mapID': 501, 'x': .5, 'y': .2, 'label': 'Second', 'reason': 'Second reason.'},
            {'mapID': 501, 'x': .4, 'y': .6, 'label': 'Third', 'reason': 'Third reason.'}],
            'onStop': self.lua.eval('function() end')}, recursive=True)
        self.assertTrue(api.StartModuleLoop('Gold', spec))
        self.lua.execute('moduleLoopFrame.OnUpdate(moduleLoopFrame, .01)')
        self.assertEqual(list(self.lua.globals().perfEvents.values()), ['begin:moduleLoop', 'end:moduleLoop'])
        before = len(self.ns.selectedRoute.stops)
        self.assertEqual(before, 4)
        self.ns.Refresh(True)
        self.assertEqual(len(self.ns.selectedRoute.stops), 4)
        self.assertEqual(self.ns.selectedRoute.stops[1].label, 'First')

    def test_module_loop_requires_confirmation_before_replacing_active_guide(self):
        api = self.lua.globals().WowTogetherModuleAPI
        self.ns.RegisterModule('Gold', self.lua.table())
        self.lua.execute('''
            local ns=...
            ns.FindTravelPath=function(a,b) return {seconds=1,legs={{method="walk"}}} end
            ns.TravelPointDistance=function() return 7 end
            ns.RouteInCombat=function() return false end
            ns.DrawRoute=function() end; ns.AttachRouteProvider=function() end
            ns.OpenGuideWindow=function() end
            popupRequest=nil
            StaticPopup_Show=function(key, title, _, data)
                popupRequest=data
                return {key=key,title=title}
            end
            StaticPopupDialogs={}
            loopStarted=0
        ''', self.ns)
        self.ns.routeSelection = self.lua.table_from({'key': 'existing:guide'})
        self.ns.selectedRoute = self.lua.table_from({'stops': []})
        spec = self.lua.table_from({'title': 'Ore loop', 'points': [
            {'mapID': 501, 'x': .3, 'y': .4, 'label': 'Mine ore', 'reason': 'Follow the vein.'},
            {'mapID': 501, 'x': .6, 'y': .4, 'label': 'Mine more ore', 'reason': 'Continue around.'}],
            'onStop': self.lua.eval('function() end'),
            'onStart': self.lua.eval('function() loopStarted=loopStarted+1 end')}, recursive=True)
        self.assertTrue(api.StartModuleLoop('Gold', spec))
        self.assertEqual(self.lua.globals().loopStarted, 0)  # Deferred until the player accepts.
        self.assertEqual(self.ns.routeSelection.key, 'existing:guide')
        self.lua.globals().StaticPopupDialogs.WOWTOGETHER_MODULE_LOOP_CONFIRM.OnAccept(
            None, self.lua.globals().popupRequest)
        self.assertEqual(self.ns.routeSelection.mode, 'module')
        self.assertEqual(self.lua.globals().loopStarted, 1)
        api.StopModuleLoop('Gold')

    def test_module_loop_reports_player_refusal_and_acceptance_during_combat(self):
        api = self.lua.globals().WowTogetherModuleAPI
        self.ns.RegisterModule('Gold', self.lua.table())
        self.lua.execute('''
            local ns=...
            ns.FindTravelPath=function(a,b) return {seconds=1,legs={{method="walk"}}} end
            ns.TravelPointDistance=function() return 7 end
            inCombat=false
            ns.RouteInCombat=function() return inCombat end
            ns.DrawRoute=function() end; ns.AttachRouteProvider=function() end
            ns.OpenGuideWindow=function() end
            popupRequest=nil
            StaticPopup_Show=function(key, title, _, data)
                popupRequest=data
                return {key=key,title=title,data=data}
            end
            StaticPopupDialogs={}
            loopStopReasons={}
            loopStarted=0
            function loopStopped(reason) loopStopReasons[#loopStopReasons+1]=reason end
        ''', self.ns)
        self.ns.routeSelection = self.lua.table_from({'key': 'existing:guide'})
        self.ns.selectedRoute = self.lua.table_from({'stops': []})
        spec = self.lua.table_from({'title': 'Ore loop', 'points': [
            {'mapID': 501, 'x': .3, 'y': .4, 'label': 'Mine ore', 'reason': 'Follow the vein.'},
            {'mapID': 501, 'x': .6, 'y': .4, 'label': 'Mine more ore', 'reason': 'Continue around.'}],
            'onStop': self.lua.globals().loopStopped,
            'onStart': self.lua.eval('function() loopStarted=loopStarted+1 end')}, recursive=True)
        self.assertTrue(api.StartModuleLoop('Gold', spec))
        self.assertEqual(self.lua.globals().loopStarted, 0)  # Refusal path never starts the session clock.
        dialog = self.lua.globals().StaticPopupDialogs.WOWTOGETHER_MODULE_LOOP_CONFIRM
        dialog.OnCancel(None, self.lua.globals().popupRequest)
        self.assertEqual(self.lua.globals().loopStopReasons[1], 'player declined guide replacement')
        self.assertTrue(api.StartModuleLoop('Gold', spec))
        request = self.lua.globals().popupRequest
        self.lua.globals().inCombat = True
        dialog.OnAccept(None, request)
        self.assertEqual(self.lua.globals().loopStopReasons[2], 'guide replacement accepted during combat')
        self.assertEqual(self.lua.globals().loopStarted, 0)
        self.assertEqual(self.ns.routeSelection.key, 'existing:guide')

    def test_farm_session_data_is_validated_displayed_and_refresh_is_rate_limited(self):
        api = self.lua.globals().WowTogetherModuleAPI
        self.ns.RegisterModule('Gold', self.lua.table())
        self.lua.execute('''
            local ns=...
            function GetTime() return 10 end
            ns.RouteInCombat=function() return false end
            redrawCount=0; ns.RedrawGoldSessionCard=function() redrawCount=redrawCount+1 end
        ''', self.ns)
        self.assertFalse(api.SetFarmSession('Gold', self.lua.table_from({'label': 'Farm'}))[0])
        self.assertTrue(api.SetFarmSession('Gold', self.lua.table_from({'label': 'Wolf den',
            'estimatedCopperPerHour': 100000, 'actualCopperPerHour': 80000, 'startTime': 100,
            'estimatedBasis': 'legacy loot chance at 90 kills/hour',
            'actualBasis': 'observed drops over 20 minutes'})))
        card = self.ns.ModuleFarmSessionForCard()
        self.assertIn('Estimated 10.0 gold/hour', card.detail)
        self.assertIn('Actual 8.0 gold/hour', card.detail)
        self.assertIn('Estimate: legacy loot chance', card.detail)
        self.assertIn('Actual: observed drops', card.detail)
        self.ns.SetOption('uiNext', True)
        self.ns.RenderRecommended(self.ns.NewQuestQuery())
        self.assertTrue(self.ns.ui.home.goldSession.IsShown(self.ns.ui.home.goldSession))
        self.assertEqual(self.ns.ui.home.goldSession.point[1], 'TOPLEFT')
        self.assertIn('Actual 8.0 gold/hour', self.ns.ui.home.goldSession.detail.GetText(self.ns.ui.home.goldSession.detail))
        self.assertTrue(api.RequestFarmSessionRefresh('Gold'))
        self.assertFalse(api.RequestFarmSessionRefresh('Gold')[0])

    def test_gold_functions_publish_only_named_hooks_with_safe_native_fallbacks(self):
        api = self.lua.globals().WowTogetherModuleAPI
        publish = api.PublishGoldFunction
        self.assertEqual(publish('Unknown', self.lua.eval('function() end'))[0], False)
        self.assertEqual(publish('Price', None)[0], False)
        self.assertTrue(publish('Price', self.lua.eval('function(id, quantity) return 777, true end'))[0])
        self.assertEqual(self.ns.AuctionUnitPrice(999, 3), (777, True))
        # A later publisher replaces this name without replacing core functions.
        self.ns.StoreAuctionQuote(999, self.lua.table_from([[12, 3]], recursive=True), True)
        self.assertTrue(publish('Price', self.lua.eval('function() error("price unavailable") end'))[0])
        self.assertEqual(self.ns.AuctionUnitPrice(999, 1), (12, True))
        self.assertTrue(publish('Price', self.lua.eval('function() return 0, true end'))[0])
        self.assertEqual(self.ns.AuctionUnitPrice(999, 1), (12, True))
        self.assertEqual(self.ns.GoldAPIVersion, 2)

    def test_gold_suggestions_are_core_recommendation_cards_not_party_progress(self):
        api = self.lua.globals().WowTogetherModuleAPI
        before, _ = self.ns.RecommendedItems()
        self.assertFalse(any(item.kind == 'gold' for item in before.values()))
        self.lua.execute('''
            goldActionCount = 0
            goldSuggestion = function()
                return {{key="ore", title="Gather copper", detail="A nearby vein can supply your smelting plan.",
                    priority=450, action=function() goldActionCount=goldActionCount+1 end}}
            end
        ''')
        self.assertTrue(api.PublishGoldFunction('Suggestions', self.lua.globals().goldSuggestion)[0])
        items, _ = self.ns.RecommendedItems()
        cards = [item for item in items.values() if item.kind == 'gold']
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].title, 'Gather copper')
        self.assertEqual(cards[0].detail, 'A nearby vein can supply your smelting plan.')
        self.assertEqual(cards[0].action, 'Follow')
        cards[0].start()
        self.assertEqual(self.lua.globals().goldActionCount, 1)
        self.assertTrue(api.PublishGoldFunction('Suggestions', self.lua.eval('''function()
            return {{key="ore", title="Smelt copper", detail="Use the gathered ore.", priority=400,
                action=function() end}}
        end'''))[0])
        refreshed, _ = self.ns.RecommendedItems()
        self.assertEqual([item.title for item in refreshed.values() if item.kind == 'gold'], ['Smelt copper'])

    def test_gold_session_card_receives_copied_summary_and_core_renders_the_action(self):
        api = self.lua.globals().WowTogetherModuleAPI
        self.ns.BeginGuideSession(self.lua.table_from({'key': 'test:guide', 'title': 'Test guide'}))
        before = self.ns.GuideSessionSummary().title
        self.lua.execute('''
            goldSessionActionCount, goldSessionInputTitle = 0, nil
            goldSession = function(summary)
                goldSessionInputTitle = summary.title
                summary.title = "mutated copy"
                return {title="Gold session", detail="You gained 8 silver.",
                    action=function() goldSessionActionCount=goldSessionActionCount+1 end}
            end
        ''')
        self.assertTrue(api.PublishGoldFunction('SessionCard', self.lua.globals().goldSession)[0])
        self.ns.RenderRecommended(self.ns.NewQuestQuery())
        card = self.ns.ui.home.goldSession
        self.assertTrue(card.IsShown(card))
        self.assertEqual(card.data.title, 'Gold session')
        self.assertEqual(self.lua.globals().goldSessionInputTitle, before)
        self.assertEqual(self.ns.GuideSessionSummary().title, before)
        card.data.start()
        self.assertEqual(self.lua.globals().goldSessionActionCount, 1)

    def test_invalid_gold_callback_results_and_exceptions_leave_core_behavior_intact(self):
        api = self.lua.globals().WowTogetherModuleAPI
        self.assertTrue(api.PublishGoldFunction('Suggestions', self.lua.eval('function() error("no cards") end'))[0])
        self.assertTrue(api.PublishGoldFunction('SessionCard', self.lua.eval('function() return {title="no action"} end'))[0])
        self.ns.RenderRecommended(self.ns.NewQuestQuery())
        self.assertFalse(self.ns.ui.home.goldSession.IsShown(self.ns.ui.home.goldSession))
        self.assertEqual(len(self.ns.Suggestions()), 0)

    def test_optional_addon_uses_public_api_from_its_own_namespace(self):
        api = self.lua.globals().WowTogetherModuleAPI
        self.assertEqual(api.version, 2)
        self.assertIsNotNone(api.RegisterModule)
        self.ns.catalogue = None
        self.assertIsNone(api.catalogue)
        self.ns.catalogue = self.lua.table_from({'count': 1})
        self.assertEqual(api.catalogue.count, 1)
        self.lua.execute('''
            local addonName, namespace = "WowTogether_Gold", {}
            local ns = _G.WowTogetherModuleAPI
            assert(ns and ns.version == 2 and ns.RegisterModule)
            ns.RegisterModule("Gold", {tab={title="Gold", render=function() end}})
        ''')
        self.assertIsNotNone(self.ns.ui.viewChoice.options['module:gold'])
        self.assertIsNotNone(self.ns.ui.hubModuleButtons['module:gold'])

    def test_module_tab_registered_before_hub_creation_is_added_to_rail(self):
        self.ns.ui = None
        self.ns.settings = None
        self.lua.execute('''local ns=...; ns.RegisterModule("Early", {
            tab={title="Early tab", render=function() end}})''', self.ns)
        self.ns.CreateUI()
        self.assertIsNotNone(self.ns.ui.hubModuleButtons['module:early'])

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
        self.assertIsNotNone(self.ns.ui.hubModuleButtons['module:gold'])
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

    def test_trail_loop_uses_estimated_closed_distance_without_searching_paths(self):
        self.lua.execute('''
            local ns = ...
            local cost={{0,1,10,1},{1,0,1,10},{10,1,0,1},{1,10,1,0}}
            ns.TravelPointDistance=function(a,b)
                return cost[a.id][b.id] * 7
            end
            ns.FindTravelPath=function() error("loop must not search paths") end
        ''', self.ns)
        points = self.lua.table_from([{'id': i, 'mapID': 1, 'x': i / 10, 'y': .5}
                                      for i in range(1, 5)], recursive=True)
        loop = self.ns.TrailLoop(points)
        self.assertEqual(loop.seconds, 4)
        self.assertEqual(len(loop.legs), 4)
        self.assertTrue(loop.legs[1].estimated)
        self.assertEqual(loop.points[1].id, loop.points[5].id)

    def test_farm_stop_appears_on_route_and_clears(self):
        self.ns.RegisterModule('Gold', self.lua.table())
        self.ns.selectedRoute = self.lua.table_from({'stops': [
            {'id': 1, 'kind': 'q', 'mapID': 1, 'x': .4, 'y': .5, 'label': 'Quest'}]}, recursive=True)
        stop = self.lua.table_from({'module': 'Gold', 'kind': 'farm', 'mapID': 1,
                                    'x': .2, 'y': .3, 'label': 'Farm Silverleaf',
                                    'reason': 'Gather herbs for your crafting goal.'}, recursive=True)
        self.ns.PushGuideStop(stop)
        self.assertEqual(self.ns.selectedRoute.stops[1].kind, 'farm')
        self.assertEqual(self.ns.StopIcon(self.ns.selectedRoute.stops[1]), self.ns.StepIconTexture('farm'))
        self.assertEqual(self.ns.StopSymbol(self.ns.selectedRoute.stops[1]), 'G')
        presentation = self.ns.GuideStepPresentation(self.ns.selectedRoute.stops[1])
        self.assertEqual(presentation.icon, self.ns.StepIconTexture('farm'))
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

    def test_module_sync_queues_only_registered_bounded_background_packets(self):
        api = self.lua.globals().WowTogetherModuleAPI
        self.assertFalse(api.QueueModuleSync('M', 'D|sample'))
        self.ns.RegisterSyncKind('M', self.lua.eval('function() return true end'))
        self.assertFalse(api.QueueModuleSync('Q', 'D|sample'))
        self.assertFalse(api.QueueModuleSync('M', ''))
        self.assertFalse(api.QueueModuleSync('M', 'D|bad\npacket'))
        self.assertFalse(api.QueueModuleSync('M', 'x' * 252))
        self.assertFalse(api.QueueModuleSync('M', 'D|sample', 'control'))
        self.assertTrue(api.QueueModuleSync('M', 'D|sample'))
        sent = self.client.drain()
        self.assertIn(('WowTogetherV1', '1|M|D|sample', 'PARTY'), sent)

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
        self.assertEqual(checker.violations('local value = ns.ReadPublic(GetTime)'), [])
        self.assertEqual(checker.violations('local scanner = ns.StartFarmCandidateScan'), [])
        self.assertEqual(checker.violations('local spawnSearch = ns.FarmPriorSpawnSearch'), [])
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
