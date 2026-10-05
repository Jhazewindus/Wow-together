"""User-tested beta pickup semantics: host regressions, not live API certification."""
import unittest

from test_050 import solo
from test_061 import world_quest, selected, run_plan
from test_routes import catalogue, map_canvas, route_client


def native(c, **values):
    c.lua.execute('''
    pickupCalls, pickupResults = {}, {}
    C_QuestLog.IsPushableQuest = function(id)
      pickupCalls[id] = (pickupCalls[id] or 0) + 1
      return pickupResults[id]
    end
    ''')
    for id, value in values.items():
        c.lua.globals().pickupResults[int(id)] = value
    c.ns.InvalidatePickupAvailability()


def allowed(c, id, key=None):
    result = c.ns.CatalogueAllowed(id, c.ns.profile, key or c.ns.self)
    return result[0] if isinstance(result, tuple) else result


class PickupGateTests(unittest.TestCase):
    def client(self):
        c = solo(); map_canvas(c)
        catalogue(c, {900: world_quest('First'), 901: world_quest('Followup', previousQuest=900)})
        return c

    def test_true_confirms_hidden_gate_false_blocks_pickup_and_option_restores_fallback(self):
        c = self.client(); native(c, **{'900': False, '901': True})
        self.assertFalse(allowed(c, 900))
        self.assertTrue(allowed(c, 901))  # Native beta evidence overrides incomplete published requirements.
        c.ns.db.config.betaPickupCheck = False
        self.assertTrue(allowed(c, 900))
        self.assertFalse(allowed(c, 901))

    def test_missing_restricted_and_failing_reads_stay_distinct_and_secret_safe(self):
        c = self.client()
        self.assertTrue(allowed(c, 900))  # Missing API keeps the existing evidence gates.
        native(c)
        self.assertIsNone(allowed(c, 900))
        c.lua.globals().pickupResults[900] = c.lua.globals().secret
        c.ns.InvalidatePickupAvailability()
        self.assertIsNone(allowed(c, 900))
        c.lua.execute("C_QuestLog.IsPushableQuest=function() error('read failed') end")
        c.ns.InvalidatePickupAvailability()
        self.assertIsNone(allowed(c, 900))
        c.ns.Diagnostics()
        self.assertIn('unknown', c.ns.diagnosticsText.text)

    def test_native_true_cannot_override_known_faction_level_or_complete_quest(self):
        c = self.client(); native(c, **{'900': True, '901': True})
        c.ns.catalogue.quests[900].side = 'Alliance'
        self.assertFalse(allowed(c, 900))
        c.ns.catalogue.quests[900].side = 'Horde'
        c.ns.catalogue.quests[900].minLevel = 50
        self.assertFalse(allowed(c, 900))
        c.lua.globals().finished[901] = True
        self.assertEqual(len(c.ns.RouteStages(c.ns.CatalogueRecord(901), c.ns.self)), 0)

    def test_false_does_not_drop_accepted_objective_or_turn_in(self):
        c = self.client(); native(c, **{'900': False})
        c.ns.active[900] = 'First'
        self.assertEqual(c.ns.RouteStages(c.ns.CatalogueRecord(900), c.ns.self)[1].kind, 'q')
        c.ns.readyToTurnIn[900] = True
        self.assertEqual(c.ns.RouteStages(c.ns.CatalogueRecord(900), c.ns.self)[1].kind, 't')
        c.ns.active[900], c.ns.offered[900] = None, True
        self.assertEqual(len(c.ns.RouteStages(c.ns.CatalogueRecord(900), c.ns.self)), 0)

    def test_turn_in_event_unlocks_next_pickup_without_manual_scan(self):
        c = self.client(); native(c, **{'900': True, '901': False})
        c.ns.ShowGuideOnMap(selected(c)); run_plan(c)
        self.assertEqual({s.id for s in c.ns.selectedRoute.stops.values()}, {900})
        c.lua.globals().pickupResults[901] = True
        c.lua.globals().finished[900] = True
        c.ns.handlers.QUEST_TURNED_IN(900)
        c.drain()
        self.assertEqual({s.id for s in c.ns.selectedRoute.stops.values()}, {901})
        self.assertEqual(c.ns.selectedRoute.stops[1].kind, 'a')
        self.assertEqual(len(c.ns.routeSelection.records), 2)

    def test_new_nearby_unlock_joins_trip_while_unfinished_objective_stays_first(self):
        c = self.client()
        catalogue(c, {900: world_quest('Active work'), 901: world_quest('Nearby unlock',
            starts=[{'mapID': 501, 'x': .21, 'y': .37, 'name': 'NPC'}])})
        native(c, **{'900': False, '901': False})
        c.lua.globals().entries[1] = c.lua.table_from({'questID': 900, 'isHeader': False, 'title': 'Active work'})
        c.ns.ShowGuideOnMap(selected(c)); run_plan(c)
        before = c.ns.GuideStepKey(c.ns.selectedRoute.stops[1])
        c.lua.globals().pickupResults[901] = True
        c.ns.handlers.QUEST_LOG_UPDATE(); c.drain()
        self.assertEqual(c.ns.GuideStepKey(c.ns.selectedRoute.stops[1]), before)
        self.assertEqual({s.id for s in c.ns.selectedRoute.stops.values()}, {900, 901})

    def test_combat_defers_new_query_preserves_public_cache_and_rechecks_on_regen(self):
        c = self.client(); native(c, **{'900': True})
        self.assertTrue(allowed(c, 900))
        previous = c.lua.globals().pickupCalls[900]
        c.lua.globals().combat = True
        c.lua.globals().pickupResults[900] = False
        c.ns.handlers.QUEST_LOG_UPDATE()
        self.assertTrue(allowed(c, 900))
        self.assertEqual(c.lua.globals().pickupCalls[900], previous)
        c.lua.globals().combat = False
        c.ns.handlers.PLAYER_REGEN_ENABLED()
        self.assertFalse(allowed(c, 900))

    def test_global_capability_is_preferred_and_cached_until_a_relevant_event(self):
        c = self.client(); native(c, **{'900': False})
        c.lua.execute('function IsPushableQuest(id) return true end')
        self.assertTrue(allowed(c, 900))
        self.assertIsNone(c.lua.globals().pickupCalls[900])
        c.lua.execute('function IsPushableQuest(id) return false end')
        self.assertTrue(allowed(c, 900))
        c.ns.handlers.PLAYER_LEVEL_UP(13)
        self.assertFalse(allowed(c, 900))


class PickupSyncTests(unittest.TestCase):
    def receiver(self):
        c = route_client()
        c.ns.members['Bob-TestRealm'] = c.lua.table()
        member = c.ns.members['Bob-TestRealm']
        member.active, member.activeRevision = c.lua.table(), 7
        member.profile = c.ns.profile
        return c, member

    def test_received_boolean_applies_only_to_sender_and_matching_active_revision(self):
        c, member = self.receiver(); native(c, **{'900': False})
        self.assertEqual(c.ns.ReceivePickupAvailabilityMessage('1|E|7|1|1|1|1|900:1', 'Bob-TestRealm'), (True, True))
        self.assertTrue(allowed(c, 900, 'Bob-TestRealm'))
        self.assertIsNone(c.lua.globals().pickupCalls[900])  # No API call for the friend.
        self.assertFalse(allowed(c, 900))
        member.activeRevision = 8
        self.assertIsNone(allowed(c, 900, 'Bob-TestRealm'))
        c.ns.ReceivePickupAvailabilityMessage('1|E|8|2|1|1|1|900:0', 'Bob-TestRealm')
        self.assertFalse(allowed(c, 900, 'Bob-TestRealm'))
        self.assertFalse(c.ns.ReceivePickupAvailabilityMessage('1|E|7|3|1|1|1|900:1', 'Bob-TestRealm')[1])

    def test_out_of_order_parts_are_atomic_and_duplicates_cannot_override(self):
        c, member = self.receiver()
        receive = c.ns.ReceivePickupAvailabilityMessage
        self.assertEqual(receive('1|E|7|4|2|2|1|901:0', 'Bob-TestRealm'), (True, True))
        self.assertIsNone(member.pickupAvailability)
        self.assertFalse(receive('1|E|7|4|2|2|1|901:1', 'Bob-TestRealm')[1])
        receive('1|E|7|4|1|2|1|900:1', 'Bob-TestRealm')
        self.assertTrue(member.pickupAvailability['values'][900])
        self.assertFalse(member.pickupAvailability['values'][901])
        self.assertFalse(receive('1|E|7|4|1|1|1|900:0', 'Bob-TestRealm')[1])
        receive('1|E|7|5|1|1|1|', 'Bob-TestRealm')
        self.assertIsNone(allowed(c, 900, 'Bob-TestRealm'))  # Empty supported snapshot means unknown.
        receive('1|E|7|6|1|1|0|', 'Bob-TestRealm')
        self.assertTrue(allowed(c, 900, 'Bob-TestRealm'))  # Missing/disabled API uses older evidence.

    def test_invalid_payloads_and_cross_part_duplicate_quests_are_rejected(self):
        c, member = self.receiver(); receive = c.ns.ReceivePickupAvailabilityMessage
        for message in ('1|E|7|1|1|1|1|900:1,900:0', '1|E|7|1|1|1|1|900:2',
                        '1|E|7|1|1|30|1|900:1', '1|E|7|1|1|1|0|900:1',
                        '1|E|7|1|1|1|1|900:1,', '1|E|7|1|1|1|1|0:1'):
            self.assertFalse(receive(message, 'Bob-TestRealm')[1])
        receive('1|E|7|2|1|2|1|900:0', 'Bob-TestRealm')
        self.assertFalse(receive('1|E|7|2|2|2|1|900:1', 'Bob-TestRealm')[1])
        self.assertIsNone(member.pickupAvailability)

    def test_send_is_bounded_coalesced_and_changes_without_log_revision(self):
        c = self.receiver()[0]; native(c, **{'900': True})
        messages = []
        c.ns.QueueMessage = lambda message: messages.append(message) or True
        c.ns.SendPickupAvailability(False, 7)
        self.assertTrue(all(len(m) <= 255 for m in messages))
        self.assertIn('900:1', ','.join(messages))
        first_count = len(messages)
        c.ns.SendPickupAvailability(False, 7)
        self.assertEqual(len(messages), first_count)
        c.lua.globals().pickupResults[900] = False
        c.ns.handlers.QUEST_TURNED_IN(899)
        c.ns.SendPickupAvailability(False, 7)
        self.assertGreater(len(messages), first_count)
        self.assertIn('900:0', messages[-1])

    def test_real_transport_updates_each_characters_result_on_unchanged_log(self):
        from test_addon import Client
        a, b = Client(quests=()), Client(name='Bob', peer='Alice', quests=())
        for c, result in ((a, True), (b, False)):
            c.guide_environment(level=12)
            catalogue(c, {900: world_quest()})
            native(c, **{'900': result})
        a.ns.SyncNow(True)
        # A peer can reply before sending its own hello. Finish the existing
        # hello/recovery handshake before comparing a synchronized character.
        for _ in range(8):
            outgoing_a = a.drain()
            for prefix, message, channel in outgoing_a:
                b.receive(message, sender='Alice-TestRealm')
            outgoing_b = b.drain()
            for prefix, message, channel in outgoing_b:
                a.receive(message, sender='Bob-TestRealm')
            if not outgoing_a and not outgoing_b:
                break
        self.assertFalse(allowed(a, 900, 'Bob-TestRealm'))
        self.assertTrue(allowed(b, 900, 'Alice-TestRealm'))
        revision = a.ns.members['Bob-TestRealm'].activeRevision
        b.lua.globals().pickupResults[900] = True
        b.ns.handlers.QUEST_TURNED_IN(899)
        for prefix, message, channel in b.drain():
            a.receive(message, sender='Bob-TestRealm')
        self.assertEqual(a.ns.members['Bob-TestRealm'].activeRevision, revision)
        self.assertTrue(allowed(a, 900, 'Bob-TestRealm'))

    def test_peer_reload_resets_old_native_sequence_and_accepts_a_fresh_snapshot(self):
        c, member = self.receiver()
        c.receive('1|E|7|99|1|1|1|900:0')
        self.assertFalse(allowed(c, 900, 'Bob-TestRealm'))
        c.receive('1|H')
        self.assertIsNone(member.pickupAvailability)
        c.receive('1|E|1|1|1|1|1|900:1')  # Can arrive before the new active snapshot.
        c.receive('1|S|1|1|1|')
        self.assertTrue(allowed(c, 900, 'Bob-TestRealm'))


if __name__ == '__main__':
    unittest.main()
