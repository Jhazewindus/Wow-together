"""Objective-area learning stays build-scoped and only samples local progress."""
import unittest

from test_addon import Client


class ObjectiveLearningTests(unittest.TestCase):
    def learning_client(self):
        client = Client(quests=(777,))
        client.lua.execute(r'''
          playerMapX, objectiveHave, taxi = 0.20, 0, false
          function UnitOnTaxi() return taxi end
          function UnitIsDeadOrGhost() return false end
          function IsInInstance() return false end
          C_Map = {
            GetBestMapForUnit=function() return 501 end,
            GetMapWorldSize=function() return 5000,3500 end,
            GetPlayerMapPosition=function() return {GetXY=function() return playerMapX,0.3 end} end,
          }
          C_QuestLog.GetQuestObjectives=function()
            return {{type='monster', text='Forest Wolf', numFulfilled=objectiveHave,
              numRequired=3, finished=objectiveHave >= 3}}
          end
        ''')
        client.ns.ReadProgress()  # Baseline before any counter increase.
        return client

    def test_three_local_counter_ticks_cluster_into_one_usable_area(self):
        c = self.learning_client()
        for have, x in ((1, 0.20), (2, 0.205), (3, 0.21)):
            c.lua.globals().objectiveHave = have
            c.lua.globals().playerMapX = x
            c.ns.ReadProgress()
            c.ns.RecordObjectiveProgress()
        point = c.ns.LearnedObjectivePoint(777, 1, False)
        self.assertEqual(point.mapID, 501)
        self.assertEqual(point.n, 3)
        self.assertTrue(point.observers[str(c.ns.self)])
        self.assertAlmostEqual(point.x, 0.205, places=5)

    def test_taxi_counter_increase_is_not_recorded(self):
        c = self.learning_client()
        c.lua.globals().taxi = True
        c.lua.globals().objectiveHave = 1
        c.ns.ReadProgress()
        c.ns.RecordObjectiveProgress()
        self.assertIsNone(c.ns.LearnedObjectivePoint(777, 1, True))

    def test_shared_objective_packet_is_deduplicated_and_legacy_offer_kind_survives(self):
        c = self.learning_client()
        packet = '1|O|70009|777|1|501|0.20000,0.30000|1'
        handled, accepted = c.ns.ReceiveObjectiveMessage(packet, 'Bob-TestRealm')
        self.assertTrue(handled)
        self.assertTrue(accepted)
        handled, accepted, reason = c.ns.ReceiveObjectiveMessage(packet, 'Bob-TestRealm')
        self.assertTrue(handled)
        self.assertFalse(accepted)
        self.assertEqual(reason, 'duplicate objective message')
        # Legacy 1|O offer snapshots do not match the longer coordinate packet.
        self.assertFalse(c.ns.ReceiveObjectiveMessage('1|O|2|1|1|1', 'Bob-TestRealm'))
        point = c.ns.LearnedObjectivePoint(777, 1, True)
        self.assertEqual(point.n, 1)


if __name__ == '__main__':
    unittest.main()
