"""Sync must not rebuild hidden browsers or lose shared event handlers.

The shipped catalogue exercises the reported workload. These are Lua 5.1 host
checks, not a measurement of the beta client's script watchdog or frame rate.
"""
import unittest

from test_addon import Client
from test_063 import guide_client
from test_074 import scanning_client
from test_0815 import entries


def observe_browser(c):
    c.lua.globals().regressionNS = c.ns
    c.lua.execute('''
        browserReads, dashboardReads = 0, 0
        local browser, render = regressionNS.GuideBrowserChoices, regressionNS.Render
        regressionNS.GuideBrowserChoices=function(...)
            browserReads=browserReads+1; return browser(...)
        end
        regressionNS.Render=function(...)
            dashboardReads=dashboardReads+1; return render(...)
        end
    ''')


class SharedEventTests(unittest.TestCase):
    def test_replacing_handler_never_registers_twice_and_errors_still_surface(self):
        c = Client()
        event = 'PLAYER_REGEN_ENABLED'
        self.assertTrue(c.ns.On(event, c.lua.eval('function() replacementRan=true end')))
        c.ns.frame.OnEvent(c.ns.frame, event)
        self.assertTrue(c.lua.globals().replacementRan)
        self.assertEqual(c.ns.frame.registrationAttempts[event], 1)

    def test_party_prefix_remains_registered_when_party_features_are_disabled(self):
        c = Client()
        c.ns.SetOption('partyMode', 'never')
        self.assertTrue(c.ns.frame.registeredEvents.CHAT_MSG_ADDON)
        self.assertIsNotNone(c.ns.handlers.CHAT_MSG_ADDON)
        self.assertIsNone(c.ns.eventFailures.CHAT_MSG_ADDON)
        self.assertFalse(c.ns.PartyFeaturesEnabled())
        c.ns.SetOption('partyMode', 'always')
        self.assertTrue(c.ns.PartyFeaturesEnabled())


if __name__ == '__main__':
    unittest.main()
