"""Dungeon quest routes use the compact instance definitions, not the retired journal pack."""
import unittest
from test_addon import Client

class DungeonFlowTests(unittest.TestCase):
    def test_active_interior_objectives_use_instance_area_ids(self):
        c = Client(quests=())
        ns = c.ns
        c.lua.globals().ns = ns
        c.lua.execute(r'''
          ns.active[900], ns.active[901] = true, true
          ns.readyToTurnIn = {}
          ns.QuestProgressReady = function() return false end
          ns.FilterGuideStages = function(stages) return stages end
          ns.RouteStages = function(record)
            return {{id=record.id, mapID=501, x=.2, y=.2, kind='q', targetName='A target'}}
          end
          ns.GuideDestinationDecision = function() return {specificBenefit=true} end
        ''')
        definition = c.lua.table_from({"areaIDs": [501]}, recursive=True)
        group = c.lua.table_from({"name": "Test Dungeon", "definition": definition}, recursive=True)
        guide = c.lua.table_from({
            "key": "dungeon:test", "title": "Test dungeon quests", "dungeonKey": "test",
            "dungeon": group, "dungeonPhase": "run",
            "records": c.lua.table_from([
                c.lua.table_from({"id": 900, "title": "Later Quest"}),
                c.lua.table_from({"id": 901, "title": "Earlier Quest"}),
            ]), "collectionGoals": c.lua.table_from({900: True, 901: True}),
        })
        route = ns.BuildDungeonRoute(guide, False, False)
        stops = [route.stops[i] for i in range(1, len(route.stops) + 1)]
        self.assertEqual([stop.id for stop in stops], [900, 901])
        self.assertTrue(all(stop.mapID == 501 for stop in stops))
        self.assertIsNone(stops[0].dungeonEncounterOrder)
        self.assertIsNone(stops[0].dungeonLootWatch)

if __name__ == "__main__":
    unittest.main()
