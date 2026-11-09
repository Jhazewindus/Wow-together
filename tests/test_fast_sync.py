import random
import unittest

from test_addon import Client


class FastSyncTests(unittest.TestCase):
    def client_with_catalogue(self, count):
        client = Client(quests=())
        quests = client.lua.table()
        for quest_id in range(1, count + 1):
            quests[quest_id] = client.lua.table_from({'id': quest_id, 'title': f'Quest {quest_id}'})
        client.ns.catalogue = client.lua.table_from({'captured': 'test-capture', 'quests': quests})
        self.assertTrue(client.ns.SyncStateInitialize())
        return client

    def test_two_bit_catalogue_codec_round_trips_5333_states_and_chunks_fit(self):
        client = self.client_with_catalogue(5333)
        rng = random.Random(11)
        states = [rng.randrange(4) for _ in range(5333)]
        payload = client.ns.SyncStateEncode(client.lua.table_from(states))
        decoded = client.ns.SyncStateDecode(payload, len(states))
        self.assertEqual([decoded[i] for i in range(1, len(states) + 1)], states)
        packets = [f'1|B|9|{part}|8|' + payload[(part - 1) * 225:part * 225]
                   for part in range(1, 9)]
        self.assertTrue(all(len(packet) <= 255 for packet in packets))
        self.assertEqual(len(payload), 1780)

    def test_full_state_sends_eight_atomic_background_chunks(self):
        client = self.client_with_catalogue(5333)
        messages = []
        client.ns.QueueMessages = lambda rows, lane: messages.extend((rows[i], lane) for i in range(1, len(rows) + 1)) or True
        client.ns.members['Bob-TestRealm'] = client.lua.table_from({
            'stateHashFromPeer': client.ns.SyncStateCatalogueHash(),
            'stateAck': 0,
        })
        self.assertTrue(client.ns.SyncStateSendPeer('Bob-TestRealm'))
        self.assertEqual(len(messages), 8)
        self.assertTrue(all(lane == 'background' and message.startswith('1|B|') and len(message) <= 255
                            for message, lane in messages))
        self.assertEqual(client.ns.members['Bob-TestRealm'].sentRev, 0)

    def test_retransmitted_full_state_parts_are_idempotent(self):
        client = self.client_with_catalogue(6)
        hash_value = client.ns.SyncStateCatalogueHash()
        client.ns.members['Bob-TestRealm'] = client.lua.table_from({'catalogueMismatch': False})
        payload = client.ns.SyncStateEncode(client.lua.table_from([0] * 6))
        first, second = payload[:2], payload[2:]
        one = client.ns.SyncStateAssembly('Bob-TestRealm', 4, 1, 2, first)
        duplicate = client.ns.SyncStateAssembly('Bob-TestRealm', 4, 1, 2, first)
        final = client.ns.SyncStateAssembly('Bob-TestRealm', 4, 2, 2, second)
        self.assertEqual(tuple(one), (True, False))
        self.assertEqual(tuple(duplicate), (True, False))
        self.assertTrue(final[0] and final[1])
        self.assertEqual(client.ns.members['Bob-TestRealm'].stateHash, hash_value)

    def test_full_history_supersedes_older_fast_scope_snapshot(self):
        client = self.client_with_catalogue(6)
        key = 'Bob-TestRealm'
        ids = client.lua.table_from([1])
        scoped = client.ns.SyncStateEncode(client.lua.table_from([1]))
        self.assertTrue(client.ns.SyncStateApplyScope(key, 2, client.ns.SyncStateScopeHash(ids), ids, scoped))
        states = client.lua.table_from([3, 0, 0, 0, 0, 0])
        full = client.ns.SyncStateEncode(states)
        self.assertTrue(client.ns.SyncStateApplyFull(key, 3, full))
        self.assertIsNone(client.ns.members[key].scopeState)
        self.assertEqual(client.ns.SyncStateForQuest(key, 1), 3)

    def test_transport_prioritizes_control_and_now_lanes_and_paces_background(self):
        client = Client(quests=())
        client.drain()
        client.lua.execute('delays = {}')
        background = '1|D|1|900|1|1|0,0'
        current = '1|S|1|1|1|900'
        control = '1|H|probe'
        self.assertTrue(client.ns.QueueMessage(background, 'background'))
        self.assertTrue(client.ns.QueueMessage(current, 'now'))
        self.assertTrue(client.ns.QueueMessage(control, 'control'))
        messages = [message for _, message, _ in client.drain()]
        sent = [message for message in messages if message in {background, current, control}]
        self.assertEqual(sent, [control, current, background])
        delays = [client.lua.globals().delays[i] for i in range(1, len(client.lua.globals().delays) + 1)]
        self.assertTrue(any(delay >= .24 for delay in delays))

    def test_throttle_halves_budget_and_idle_time_recovers_to_ceiling(self):
        client = Client(quests=())
        client.drain()
        client.lua.execute('''
        fakeTime = 0
        function GetTime() return fakeTime end
        C_Timer.After = function(delay, fn)
            timers[#timers + 1] = fn; delays[#delays + 1] = delay; fakeTime = fakeTime + delay
        end
        sendResults = {8, 8, 8, 8, 7}
        ''')
        self.assertTrue(client.ns.QueueMessage('1|S|1|1|1|900', 'now'))
        client.drain()
        self.assertEqual(client.ns.TransportState().budget, 75)
        client.lua.execute('local ns=...; C_Timer.After(150, function() ns.QueueMessage("1|S|2|1|1|900", "now") end)', client.ns)
        client.drain()
        self.assertEqual(client.ns.TransportState().budget, 600)

    def test_multi_packet_delta_accepts_same_revision_and_updates_peer_state(self):
        client = self.client_with_catalogue(60)
        hash_value = client.ns.SyncStateCatalogueHash()
        zero = client.ns.SyncStateEncode(client.lua.table_from([0] * 60))
        client.ns.members['Bob-TestRealm'] = client.lua.table_from({
            'stateHashFromPeer': hash_value, 'stateHash': hash_value, 'stateAck': 0, 'sentHash': hash_value,
        })
        self.assertTrue(client.ns.SyncStateApplyFull('Bob-TestRealm', 0, zero))
        changed = []
        for quest_id in range(1, 31):
            client.ns.questHistory[quest_id] = True
            client.ns.SyncStateMarkDirty(quest_id)
            client.ns.SyncStateScan()
            changed.append(quest_id)
        messages = []
        client.ns.QueueMessages = lambda rows, lane: messages.extend((rows[i], lane) for i in range(1, len(rows) + 1)) or True
        self.assertTrue(client.ns.SyncStateSendPeer('Bob-TestRealm'))
        updates = [message for message, lane in messages if lane == 'now']
        self.assertEqual(len(updates), 2)
        self.assertTrue(all(len(message) <= 255 and message.startswith('1|U|30|') for message in updates))
        for message in updates:
            handled, accepted, reason = client.ns.ReceiveSyncStateMessage(message, 'Bob-TestRealm')
            self.assertTrue(handled)
            self.assertTrue(accepted, reason)
        state = client.ns.members['Bob-TestRealm']
        self.assertEqual(state.receivedRev, 30)
        self.assertTrue(all(state.completed[quest_id] for quest_id in changed))

    def test_journal_caps_at_one_thousand_and_moves_min_revision(self):
        client = self.client_with_catalogue(1001)
        for quest_id in range(1, 1002):
            client.ns.questHistory[quest_id] = True
            client.ns.SyncStateMarkDirty(quest_id)
            client.ns.SyncStateScan()
        saved = client.ns.char.syncState
        self.assertEqual(len(saved.journal), 1000)
        self.assertEqual(len(client.ns.char.stateJournal), 1000)
        self.assertEqual(saved.minRev, 1)
        self.assertIsNone(client.ns.SyncStateJournalSince(0))
        self.assertEqual(len(client.ns.SyncStateJournalSince(1)), 1000)

    def test_sync_scans_catalogue_once_then_records_coalesced_dirty_quests(self):
        client = self.client_with_catalogue(1000)
        calls = []
        client.ns.Completed = lambda quest_id: calls.append(quest_id) or False
        client.ns.SyncStateInitialize()  # Reconcile the saved bitset once on this login.
        client.ns.SyncStateScan()
        self.assertEqual(len(calls), 1000)
        calls.clear()
        client.ns.SyncStateScan()
        self.assertEqual(calls, [])
        client.ns.active[17] = True
        client.ns.SyncStateRefreshActive(client.lua.table(), client.ns.active)
        client.ns.SyncStateMarkDirty(17)
        client.ns.SyncStateScan()
        self.assertEqual(calls, [17])
        self.assertEqual(client.ns.SyncStateRevision(), 1)
        self.assertEqual(client.ns.SyncStateJournalSince(0)[1].id, 17)


if __name__ == '__main__':
    unittest.main()
