"""Quest XP estimates are explicit and opt-in until Forever rewards are verified."""
import unittest
import json

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

    def test_turnin_samples_calibrate_only_after_twenty_unrested_observations(self):
        c = self.client()
        c.ns.profile.level = 21
        c.ns.char = c.lua.table_from({})
        c.lua.execute('function GetXPExhaustion() return 0 end')
        c.ns.catalogue.quests[100].level = 15
        c.ns.catalogue.quests[100].xp = 1000
        self.assertTrue(c.ns.RecordQuestXPSample(100, 500))
        self.assertEqual(c.ns.QuestXPMultiplier(6)[0], 0.8)
        for _ in range(19):
            self.assertTrue(c.ns.RecordQuestXPSample(100, 600))
        self.assertEqual(c.ns.QuestXPMultiplier(6)[0], 0.6)
        self.assertEqual(c.ns.QuestXPMultiplier(6)[1], 'observed')
        self.assertEqual(c.ns.QuestXP(100, 21), 600)
        self.assertEqual(len(c.ns.char.xpSamples), 20)

    def test_xp_sample_history_is_bounded_to_five_hundred(self):
        c = self.client()
        c.ns.profile.level = 15
        samples = c.lua.table()
        for i in range(1, 501): samples[i] = c.lua.table_from({'questID': 1})
        c.ns.char = c.lua.table_from({'xpSamples': samples})
        self.assertTrue(c.ns.RecordQuestXPSample(100, 500))
        self.assertEqual(len(c.ns.char.xpSamples), 500)

    def test_research_export_contains_anonymous_xp_sample_events(self):
        c = self.client()
        c.ns.char = c.lua.table_from({})
        self.assertTrue(c.ns.RecordQuestXPSample(100, 500))
        exported = json.loads(c.ns.ExportQuestResearch())
        sample = exported['events'][-1]
        self.assertEqual(sample['event'], 'xp-sample')
        self.assertEqual((sample['questID'], sample['questLevel'], sample['playerLevel'], sample['xpReward']), (100, 5, 15, 500))
        self.assertTrue(sample['rested'])

    def test_quest_turned_in_handler_records_the_xp_reward_argument(self):
        c = self.client()
        c.ns.char = c.lua.table_from({})
        c.lua.execute('function GetXPExhaustion() return 0 end')
        c.ns.handlers.QUEST_TURNED_IN(100, 500)
        self.assertEqual(len(c.ns.char.xpSamples), 1)
        self.assertEqual(c.ns.char.xpSamples[1].xpReward, 500)

    def test_stonetalon_chain_is_valued_across_levels_24_28_and_30(self):
        c = self.client()
        c.ns.catalogue = c.lua.table_from({'quests': {
            1093: {'id': 1093, 'title': 'Super Reaper 6000', 'level': 21, 'xp': 1650, 'side': 'Both', 'previousQuest': None},
            1094: {'id': 1094, 'title': 'Further Instructions', 'level': 21, 'xp': 830, 'side': 'Both', 'previousQuest': 1093},
            1095: {'id': 1095, 'title': 'Further Instructions II', 'level': 27, 'xp': 1100, 'side': 'Both', 'previousQuest': 1094},
            1096: {'id': 1096, 'title': 'Gerenzo Wrenchwhistle', 'level': 27, 'xp': 2200, 'side': 'Both', 'previousQuest': 1095},
            2001: {'id': 2001, 'title': 'Baseline A', 'level': 24, 'xp': 1200, 'side': 'Both'},
            2002: {'id': 2002, 'title': 'Baseline B', 'level': 24, 'xp': 1200, 'side': 'Both'},
            2003: {'id': 2003, 'title': 'Baseline C', 'level': 24, 'xp': 1200, 'side': 'Both'},
        }}, recursive=True)
        c.ns.profile.faction = 'Horde'
        c.ns.profile.level = 24
        guide = c.lua.table_from({'key': 'zone:stonetalon', 'mode': 'zone', 'zone': 'Stonetalon Mountains',
                                 'rangeLow': 21, 'rangeHigh': 29, 'records': [{'id': 1093}]}, recursive=True)
        c.ns.routeSelection = guide
        self.assertTrue(c.ns.LevelingValue(1093))
        at_24 = c.ns.ChainValue(1093)
        self.assertTrue(at_24.included)
        self.assertEqual((at_24.totalSteps, at_24.completedSteps), (4, 0))
        c.ns.profile.level = 28
        at_28 = c.ns.ChainValue(1093)
        self.assertFalse(at_28.included)
        self.assertIn('below your pace', at_28.reason)
        self.assertFalse(c.ns.LevelingValue(1093)[0])
        self.assertTrue(c.ns.GuideZoneFinishing(guide))
        c.ns.active[1093] = 'Super Reaper 6000'
        self.assertTrue(c.ns.LevelingValue(1093)[0])  # Zone finish retains work already in the log.
        c.ns.active[1093] = None
        c.ns.profile.level = 30
        self.assertFalse(c.ns.ChainValue(1093).included)
        self.assertFalse(c.ns.LevelingValue(1093)[0])
        c.ns.profile.level = 40
        c.lua.globals().finished[1093] = True
        c.lua.globals().finished[1094] = True
        self.assertFalse(c.ns.ChainValue(1093).committed)  # Completed work cannot commit a grey endpoint.
        self.assertTrue(c.ns.SetGuideEfficiencyMode(guide, 'complete'))
        self.assertEqual(c.ns.GuideEfficiencyMode(guide), 'complete')
        self.assertTrue(c.ns.LevelingValue(1093))

    def test_two_completed_chain_steps_commit_the_remainder(self):
        c = self.client()
        c.ns.catalogue = c.lua.table_from({'quests': {
            1093: {'id': 1093, 'title': 'Super Reaper 6000', 'level': 21, 'xp': 1650, 'side': 'Both'},
            1094: {'id': 1094, 'title': 'Further Instructions', 'level': 21, 'xp': 830, 'side': 'Both', 'previousQuest': 1093},
            1095: {'id': 1095, 'title': 'Further Instructions II', 'level': 27, 'xp': 1100, 'side': 'Both', 'previousQuest': 1094},
            1096: {'id': 1096, 'title': 'Gerenzo Wrenchwhistle', 'level': 27, 'xp': 2200, 'side': 'Both', 'previousQuest': 1095},
        }}, recursive=True)
        c.ns.profile.faction = 'Horde'
        c.ns.profile.level = 28
        c.lua.globals().finished[1093] = True
        c.lua.globals().finished[1094] = True
        chain = c.ns.ChainValue(1093)
        self.assertTrue(chain.committed)
        self.assertEqual((chain.completedSteps, chain.remainingSteps), (2, 2))
        self.assertIn('Finishing this chain: 2 quests left', chain.reason)
        c.ns.ForgetQuestCompletion(1094)
        c.lua.globals().finished[1094] = False
        chain = c.ns.ChainValue(1093)
        self.assertFalse(chain.committed)
        self.assertEqual(chain.completedSteps, 1)


if __name__ == '__main__':
    unittest.main()
