"""Bounded party quest-history digests for the first party-plan slice."""
import unittest

from test_addon import Client


class PartyPlanDigestTests(unittest.TestCase):
    def test_capability_hello_marks_legacy_peers_and_new_peers(self):
        c = Client(quests=())
        c.receive('1|H')
        self.assertFalse(c.ns.members['Bob-TestRealm'].planSupport)
        c.receive('2|H|0.8.104|1')
        self.assertTrue(c.ns.members['Bob-TestRealm'].planSupport)
        self.assertEqual(c.ns.members['Bob-TestRealm'].version, '0.8.104')

    def test_digest_round_trip_packs_state_and_personal_skip_bits(self):
        c = Client(quests=())
        c.ns.active[10] = True
        c.ns.Completed = lambda quest_id: quest_id == 40
        c.ns.GuideQuestSkipped = lambda quest_id: quest_id == 20
        c.ns.CatalogueQuest = lambda quest_id: c.lua.table_from({'prerequisitesUnverified': True}) if quest_id == 30 else c.lua.table()
        c.ns.ObservedPickupAvailable = lambda quest_id: quest_id == 30
        c.ns.PartyPlanPinned = lambda quest_id: quest_id == 40
        ids = c.lua.table_from([10, 20, 30, 40])
        payload = c.ns.PartyPlanEncodeStates(ids)
        states, offers, skipped, pins = c.ns.PartyPlanDecodeStates(payload, 4)
        self.assertEqual([states[i] for i in range(1, 5)], [2, 1, 1, 3])
        self.assertEqual([offers[i] for i in range(1, 5)], [False, False, True, False])
        self.assertEqual([skipped[i] for i in range(1, 5)], [False, True, False, False])
        self.assertEqual([pins[i] for i in range(1, 5)], [False, False, False, True])

    def test_scope_and_digest_messages_are_validated_and_bound_to_scope(self):
        c = Client(quests=())
        sender = 'Bob-TestRealm'
        c.ns.members[sender] = c.lua.table()
        c.ns.Completed = lambda quest_id: quest_id == 40
        ids = c.lua.table_from([10, 20, 30, 40])
        digest = c.ns.PartyPlanEncodeStates(ids)
        scope_hash = c.ns.PartyPlanScopeHash(ids)
        result = c.ns.ReceivePartyPlanMessage(f'2|C|1|{scope_hash}|1|1|10,20,30,40', sender)
        self.assertTrue(result[0]); self.assertTrue(result[1])
        result = c.ns.ReceivePartyPlanMessage(f'2|S|1|{scope_hash}|24|1|1|{digest}', sender)
        self.assertTrue(result[0]); self.assertTrue(result[1])
        self.assertEqual(c.ns.members[sender].partyPlan.level, 24)
        self.assertEqual(c.ns.members[sender].partyPlan.states[4], 3)
        bad = c.ns.ReceivePartyPlanMessage('2|S|2|123|24|1|1|A', sender)
        self.assertFalse(bad[1])

    def test_sender_emits_bounded_scope_and_digest_only_in_party_mode(self):
        c = Client(quests=())
        sent = []
        c.ns.PartyFeaturesEnabled = lambda: True
        c.ns.QueueMessage = lambda message, *_: sent.append(message) or True
        c.ns.syncReady = True
        c.ns.partyNames = c.lua.table_from(['Bob-TestRealm'])
        c.ns.profile.level = 24
        c.ns.routeSelection = c.lua.table_from({'records': [{'id': 10}, {'id': 20}]}, recursive=True)
        c.ns.CataloguePrerequisiteIDs = lambda quest_id: c.lua.table()
        c.ns.CatalogueQuest = lambda quest_id: None
        c.ns.Completed = lambda quest_id: False
        c.ns.GuideQuestSkipped = lambda quest_id: False
        c.ns.ResetPartyPlanTraffic()
        self.assertTrue(c.ns.SendPartyPlanDigest(True))
        self.assertEqual(len(sent), 2)
        self.assertTrue(all(len(message) <= 255 for message in sent))
        self.assertIn('|C|', sent[0]); self.assertIn('|S|', sent[1])
        c.ns.PartyFeaturesEnabled = lambda: False
        self.assertFalse(c.ns.SendPartyPlanDigest(True))
        self.assertEqual(len(sent), 2)

    def test_tracker_summary_shows_a_gap_and_respects_a_peer_skip(self):
        c = Client(quests=())
        sender = 'Bob-TestRealm'
        c.ns.PartyFeaturesEnabled = lambda: True
        c.ns.partyNames = c.lua.table_from([sender])
        c.ns.MemberLabel = lambda name: 'Bob'
        c.ns.routeSelection = c.lua.table_from({'records': [{'id': 10, 'title': 'Test quest'}]}, recursive=True)
        c.ns.CataloguePrerequisiteIDs = lambda quest_id: c.lua.table()
        c.ns.CatalogueQuest = lambda quest_id: c.lua.table_from({'title': 'Test quest'})
        c.ns.Completed = lambda quest_id: False
        c.ns.active[10] = True
        c.ns.members[sender] = c.lua.table_from({'partyPlan': {'hash': c.ns.PartyPlanScopeHash(c.lua.table_from([10])),
            'states': {1: 0}, 'skipped': {1: False}}}, recursive=True)
        self.assertEqual(c.ns.PartyPlanMissingLine(), 'Missing vs party: waiting for matching quest data.')
        c.ns.members[sender].planSupport = False
        self.assertEqual(c.ns.PartyPlanMissingLine(), 'Missing vs party: update party addons to compare quest gaps.')
        c.ns.members[sender].planSupport = True
        c.ns.members[sender].partyPlan.states[1] = 1
        self.assertEqual(c.ns.PartyPlanMissingLine(), 'Missing vs party: Bob lacks Test quest')
        c.ns.members[sender].partyPlan.skipped[1] = True
        self.assertEqual(c.ns.PartyPlanMissingLine(), 'Missing vs party: no quest-log gaps in this guide.')

    def test_maximum_scope_digest_stays_within_party_message_limit(self):
        c = Client(quests=())
        sent = []
        c.ns.PartyFeaturesEnabled = lambda: True
        c.ns.QueueMessage = lambda message, *_: sent.append(message) or True
        c.ns.syncReady = True
        c.ns.partyNames = c.lua.table_from(['Bob-TestRealm'])
        c.ns.profile.level = 60
        roots = [{'id': 1000000000 + index} for index in range(512)]
        c.ns.routeSelection = c.lua.table_from({'records': roots}, recursive=True)
        c.ns.CataloguePrerequisiteIDs = lambda quest_id: c.lua.table()
        c.ns.CatalogueQuest = lambda quest_id: c.lua.table()
        c.ns.Completed = lambda quest_id: None
        c.ns.GuideQuestSkipped = lambda quest_id: False
        c.ns.PartyPlanPinned = lambda quest_id: False
        c.ns.ObservedPickupAvailable = lambda quest_id: False
        c.ns.ResetPartyPlanTraffic()
        self.assertTrue(c.ns.SendPartyPlanDigest(True))
        self.assertEqual(len(sent), 29 + 3)
        self.assertTrue(all(len(message) <= 255 for message in sent))


if __name__ == '__main__':
    unittest.main()
