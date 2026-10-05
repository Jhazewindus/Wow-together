"""Public offer/progression capture and copyable exports; no live beta claims."""
import json
import unittest
from test_addon import Client
from test_062 import client


def setup():
    c = client()
    for id in (900, 901):
        c.ns.catalogue.quests[id].starts[1].entityID = 123
    c.lua.execute("function UnitGUID() return 'Creature-0-1-2-3-123-ABC' end")
    return c


def offer(c, ids, complete=True):
    c.ns.RecordNPCOfferAvailability(c.lua.table_from([{'questID': id} for id in ids], recursive=True), complete)


def exported(c):
    return json.loads(c.ns.ExportQuestResearch())


class QuestResearchTests(unittest.TestCase):
    def test_offer_before_and_after_hand_in_records_evidence_without_inventing_a_dependency(self):
        c = setup()
        offer(c, [900])
        c.ns.handlers.QUEST_TURNED_IN(900)
        c.lua.globals().finished[900] = True
        offer(c, [901])
        data = exported(c)
        self.assertEqual(data['format'], 'wow-together-quest-research')
        before, turn_in, after = data['events']
        self.assertEqual([e['event'] for e in data['events']], ['offers', 'turn-in', 'offers'])
        self.assertEqual(before['npcID'], 123)
        self.assertTrue(before['completeList'])
        self.assertEqual(before['offered'], [900])
        self.assertIn(900, before['notCompleted'])
        self.assertIn(901, before['notCompleted'])
        self.assertIn(900, turn_in['completed'])  # The event itself proves hand-in, even before flag refresh.
        self.assertEqual(after['offered'], [901])
        self.assertIn(900, after['completed'])
        self.assertNotIn('inferredPrerequisite', after)

    def test_single_dialog_never_claims_a_complete_npc_list(self):
        c = setup(); offer(c, [901], complete=False)
        data = exported(c)['events'][0]
        self.assertFalse(data['completeList'])
        self.assertEqual(data['offered'], [901])

    def test_opening_one_detail_keeps_previously_confirmed_absence_in_the_same_context(self):
        c = setup(); offer(c, [900])
        self.assertFalse(c.ns.ObservedPickupAvailable(901))
        offer(c, [900], complete=False)
        self.assertFalse(c.ns.ObservedPickupAvailable(901))
        self.assertFalse(exported(c)['events'][-1]['completeList'])

    def test_recommended_pickups_missing_from_a_full_offer_list_are_identified(self):
        c = setup()
        c.ns.selectedRoute = c.lua.table_from({'stops': [
            {'id': 900, 'kind': 'a', 'memberKey': c.ns.self},
            {'id': 901, 'kind': 'a', 'memberKey': 'Bob-TestRealm'}]}, recursive=True)
        offer(c, [])
        record = exported(c)['events'][0]
        self.assertEqual(record['plannedPickups'], [900])
        self.assertEqual(record['missingPlannedPickups'], [900])
        offer(c, [900], complete=False)
        self.assertEqual(exported(c)['events'][-1]['missingPlannedPickups'], [])

    def test_acceptance_is_distinct_from_completion_and_invalid_event_ids_are_ignored(self):
        c = setup(); c.ns.handlers.QUEST_ACCEPTED(2, 900)
        record = exported(c)['events'][0]
        self.assertEqual(record['event'], 'accept')
        self.assertEqual(record['questID'], 900)
        self.assertIn(900, record['active'])
        self.assertIn(900, record['notCompleted'])
        for id in (None, 0, c.lua.globals().secret):
            c.ns.handlers.QUEST_ACCEPTED(2, id)
        self.assertEqual(len(exported(c)['events']), 1)

    def test_restricted_history_is_unknown_and_secret_npc_ids_are_not_logged(self):
        c = setup()
        c.lua.execute('C_QuestLog.IsQuestFlaggedCompleted=function() return secret end')
        offer(c, [900])
        record = exported(c)['events'][0]
        self.assertEqual(record['completed'], [])
        self.assertEqual(record['notCompleted'], [])
        self.assertIn(900, record['historyUnknown'])
        c.lua.execute('function UnitGUID() return secret end')
        offer(c, [901])
        self.assertEqual(len(exported(c)['events']), 1)

    def test_repeated_identical_offers_are_coalesced_and_capture_is_optional(self):
        c = setup(); offer(c, [900]); offer(c, [900])
        self.assertEqual(len(exported(c)['events']), 1)
        c.ns.SetOption('recordQuestData', False)
        c.ns.handlers.QUEST_TURNED_IN(900); offer(c, [901])
        self.assertEqual(len(exported(c)['events']), 1)

    def test_pause_and_resume_mark_a_new_capture_segment(self):
        c = setup(); offer(c, [900])
        first = exported(c)['events'][0]['session']
        c.ns.SetOption('recordQuestData', False)
        c.ns.handlers.QUEST_TURNED_IN(900)
        c.ns.SetOption('recordQuestData', True); offer(c, [900])
        data = exported(c)
        self.assertEqual(len(data['events']), 2)
        self.assertGreater(data['events'][1]['session'], first)

    def test_export_is_bounded_and_reports_replaced_observations(self):
        c = setup()
        for id in range(1000, 1305):
            c.ns.RecordQuestResearch('turn-in', c.lua.table_from({'questID': id}))
        data = exported(c)
        self.assertEqual(data['capacity'], 300)
        self.assertEqual(len(data['events']), 300)
        self.assertEqual(data['dropped'], 5)
        self.assertEqual(data['events'][0]['sequence'], 6)
        self.assertEqual(data['events'][-1]['sequence'], 305)

    def test_export_includes_build_and_confounding_changes_without_character_names(self):
        c = setup(); offer(c, [900])
        c.ns.handlers.PLAYER_LEVEL_UP(13)
        c.ns.handlers.UPDATE_FACTION()
        data = exported(c)
        self.assertEqual(data['events'][0]['interface'], 16001)
        self.assertEqual(data['events'][0]['build'], '70009')
        self.assertEqual(data['events'][1]['level'], 13)
        self.assertEqual(data['events'][2]['event'], 'reputation')
        self.assertEqual(data['events'][2]['reputationRevision'], 1)
        text = c.ns.ExportQuestResearch()
        self.assertNotIn('Alice', text)
        self.assertNotIn('Bob', text)
        self.assertNotIn('TestRealm', text)

    def test_current_character_export_persists_across_reload_and_is_separate_from_friends(self):
        c = setup(); offer(c, [900])
        saved = {'questResearch': {c.ns.self: dict(c.ns.db.questResearch[c.ns.self])}}
        state = saved['questResearch'][c.ns.self]
        state['events'] = exported(c)['events']
        restored = Client(quests=(), saved_variables=saved)
        data = exported(restored)
        self.assertEqual(len(data['events']), 1)
        self.assertEqual(data['events'][0]['offered'], [900])
        self.assertEqual(restored.ns.db.questResearch[restored.ns.self].session, 2)
        friend = Client(name='Bob', peer='Alice', quests=(), saved_variables=saved)
        self.assertEqual(exported(friend)['events'], [])

    def test_json_escaping_and_report_refresh_preserve_export_mode(self):
        c = setup()
        c.lua.globals().customBuild = '702"\\\n05'
        c.lua.execute("function GetBuildInfo() return '1.60.1', customBuild, 'test', 16001 end")
        offer(c, [900])
        self.assertEqual(exported(c)['events'][0]['build'], '702"\\\n05')
        c.ns.settings.researchExport.OnClick()
        self.assertIn('Quest data export', c.ns.diagnosticsWindow.title.text)
        self.assertEqual(json.loads(c.ns.diagnosticsText.text)['schema'], 1)
        c.ns.reportRefresh()
        self.assertEqual(json.loads(c.ns.diagnosticsText.text)['schema'], 1)
        c.ns.Diagnostics()
        self.assertIn('Diagnostics', c.ns.diagnosticsWindow.title.text)
        self.assertIn('Quest data recording: on; 1/300', c.ns.diagnosticsText.text)


if __name__ == '__main__':
    unittest.main()
