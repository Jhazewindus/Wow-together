"""Dungeon run routing follows active interior objectives and journal order."""
import unittest

from test_addon import Client


class DungeonFlowTests(unittest.TestCase):
    def test_active_interior_objectives_follow_encounter_order(self):
        c = Client(quests=())
        ns = c.ns
        c.lua.globals().ns = ns
        ns.profile.classID = 8
        c.lua.execute(r'''
          ns.active[900], ns.active[901] = true, true
          ns.readyToTurnIn = {}
          ns.QuestProgressReady = function() return false end
          ns.FilterGuideStages = function(stages) return stages end
          ns.DungeonViewerData = function()
            return {maps={{mapID=501}}, bosses={
              {id=101, name='First Boss', encounterOrder=1,
                loot={{id=555, name='Test Staff', classID=2, subclass=7}}},
              {id=102, name='Second Boss', encounterOrder=2},
            }}
          end
          ns.RouteStages = function(record)
            if record.id == 900 then return {{id=900, mapID=501, x=.8, y=.8,
              kind='q', entityID=102, targetName='Second Boss', title=record.title}} end
            return {{id=901, mapID=501, x=.2, y=.2,
              kind='q', entityID=101, targetName='First Boss', title=record.title}}
          end
          ns.GuideDestinationDecision = function() return {specificBenefit=true} end
        ''')
        guide = c.lua.table_from({
            "key": "dungeon:test", "title": "Test dungeon quests", "dungeonKey": "test",
            "dungeon": c.lua.table_from({"name": "Test Dungeon"}), "dungeonPhase": "run",
            "records": c.lua.table_from([
                c.lua.table_from({"id": 900, "title": "Second Boss Quest"}),
                c.lua.table_from({"id": 901, "title": "First Boss Quest"}),
            ]), "collectionGoals": c.lua.table_from({900: True, 901: True}),
        })
        route = ns.BuildDungeonRoute(guide, False, False)
        stops = [route.stops[i] for i in range(1, len(route.stops) + 1)]
        self.assertEqual([stop.id for stop in stops], [901, 900])
        self.assertEqual([stop.dungeonEncounterOrder for stop in stops], [1, 2])
        self.assertIn("Kill First Boss", stops[0].label)
        self.assertIn("First Boss Quest", stops[0].label)
        self.assertEqual(ns.GuideStepAction(stops[0]), "Kill First Boss — also completes First Boss Quest")
        self.assertEqual(stops[0].dungeonLootWatch[1].name, "Test Staff")
        self.assertEqual(stops[0].dungeonLootWatch[1].members, "You")


if __name__ == "__main__":
    unittest.main()
