"""Steady-state allocation checks for the party-mode route hot paths."""
import unittest

from test_0856 import destination, terrain_client
from test_navigation import navigator


class MemoryChurnTests(unittest.TestCase):
    def stabilize_public_apis(self, client):
        client.lua.globals().ns = client.ns
        # The live C_Map API returns a position value. Reuse its host equivalent
        # so this check measures addon allocations, not the mock's table literal.
        client.lua.execute('''
            function GetTime() return 10 end
            local position = {GetXY=function() return playerX, playerY end}
            C_Map.GetPlayerMapPosition=function() return position end
            local seen, noOp = {}, function() end
            local names = {"SetTextColor", "SetVertexColor", "SetWordWrap", "SetJustifyV", "SetJustifyH",
                "SetBackdropColor", "SetBackdropBorderColor", "SetColorTexture", "SetThickness",
                "SetFrameStrata", "SetAllPoints", "Raise", "RegisterForClicks"}
            local function stabilize(value)
                if type(value) ~= "table" or seen[value] then return end
                seen[value] = true
                if value.GetWidth then for _, name in ipairs(names) do value[name] = noOp end end
                for _, child in pairs(value) do stabilize(child) end
            end
            stabilize(ns.navigation); stabilize(ns.standaloneNavigation); stabilize(ns.minimapRoute)
        ''')

    def allocations_for(self, client, expression, calls=1000):
        client.lua.execute(f'{expression}; {expression}')
        client.lua.execute(f'''
            collectgarbage("collect")
            collectgarbage("stop")
            local before = collectgarbage("count")
            for index=1,{calls} do {expression} end
            allocationDelta = collectgarbage("count") - before
            collectgarbage("restart")
        ''')
        return client.lua.globals().allocationDelta

    def test_unchanged_route_calls_reuse_steady_state_state(self):
        client = navigator()
        self.stabilize_public_apis(client)
        self.assertLess(self.allocations_for(client, 'ns.UpdateNavigation(true)'), 4)
        self.assertLess(self.allocations_for(client, 'ns.minimapRoute.OnUpdate(ns.minimapRoute, .2)'), 4)
        self.assertLess(self.allocations_for(client, 'ns.DrawNavigationArrow(ns.navigation.state.angle)'), 4)

        client = terrain_client()
        self.stabilize_public_apis(client)
        goal = destination(client)
        client.lua.globals().goal = goal
        client.ns.TravelNetworkDestination(goal)
        self.assertLess(self.allocations_for(client, 'ns.TravelNetworkDestination(goal)'), 4)
        client.lua.execute('lineOrigin=ns.PlayerPoint(501,{})')
        self.assertLess(self.allocations_for(client, 'ns.TravelLinePoints(lineOrigin, goal)'), 4)

    def test_probe_reports_sections_without_forcing_collection(self):
        client = navigator()
        self.stabilize_public_apis(client)
        client.lua.execute('''
            realCollectgarbage = collectgarbage
            forcedCollections = 0
            collectgarbage = function(mode)
                if mode == "collect" then forcedCollections = forcedCollections + 1 end
                return realCollectgarbage(mode)
            end
        ''')
        client.lua.execute('local ns=...; ns.ShowDiagnostics=function(report) diagnosticReport=report end', client.ns)
        client.lua.execute('''
            realCollectgarbage("collect"); realCollectgarbage("stop")
            before=realCollectgarbage("count")
        ''')
        client.ns.Diagnostics()
        client.lua.execute('probeDelta=realCollectgarbage("count")-before; realCollectgarbage("restart")')
        self.assertEqual(client.lua.globals().forcedCollections, 0)
        self.assertLess(client.lua.globals().probeDelta, 1024)
        report = client.lua.globals().diagnosticReport
        self.assertIn('Heap increases observed (last 60 s)', report)
        self.assertIn('Lua heap:', report)
        self.assertIn('Last /wt probe allocation:', report)

    def test_allocation_ledger_is_bounded_to_sixty_one_time_buckets(self):
        client = navigator()
        client.lua.globals().ns = client.ns
        client.lua.execute('''
            ledgerClock=10
            function GetTime() return ledgerClock end
            clientAlloc={}
            start=ns.StartMemorySample(ns.MemorySampleSection.minimap)
            for index=1,100 do clientAlloc[index]=string.rep("x",64) end
            ns.EndMemorySample(ns.MemorySampleSection.minimap,start)
            first=nil
            ns.AllocationDiagnostics(function(line) if string.find(line,"Heap increases observed (last 60 s)",1,true) then first=line end end)
            ledgerClock=80
            expired=nil
            ns.AllocationDiagnostics(function(line) if string.find(line,"Heap increases observed (last 60 s)",1,true) then expired=line end end)
        ''')
        first, expired = client.lua.globals().first, client.lua.globals().expired
        self.assertIn('minimap', first)
        self.assertIn('0.0 MiB total', expired)
