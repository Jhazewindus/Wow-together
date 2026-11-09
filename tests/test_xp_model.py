"""Quest XP estimates are explicit and opt-in until Forever rewards are verified."""
import unittest
import json
from pathlib import Path

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
        c.ns.catalogue = c.lua.table_from({'quests': c.ns.catalogue.quests})
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

    def test_probe_reads_cached_step_metadata_without_replanning(self):
        c = self.client()
        c.ns.navigation.state.stop = c.lua.table_from({'id': 100, 'kind': 'a',
            'reasonCode': 'quest-pickup', 'label': 'Collect Old quest'})
        c.lua.execute('''
          local ns = ...
          ns.GuideDestinationDecision = function() error('probe recomputed destination policy') end
          ns.LevelingValue = function() error('probe entered quest policy') end
          ns.ChainValue = function() error('probe evaluated quest chains') end
          ns.ZoneExitProjection = function() error('probe recalculated XP projection') end
        ''', c.ns)
        c.ns.Diagnostics()  # Exact /wt probe entry point, with an active guide step.
        report = str(c.ns.diagnosticsText.text)
        self.assertIn('Destination reason: quest-pickup; Collect Old quest.', report)
        self.assertIn('cached route metadata only', report)

    def test_guide_xp_text_queues_one_record_per_timer_without_chain_planning(self):
        c = self.client()
        c.lua.execute('timers = {}; delays = {}')
        c.ns.QueueBackgroundRender = c.lua.eval('function() end')
        c.lua.execute('xpEligibilityCalls = 0')
        c.ns.LevelingValue = c.lua.eval('''function(id)
            xpEligibilityCalls = xpEligibilityCalls + 1
            return false, 'keep under Later'
        end''')
        guide = c.lua.table_from({'fullGuide': True, 'key': 'large', 'mode': 'bundle', 'rangeLow': 1,
            'records': c.lua.table_from([{'id': 100}, {'id': 101}, {'id': 102}])})
        self.assertEqual(c.ns.GuideXPText(guide), 'Calculating quest XP…')
        self.assertIsNone(guide.xpStartLevel)
        self.assertEqual(c.lua.globals().xpEligibilityCalls, 0)
        timers = c.lua.globals().timers
        self.assertEqual(len(timers), 1)
        c.lua.eval('table.remove')(timers, 1)()
        self.assertIsNone(guide.xpStartLevel)  # First callback yields before the first record calculation.
        calls = 1
        while len(timers):
            callback = timers[1]
            c.lua.eval('table.remove')(timers, 1)
            callback()
            calls += 1
            self.assertLess(calls, 10)
        self.assertGreater(calls, 3)
        self.assertEqual(guide.xpReward, 2200)
        self.assertEqual(c.lua.globals().xpEligibilityCalls, 1)
        self.assertIn('Quest XP estimate:', c.ns.GuideXPText(guide))

    def test_turnin_samples_calibrate_only_after_twenty_unrested_observations(self):
        c = self.client()
        c.ns.db.config.xpModel = True
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

    def test_observed_multiplier_is_opt_in(self):
        c = self.client()
        c.ns.profile.level = 21
        c.ns.char = c.lua.table_from({'xpSamples': c.lua.table_from([
            {'difference': 6, 'multiplier': 0.5, 'rested': False} for _ in range(20)], recursive=True)})
        self.assertEqual(c.ns.QuestXPMultiplier(6)[1], 'table')
        c.ns.db.config.xpModel = True
        self.assertEqual(c.ns.QuestXPMultiplier(6)[1], 'observed')

    def test_zone_projection_is_prepared_once_for_per_quest_policy(self):
        c = self.client()
        c.ns.profile.level = 29
        c.ns.profile.faction = 'Horde'
        c.ns.db.config.xpModel = True
        c.ns.xpCurve = c.lua.table_from({29: 100000, 30: 110000})
        records, quests = c.lua.table(), c.lua.table()
        for quest_id in range(1, 601):
            records[quest_id] = c.lua.table_from({'id': quest_id})
            quests[quest_id] = c.lua.table_from({'id': quest_id, 'title': 'Quest ' + str(quest_id),
                'level': 29, 'xp': 1000, 'side': 'Both'})
        c.ns.catalogue = c.lua.table_from({'quests': quests})
        c.lua.globals().ns = c.ns
        guide = c.lua.table_from({'key': 'zone:large', 'mode': 'zone', 'rangeLow': 21,
            'rangeHigh': 29, 'records': records}, recursive=True)
        c.ns.policyMetrics = c.lua.table_from({'zoneExitCalls': 0, 'zoneFinishingCalls': 0})
        elapsed, yields = c.lua.eval('''function(guide)
            local start, count = os.clock(), 0
            local job = coroutine.create(function() return ns.BuildLevelingRoute(guide, true, true) end)
            local okay, result
            repeat
                okay, result = coroutine.resume(job)
                if not okay then error(result) end
                if coroutine.status(job) ~= 'dead' then count = count + 1 end
            until coroutine.status(job) == 'dead'
            return os.clock() - start, count
        end''')(guide)
        self.assertLess(elapsed, 0.05)
        self.assertGreater(yields, 0)
        self.assertEqual(c.ns.policyMetrics.zoneExitCalls, 1)
        self.assertEqual(c.ns.policyMetrics.zoneFinishingCalls, 1)

    def test_zone_finishing_is_cached_per_query_and_invalidated_by_progress_revision(self):
        c = self.client()
        c.ns.profile.level = 29
        c.ns.db.config.xpModel = True
        c.ns.xpCurve = c.lua.table_from({29: 100000, 30: 110000})
        guide = c.lua.table_from({'key': 'zone:cached', 'mode': 'zone', 'rangeLow': 21,
            'rangeHigh': 29, 'records': [{'id': 101}]}, recursive=True)
        c.ns.policyMetrics = c.lua.table_from({'zoneExitCalls': 0, 'zoneFinishingCalls': 0})
        query = c.ns.NewQuestQuery()
        c.ns.PrepareGuidePolicy(guide, query)
        self.assertTrue(c.ns.GuideZoneFinishing(guide, c.ns.profile, None, query))
        self.assertTrue(c.ns.GuideZoneFinishing(guide, c.ns.profile, None, query))
        self.assertEqual(c.ns.policyMetrics.zoneFinishingCalls, 1)
        c.ns.guideProgressRevision = 1
        c.ns.PrepareGuidePolicy(guide, query)
        self.assertEqual(c.ns.policyMetrics.zoneFinishingCalls, 2)

    def test_zone_route_refresh_does_not_retain_policy_tables(self):
        c = self.client()
        c.ns.profile.level = 29
        c.ns.profile.faction = 'Horde'
        c.ns.db.config.xpModel = True
        c.ns.xpCurve = c.lua.table_from({29: 100000, 30: 110000})
        records, quests = c.lua.table(), c.lua.table()
        for quest_id in range(1, 601):
            records[quest_id] = c.lua.table_from({'id': quest_id})
            quests[quest_id] = c.lua.table_from({'id': quest_id, 'title': 'Quest ' + str(quest_id),
                'level': 29, 'xp': 1000, 'side': 'Both'})
        c.ns.catalogue = c.lua.table_from({'quests': quests})
        guide = c.lua.table_from({'key': 'zone:memory', 'mode': 'zone', 'rangeLow': 21,
            'rangeHigh': 29, 'records': records}, recursive=True)
        c.lua.globals().ns = c.ns
        growth = c.lua.eval('''function(guide)
            collectgarbage('collect')
            local before = collectgarbage('count')
            for _ = 1, 10 do ns.BuildLevelingRoute(guide, false, false) end
            collectgarbage('collect')
            return collectgarbage('count') - before
        end''')(guide)
        self.assertLess(growth, 2 * 1024)

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

    def test_xp_model_is_disabled_by_default(self):
        c = self.client()
        self.assertFalse(c.ns.Option('xpModel'))

    def test_catalogue_xp_and_followers_share_one_index_for_many_records(self):
        c = self.client()
        quests = c.lua.table()
        for quest_id in range(1, 502):
            quests[quest_id] = c.lua.table_from({'id': quest_id, 'title': 'Quest ' + str(quest_id),
                'level': 15, 'xp': 1000, 'side': 'Both'})
        quests[2].previousQuest = 1
        quests[3].prerequisiteAll = c.lua.table_from([1])
        quests[4].prerequisiteAny = c.lua.table_from([1])
        quests[5].series = c.lua.table_from([200, 501])
        c.ns.catalogue = c.lua.table_from({'quests': quests})
        c.ns.db.config.xpModel = True
        c.lua.globals().ns = c.ns
        c.lua.execute('''
            originalPairs = pairs
            cataloguePairCount = 0
            pairs = function(value)
                if value == ns.catalogue.quests then cataloguePairCount = cataloguePairCount + 1 end
                return originalPairs(value)
            end
        ''')
        query = c.ns.NewQuestQuery()
        for quest_id in range(1, 502):
            self.assertIsNotNone(c.ns.XPLevelingValue(quest_id, query)[0])
        self.assertEqual(c.lua.globals().cataloguePairCount, 1)
        followers = c.ns.CatalogueFollowers(1)
        for quest_id in (2, 3, 4): self.assertTrue(followers[quest_id])
        self.assertTrue(c.ns.CatalogueFollowers(200)[501])
        self.assertEqual(c.ns.CatalogueXPReference(15), 1000)
        self.assertEqual(len(c.ns.CatalogueQuestIDsAtLevel(15)), 501)

    def test_xp_leveling_memo_is_cleared_when_completion_revision_changes(self):
        c = self.client()
        c.ns.db.config.xpModel = True
        c.ns.questHistory = c.lua.table()
        c.ns.questHistoryCount = 0
        self.assertTrue(c.ns.XPLevelingValue(100)[0])
        c.ns.questHistory[102] = True
        c.ns.questHistoryCount = 1
        value, reason = c.ns.XPLevelingValue(100)
        self.assertFalse(value)
        self.assertIn('Later', reason)

    def test_diagnostics_with_xp_on_never_calls_planning_functions(self):
        c = self.client()
        c.ns.db.config.xpModel = True
        self.assertEqual(c.ns.XPDiagnosticsText(), 'on; not computed yet')
        c.lua.globals().ns = c.ns
        elapsed, calls, okay = c.lua.eval('''function()
            local names = {'GuideDestinationDecision', 'LevelingQuestEnabled', 'ChainValue',
                'ZoneExitProjection', 'XPLevelingValue'}
            local originals, count = {}, 0
            for _, name in ipairs(names) do
                originals[name] = ns[name]
                ns[name] = function() count = count + 1; error(name .. ' called by probe') end
            end
            local start = os.clock()
            local okay = pcall(ns.Diagnostics)
            local elapsed = os.clock() - start
            for _, name in ipairs(names) do ns[name] = originals[name] end
            return elapsed, count, okay
        end''')()
        self.assertTrue(okay)
        self.assertEqual(calls, 0)
        self.assertLess(elapsed, 0.02)

    def test_per_record_functions_do_not_scan_the_full_catalogue(self):
        root = Path(__file__).resolve().parents[1]
        for filename in ('GuideXP.lua', 'GuidePolicy.lua'):
            source = (root / 'WowTogether' / filename).read_text(encoding='utf-8')
            self.assertNotIn('pairs(ns.catalogue and ns.catalogue.quests or {})', source)
            self.assertNotIn('pairs(ns.catalogue.quests)', source)

    def test_old_solo_mode_gets_one_party_setting_notice_at_login(self):
        c = Client(quests=(), saved_variables={'config': {'soloMode': True, 'partyMode': 'never'}})
        c.ns.handlers.PLAYER_LOGIN()
        first = sum('Set Settings > Party mode to Ask me' in str(message)
            for message in c.lua.globals().logs.values())
        c.ns.handlers.PLAYER_LOGIN()
        second = sum('Set Settings > Party mode to Ask me' in str(message)
            for message in c.lua.globals().logs.values())
        self.assertEqual((first, second), (1, 1))
        self.assertEqual(c.ns.Option('partyMode'), 'never')

    def test_old_solo_mode_gets_one_party_setting_notice_at_login(self):
        c = Client(quests=(), saved_variables={'config': {'soloMode': True, 'partyMode': 'never'}})
        before = len(c.lua.globals().logs)
        c.ns.handlers.PLAYER_LOGIN()
        messages = [str(c.lua.globals().logs[index]) for index in range(before + 1, len(c.lua.globals().logs) + 1)]
        self.assertEqual(sum('Set Settings > Party mode to Ask me' in message for message in messages), 1)
        c.ns.handlers.PLAYER_LOGIN()
        self.assertEqual(sum('Set Settings > Party mode to Ask me' in str(message)
            for message in c.lua.globals().logs.values()), 1)
        self.assertEqual(c.ns.Option('partyMode'), 'never')

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
        c.ns.profile.level = 29
        self.assertFalse(c.ns.LevelingValue(1093)[0])
        reason = c.ns.LevelingValue(1093)[1]
        self.assertIn('below your pace', reason)
        stop = c.lua.table_from({'id': 1093, 'kind': 'a', 'title': 'Super Reaper 6000'})
        decision = c.ns.GuideDestinationDecision(stop, guide)
        self.assertIn(decision.code, ('chain-value', 'zone-finishing'))
        c.ns.profile.level = 28
        c.ns.active[1093] = 'Super Reaper 6000'
        self.assertFalse(c.ns.LevelingValue(1093)[0])  # Old in-log work stays out of the current route.
        self.assertTrue(c.ns.LevelingValue(1093)[1].startswith('in-log-low-value:'))
        c.ns.active[1093] = 'Super Reaper 6000'
        c.ns.NextZoneBaselineGuide = c.lua.eval("function() return {key='zone:needles', title='Thousand Needles', zone='Thousand Needles', mode='zone', rangeLow=25, rangeHigh=35, records={}} end")
        route = c.ns.BuildLevelingRoute(guide, False, False)
        self.assertEqual(route.stops[1].reasonCode, 'zone-exit')
        self.assertEqual(route.stops[1].label, 'Stonetalon Mountains finished — next: Thousand Needles (25–35)')
        guide.fullGuide = True
        guide.fixedPlan = c.lua.table()
        c.ns.ShowGuideQuestList(guide)
        frame = c.ns.guideQuestList
        frame.rows[1].OnMouseUp(frame.rows[1])  # Expand Also in this zone.
        low_value_row = next(row for row in frame.rows.values() if row.stop and row.stop.id == 1093)
        self.assertTrue(low_value_row.stop.inLogLowValue)
        self.assertIn('worth ~', low_value_row.stop.label)
        self.assertTrue(low_value_row.abandon.IsShown(low_value_row.abandon))
        self.assertTrue(low_value_row.keep.IsShown(low_value_row.keep))
        c.ns.active[1093] = None
        c.ns.NextZoneBaselineGuide = None
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
        self.assertTrue(c.ns.KeepLowValueQuest(1093))
        self.assertTrue(c.ns.ChainValue(1093).committed)

    def test_abandon_action_selects_and_abandons_only_after_explicit_call(self):
        c = self.client()
        c.ns.active[1093] = 'Old quest'
        c.lua.execute('''selectedQuest, abandonCalls = nil, 0
          C_QuestLog = {
            GetLogIndexForQuestID=function(id) return id == 1093 and 1 end,
            SetSelectedQuest=function(id) selectedQuest=id end,
            AbandonQuest=function() abandonCalls=abandonCalls+1 end,
          }''')
        self.assertEqual(c.lua.globals().abandonCalls, 0)
        self.assertTrue(c.ns.AbandonLowValueQuest(1093))
        self.assertEqual(c.lua.globals().selectedQuest, 1093)
        self.assertEqual(c.lua.globals().abandonCalls, 1)


if __name__ == '__main__':
    unittest.main()
