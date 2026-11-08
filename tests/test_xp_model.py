"""Quest XP estimates are explicit and opt-in until Forever rewards are verified."""
import unittest

from test_addon import Client


class XPModelTests(unittest.TestCase):
    def client(self):
        c = Client(quests=())
        c.lua.execute('function UnitLevel() return 15 end; function UnitXP() return 500 end; '
                      'function UnitXPMax() return 1500 end; function GetXPExhaustion() return 300 end')
        c.ns.ReadProfile()
        c.ns.profile.level = 15
        c.ns.profile.faction = 'Horde'
        c.ns.catalogue = c.lua.table_from({'quests': {
            100: {'id': 100, 'title': 'Old quest', 'level': 5, 'xp': 1000, 'side': 'Both'},
            101: {'id': 101, 'title': 'Yellow quest', 'level': 15, 'xp': 1000, 'side': 'Both'},
            102: {'id': 102, 'title': 'Next quest', 'level': 18, 'xp': 1200, 'previousQuest': 100, 'side': 'Both'},
        }}, recursive=True)
        return c

    def test_state_and_classic_overlevel_table(self):
        c = self.client()
        state = c.ns.XPState()
        self.assertEqual((state.level, state.xp, state.xpMax, state.rested, state.toNextLevel), (15, 500, 1500, 300, 1000))
        self.assertEqual(c.ns.QuestXP(100, 15), 100)  # ten levels below: 10%
        self.assertEqual(c.ns.QuestXP(100, 19), 100)  # still at the 10% floor
        self.assertEqual(c.ns.QuestXP(101, 15), 1000)

    def test_xp_model_keeps_grey_work_later_but_accepts_useful_chain_unlock(self):
        c = self.client()
        c.ns.db.config.xpModel = True
        result, reason = c.ns.XPLevelingValue(100)
        self.assertTrue(result)
        self.assertIn('Next quest', reason)
        c.ns.catalogue.quests[102].previousQuest = None
        result, reason = c.ns.XPLevelingValue(100)
        self.assertFalse(result)
        self.assertIn('Later', reason)

    def test_zone_projection_reports_exit_level_and_zone_remaining(self):
        c = self.client()
        c.ns.xpCurve = c.lua.table_from({15: 1500, 16: 1600})
        guide = c.lua.table_from({'mode': 'zone', 'key': 'test', 'rangeLow': 10, 'rangeHigh': 15,
                                  'records': [{'id': 101}]}, recursive=True)
        xp = c.ns.ZoneXPRemaining(guide, c.ns.profile)
        self.assertEqual(xp, (1000, 0))
        projection = c.ns.ZoneExitProjection(guide, c.ns.profile)
        self.assertEqual((projection.level, projection.xp), (16, 0))


if __name__ == '__main__':
    unittest.main()
