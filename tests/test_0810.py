"""Unknown beta events must not interrupt TOC loading or claim a home binding."""
import unittest

from lupa.lua51 import LuaError
from test_addon import Client
from test_087 import tip_client


class BetaEventStartupTests(unittest.TestCase):
    def test_reported_invalid_inn_event_is_never_registered(self):
        c = Client()
        self.assertIsNone(c.ns.frame.registrationAttempts.INN_INFO)
        self.assertIsNone(c.ns.handlers.INN_INFO)
        self.assertIsNotNone(c.ns.ui)
        self.assertIsNotNone(c.ns.navigation)
        self.assertTrue(c.ns.minimapButton.IsShown(c.ns.minimapButton))
        self.assertTrue(c.ns.questReady)
        self.assertEqual(c.ns.active[1], 'Quest 1')

    def test_absent_optional_events_do_not_stop_initialization_or_later_events(self):
        c = Client(before_load='''
            unsupportedEvents={CONFIRM_BINDER=true, HEARTHSTONE_BOUND=true,
                COMMODITY_SEARCH_RESULTS_UPDATED=true}
        ''')
        for event in ('CONFIRM_BINDER', 'HEARTHSTONE_BOUND', 'COMMODITY_SEARCH_RESULTS_UPDATED'):
            self.assertIsNone(c.ns.handlers[event])
            self.assertIsNotNone(c.ns.eventFailures[event])
        c.guide_environment(level=12)
        for event in ('PLAYER_LOGIN', 'QUEST_LOG_UPDATE', 'ZONE_CHANGED_NEW_AREA'):
            self.assertTrue(c.ns.frame.registeredEvents[event])
            c.ns.frame.OnEvent(c.ns.frame, event)
        c.drain()
        self.assertEqual(set(c.ns.active), {1, 2})
        self.assertIsNotNone(c.ns.navigation)
        self.assertIsNotNone(c.ns.ui.trackerButton)
        self.assertIsNotNone(c.ns.InitializeGuideTips)
        count = len(c.lua.globals().logs)
        c.ns.Diagnostics()
        report = c.ns.diagnosticsText.text
        self.assertIn('0.8.10', report)
        self.assertIn('HEARTHSTONE_BOUND (registration rejected)', report)
        self.assertIn('Inn recording: unavailable; binding event unavailable', report)
        self.assertEqual(len(c.lua.globals().logs), count)

    def test_validity_probe_avoids_native_registration_of_unsupported_event(self):
        c = Client(before_load='''
            unsupportedEvents={CONFIRM_BINDER=true}
            C_EventUtils={IsEventValid=function(event) return not unsupportedEvents[event] end}
        ''')
        self.assertIsNone(c.ns.frame.registrationAttempts.CONFIRM_BINDER)
        self.assertEqual(c.ns.eventFailures.CONFIRM_BINDER, 'unsupported')
        self.assertIsNone(c.ns.handlers.CONFIRM_BINDER)
        c.ns.Diagnostics()
        self.assertIn('C_EventUtils.IsEventValid: present', c.ns.diagnosticsText.text)

    def test_failed_or_restricted_validity_probe_falls_back_to_actual_registration(self):
        for result in ('error("probe failed")', 'secret', 'nil'):
            with self.subTest(result=result):
                c = Client(before_load='''
                    unsupportedEvents={CONFIRM_BINDER=true}
                    C_EventUtils={IsEventValid=function() %s end}
                ''' % (result if result.startswith('error') else 'return ' + result))
                self.assertEqual(c.ns.frame.registrationAttempts.CONFIRM_BINDER, 1)
                self.assertIsNone(c.ns.handlers.CONFIRM_BINDER)
                self.assertTrue(c.ns.frame.registeredEvents.QUEST_LOG_UPDATE)

    def test_positive_validity_does_not_override_rejected_registration(self):
        c = Client(before_load='''
            C_EventUtils={IsEventValid=function() return true end}
            rejectedEvents={HEARTHSTONE_BOUND=true}
            unsupportedEvents={CONFIRM_BINDER=true}
        ''')
        self.assertIsNone(c.ns.handlers.HEARTHSTONE_BOUND)
        self.assertIsNone(c.ns.handlers.CONFIRM_BINDER)
        self.assertIsNotNone(c.ns.navigation)

    def test_successful_retry_installs_handler_and_clears_failure(self):
        c = Client(before_load='unsupportedEvents={CONFIRM_BINDER=true}')
        c.lua.globals().unsupportedEvents.CONFIRM_BINDER = None
        handler = c.lua.eval('function() callbackRan=true end')
        self.assertTrue(c.ns.On('CONFIRM_BINDER', handler))
        self.assertIsNone(c.ns.eventFailures.CONFIRM_BINDER)
        c.ns.frame.OnEvent(c.ns.frame, 'CONFIRM_BINDER')
        self.assertTrue(c.lua.globals().callbackRan)

    def test_handler_errors_still_propagate(self):
        c = Client()
        c.ns.On('QUEST_POI_UPDATE', c.lua.eval('function() error("handler regression") end'))
        with self.assertRaisesRegex(LuaError, 'handler regression'):
            c.ns.frame.OnEvent(c.ns.frame, 'QUEST_POI_UPDATE')

    def test_modern_binder_interaction_records_visit_without_binding(self):
        c = Client(before_load='''
            Enum.PlayerInteractionType={Binder=901, Gossip=902}
            unsupportedEvents={CONFIRM_BINDER=true}
        ''')
        c.guide_environment()
        c.lua.execute('''
            C_Map.GetMapWorldSize=function() return 1000,1000 end
            function UnitGUID() return "Creature-0-1-2-3-500-ABC" end
        ''')
        c.ns.guideServiceData = c.lua.table_from({'inns': [{
            'id': 'TEST_INN', 'npcID': 500, 'name': 'Test hub', 'faction': 'Horde',
            'mapID': 501, 'x': .21, 'y': .37}]}, recursive=True)
        state = c.ns.db.guideServices[c.ns.self]
        event = 'PLAYER_INTERACTION_MANAGER_FRAME_SHOW'
        for payload in (902, c.lua.globals().secret):
            c.ns.frame.OnEvent(c.ns.frame, event, payload)
            self.assertEqual(len(state.inns), 0)
        c.ns.frame.OnEvent(c.ns.frame, event, 901)
        self.assertEqual(state.inns.TEST_INN.name, 'Test hub')
        self.assertIsNone(state.boundInnID)
        c.ns.frame.OnEvent(c.ns.frame, 'HEARTHSTONE_BOUND')
        self.assertEqual(state.boundInnID, 'TEST_INN')
        self.assertIsNone(c.ns.pendingGuideInn)
        c.ns.Diagnostics()
        self.assertIn('Inn recording: modern binder interaction; binding event registered', c.ns.diagnosticsText.text)

    def test_missing_binder_enum_does_not_treat_other_npc_interactions_as_inns(self):
        for value in ('nil', 'secret'):
            c = Client(before_load='Enum.PlayerInteractionType={Binder=' + value + '}')
            self.assertIsNone(c.ns.handlers.PLAYER_INTERACTION_MANAGER_FRAME_SHOW)
            self.assertIsNotNone(c.ns.handlers.CONFIRM_BINDER)

    def test_unavailable_binding_event_keeps_native_home_detection(self):
        c = tip_client()
        c.ns.frame.RegisterEvent = c.lua.eval('function() return false end')
        c.ns.handlers.HEARTHSTONE_BOUND = None
        self.assertFalse(c.ns.On('HEARTHSTONE_BOUND', c.lua.eval('function() error("unexpected bind") end')))
        self.assertIsNotNone(c.ns.CurrentGuideTip())
        c.lua.execute('function GetBindLocation() return "Test hub" end; clock=3')
        self.assertIsNone(c.ns.CurrentGuideTip())
        self.assertIsNone(c.ns.db.guideServices[c.ns.self].boundInnID)

    def test_unreadable_new_visit_clears_stale_binding_candidate(self):
        c = tip_client()
        c.lua.execute('function UnitGUID() return "Creature-0-1-2-3-500-ABC" end')
        c.ns.handlers.CONFIRM_BINDER()
        self.assertEqual(c.ns.pendingGuideInn, 'INN_500')
        c.lua.execute('C_Map.GetBestMapForUnit=function() return secret end')
        c.ns.handlers.CONFIRM_BINDER()
        self.assertIsNone(c.ns.pendingGuideInn)
        c.ns.handlers.HEARTHSTONE_BOUND()
        self.assertIsNone(c.ns.db.guideServices[c.ns.self].boundInnID)


if __name__ == '__main__':
    unittest.main()
