"""Active mob hints need unfinished objectives and respect public native vetoes.

These are Lua 5.1 host regressions with synthetic client answers. They do not
establish the Winter Wolf's live flag, drops, or the source of a beta tester's star.
"""
import unittest

from test_addon import Client
from test_057 import mob_client
from test_071 import giver_client


def wolf_client():
    c = Client(quests=(317,), use_catalogue=True,
               saved_variables={'config': {'soloMode': True}})
    c.lua.execute('''
      boarMeat=0
      C_QuestLog.GetQuestObjectives=function() return {
        {text='Chunk of Boar Meat: '..boarMeat..'/4', numFulfilled=boarMeat,
         numRequired=4, finished=false, type='item'},
        {text='Thick Bear Fur: 0/2', numFulfilled=0, numRequired=2,
         finished=false, type='item'}} end
      related=true
      C_QuestLog.UnitIsRelatedToActiveQuest=function() return related end
      plate=CreateFrame('Frame'); plate.namePlateUnitToken='nameplate1'
      C_NamePlate={GetNamePlateForUnit=function() return plate end,
                  GetNamePlates=function() return {plate} end}
      function UnitGUID() return 'Creature-0-1-2-3-1131-ABC' end
      function SetRaidTarget() error('Cosmetic hints must never set raid marks') end
    ''')
    c.ns.ReadProgress()
    c.ns.UpdateNPCHints()
    return c


class ActiveMobHintTests(unittest.TestCase):
    def test_winter_wolf_native_false_removes_broad_drop_hint_without_changing_quest(self):
        c = wolf_client()
        self.assertEqual(c.ns.npcHintCount, 1)
        hint = c.ns.npcHints['nameplate1']
        self.assertIn(317, hint.target.quests)
        c.lua.globals().related = False
        c.ns.UpdateNPCHints()
        self.assertFalse(hint.IsShown(hint))
        self.assertEqual(c.ns.npcHintCount, 0)
        self.assertEqual(c.ns.npcNativeRejected, 1)
        self.assertIsNotNone(c.ns.active[317])
        self.assertFalse(c.ns.Completed(317))
        self.assertFalse(c.ns.GuideQuestSkipped(317))
        c.ns.Diagnostics()
        self.assertIn('Local mob candidates rejected by public native quest flag: 1',
                      c.ns.diagnosticsText.text)

    def test_confirmed_pending_item_source_hides_when_only_other_item_remains(self):
        c = wolf_client()
        c.lua.globals().boarMeat = 4
        c.ns.ReadProgress(); c.ns.UpdateNPCHints()
        self.assertEqual(c.ns.npcHintCount, 0)
        self.assertFalse(c.ns.QuestProgressReady(c.ns.self, 317))

    def test_readable_objectives_reject_outdated_source_even_when_native_true(self):
        c = wolf_client()
        c.lua.execute('''C_QuestLog.GetQuestObjectives=function() return {
          {text='Changed Forever objective: 0/8', numFulfilled=0,
           numRequired=8, finished=false, type='monster'}} end''')
        c.ns.ReadProgress(); c.ns.UpdateNPCHints()
        self.assertEqual(c.ns.npcHintCount, 0)

    def test_missing_or_restricted_objective_list_requires_native_confirmation(self):
        for objective_list in ('nil', 'secret', '{{text=secret, finished=secret}}'):
            for native in ('nil', 'secret', 'false'):
                with self.subTest(objectives=objective_list, native=native):
                    c = wolf_client()
                    c.lua.execute('C_QuestLog.GetQuestObjectives=function() return '
                                  + objective_list + ' end; related=' + native)
                    c.ns.ReadProgress(); c.ns.UpdateNPCHints()
                    self.assertEqual(c.ns.npcHintCount, 0)

    def test_absent_and_failing_native_api_cannot_confirm_an_unmatched_source(self):
        for implementation in ('nil', 'function() error("restricted query") end'):
            with self.subTest(api=implementation):
                c = wolf_client()
                c.lua.execute('C_QuestLog.GetQuestObjectives=nil; '
                              'C_QuestLog.UnitIsRelatedToActiveQuest=' + implementation)
                c.ns.ReadProgress(); c.ns.UpdateNPCHints()
                self.assertEqual(c.ns.npcHintCount, 0)

    def test_matching_pending_public_objective_survives_unknown_native_result(self):
        for implementation in ('nil', 'function() return secret end',
                               'function() error("restricted query") end'):
            with self.subTest(api=implementation):
                c = mob_client()
                c.lua.execute('C_QuestLog.UnitIsRelatedToActiveQuest=' + implementation)
                c.ns.UpdateNPCHints()
                self.assertEqual(c.ns.npcHintCount, 2)

    def test_secret_counts_do_not_complete_matching_pending_collection(self):
        c = wolf_client()
        c.lua.execute('''C_QuestLog.GetQuestObjectives=function() return {
          {text='Chunk of Boar Meat', numFulfilled=secret, numRequired=secret,
           finished=secret, type='item'}} end; related=secret''')
        c.ns.ReadProgress(); c.ns.UpdateNPCHints()
        self.assertEqual(c.ns.npcHintCount, 1)

    def test_abandoning_and_marker_toggle_hide_owned_star_only(self):
        c = wolf_client(); hint = c.ns.npcHints['nameplate1']
        c.ns.SetOption('nameplateHints', False); c.ns.UpdateNPCHints()
        self.assertFalse(hint.IsShown(hint))
        self.assertTrue(c.ns.Option('npcHints'))
        c.ns.SetOption('nameplateHints', True); c.ns.UpdateNPCHints()
        self.assertTrue(hint.IsShown(hint))
        c.ns.active[317] = None
        c.ns.ReadProgress(); c.ns.UpdateNPCHints()
        self.assertFalse(hint.IsShown(hint))

    def test_native_veto_does_not_hide_friendly_guide_pickups_or_turnins(self):
        c = giver_client()
        c.lua.execute('C_QuestLog.UnitIsRelatedToActiveQuest=function() return false end')
        c.ns.UpdateNPCHints()
        self.assertEqual(c.ns.npcHints['nameplate1'].target.kind, 'a')
        self.assertEqual(c.ns.npcHintCount, 1)
        c.ns.selectedRoute = None
        q = c.ns.CatalogueQuest(900)
        q.ends[1].entityID = 123
        c.ns.active[900] = 'Ready to return'
        c.ns.readyToTurnIn[900] = True
        c.ns.UpdateNPCHints()
        self.assertEqual(c.ns.npcHints['nameplate1'].target.kind, 't')
        self.assertEqual(c.ns.npcHintCount, 1)

    def test_native_quest_getter_is_not_called_during_combat(self):
        c = mob_client()
        c.lua.execute('''combat=true; nativeCalls=0
          C_QuestLog.UnitIsRelatedToActiveQuest=function()
            nativeCalls=nativeCalls+1; error('combat query') end''')
        c.ns.UpdateNPCHints()
        self.assertTrue(c.ns.npcHintsPending)
        self.assertEqual(c.lua.globals().nativeCalls, 0)

    def test_known_pending_peer_objective_survives_local_native_false(self):
        c = mob_client()
        c.lua.globals().grouped = True
        c.unit_names({'player': ['Alice', 'TestRealm'],
                      'party1': ['Bob', 'TestRealm']})
        c.receive('1|S|5|1|1|900')
        c.receive('1|P|12|2|501|Test Coast')
        member = c.ns.members['Bob-TestRealm']
        member.progress = c.lua.table_from({900: {
            'activeRevision': member.activeRevision,
            'objectives': [{'text': 'Test Hunters killed', 'have': 0, 'need': 7,
                            'finished': False}]}}, recursive=True)
        c.lua.execute('C_QuestLog.UnitIsRelatedToActiveQuest=function() return false end')
        c.ns.UpdateNPCHints()
        self.assertEqual(c.ns.npcHintCount, 1)
        self.assertTrue(c.ns.npcHints['nameplate1'].IsShown(c.ns.npcHints['nameplate1']))
        self.assertFalse(c.ns.npcHints['nameplate2'].IsShown(c.ns.npcHints['nameplate2']))
        member.progress[900].objectives[1].have = 7
        c.ns.UpdateNPCHints()
        self.assertEqual(c.ns.npcHintCount, 0)

    def test_native_true_cannot_mark_unknown_or_future_quest_mobs(self):
        c = wolf_client()
        c.lua.execute("function UnitGUID() return 'Creature-0-1-2-3-999999-ABC' end")
        c.ns.UpdateNPCHints()
        self.assertEqual(c.ns.npcHintCount, 0)
        c.lua.execute("function UnitGUID() return 'Creature-0-1-2-3-1131-ABC' end")
        c.ns.active[317] = None
        c.ns.UpdateNPCHints()
        self.assertEqual(c.ns.npcHintCount, 0)


if __name__ == '__main__':
    unittest.main()
