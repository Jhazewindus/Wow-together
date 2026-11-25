"""Raid entrances are captured from the last outdoor position, per build."""
import json
import unittest

from test_addon import Client


class InstanceObservationTests(unittest.TestCase):
    def test_entry_saves_personal_build_scoped_observation_and_exports_it(self):
        c = Client(quests=(), default_guide=True)
        c.lua.execute('''
            inInstance = false
            IsInInstance = function() return inInstance, inInstance and "raid" or "none" end
            GetServerTime = function() return 123456 end
            C_Map = {
                GetBestMapForUnit = function() return 1431 end,
                GetPlayerMapPosition = function() return {GetXY=function() return 0.42, 0.68 end} end,
            }
            GetInstanceInfo = function()
                return "Onyxia's Lair", "raid", 3, "40 Player", 40, 0, false, 249
            end
        ''')
        frame = c.ns.instanceObservationFrame
        frame.OnUpdate(frame, 0.6)
        c.lua.globals().inInstance = True
        c.ns.handlers.PLAYER_ENTERING_WORLD()

        row = c.lua.globals().WowTogetherCharDB.instanceEntrances["70009"]["249|Onyxia's Lair"]
        self.assertEqual((row.name, row.instanceID, row.build, row.mapID),
                         ("Onyxia's Lair", 249, "70009", 1431))
        self.assertEqual((row.x, row.y, row.observedAt), (0.42, 0.68, 123456))
        exported = json.loads(c.ns.ExportQuestResearch())
        entrance = next(event for event in exported["events"] if event["event"] == "instance-entrance")
        self.assertEqual(entrance["name"], "Onyxia's Lair")
        self.assertEqual(entrance["instanceID"], 249)
        self.assertEqual((entrance["mapID"], entrance["x"], entrance["y"]), (1431, 0.42, 0.68))

    def test_entry_without_a_cached_outdoor_position_does_not_guess(self):
        c = Client(quests=(), default_guide=True)
        c.lua.execute('''
            IsInInstance = function() return true, "raid" end
            GetInstanceInfo = function() return "Hyjal Summit", "raid", 3, "40 Player", 40, 0, false, 409 end
        ''')
        c.ns.handlers.PLAYER_ENTERING_WORLD()
        rows = c.lua.globals().WowTogetherCharDB.instanceEntrances["70009"]
        self.assertTrue(rows is None or len(rows) == 0)
        self.assertEqual(len(c.ns.InstanceEntranceObservations()), 0)

    def test_observations_are_exported_only_for_current_build(self):
        c = Client(quests=(), default_guide=True,
                   saved_character={"schema": 2, "instanceEntrances": {
                       "70009": {"249|Onyxia's Lair": {"name": "Onyxia's Lair", "instanceID": 249,
                           "build": "70009", "mapID": 1431, "x": 0.4, "y": 0.6,
                           "source": "observed"}},
                       "70010": {"409|Hyjal Summit": {"name": "Hyjal Summit", "instanceID": 409,
                           "build": "70010", "mapID": 1443, "x": 0.3, "y": 0.7,
                           "source": "observed"}},
                   }})
        self.assertEqual(len(c.ns.InstanceEntranceObservations()), 1)
        self.assertEqual(c.ns.InstanceEntranceObservations()[1].name, "Onyxia's Lair")


if __name__ == "__main__":
    unittest.main()
