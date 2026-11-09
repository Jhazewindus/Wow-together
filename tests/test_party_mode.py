"""Party-mode prompt and session-scoped consent."""
import unittest

from test_addon import Client


class PartyModeTests(unittest.TestCase):
    def grouped(self, client):
        client.unit_names({'player': ('Alice', 'TestRealm'), 'party1': ('Bob', 'TestRealm')})
        client.lua.execute('function IsInGroup() return true end; function IsInRaid() return false end')
        client.ns.handlers.GROUP_ROSTER_UPDATE()

    def test_ask_registers_prefix_and_prompts_on_normal_group(self):
        c = Client(party_mode='ask')
        self.assertTrue(c.lua.globals().C_ChatInfo.IsAddonMessagePrefixRegistered('WowTogetherV1'))
        self.assertFalse(c.ns.PartyFeaturesEnabled())
        self.grouped(c)
        self.assertTrue(c.ns.partyPrompt.IsShown(c.ns.partyPrompt))
        c.ns.partyPrompt.yes.OnClick(c.ns.partyPrompt.yes)
        self.assertTrue(c.ns.PartyFeaturesEnabled())
        self.assertTrue(c.ns.partyModeTemporary)
        self.assertGreater(c.ns.TransportState().queued, 0)

    def test_ask_accepts_only_peer_hello_before_consent(self):
        c = Client(party_mode='ask')
        self.grouped(c)
        queued_before = c.ns.TransportState().queued
        c.ns.Receive('WowTogetherV1', '2|H|0.8.106|1', 'PARTY', 'Bob-TestRealm')
        peer = c.ns.members['Bob-TestRealm']
        self.assertEqual(peer.version, '0.8.106')
        self.assertTrue(peer.planSupport)
        self.assertEqual(c.ns.TransportState().queued, queued_before)
        self.assertFalse(c.ns.PartyFeaturesEnabled())

    def test_not_now_suppresses_only_this_roster_and_leave_restores_solo(self):
        c = Client(party_mode='ask')
        self.grouped(c)
        c.ns.partyPrompt.later.OnClick(c.ns.partyPrompt.later)
        c.ns.handlers.GROUP_ROSTER_UPDATE()
        self.assertFalse(c.ns.partyPrompt.IsShown(c.ns.partyPrompt))
        self.assertEqual(c.ns.Option('partyMode'), 'ask')
        c.ns.partyModeTemporary = True
        c.ns.ApplyPartyMode()
        c.lua.execute('function IsInGroup() return false end')
        c.ns.handlers.GROUP_ROSTER_UPDATE()
        self.assertFalse(c.ns.PartyFeaturesEnabled())
        self.assertIsNone(c.ns.partyModeTemporary)

    def test_never_choice_persists(self):
        c = Client(party_mode='ask')
        self.grouped(c)
        c.ns.partyPrompt.never.OnClick(c.ns.partyPrompt.never)
        self.assertEqual(c.ns.Option('partyMode'), 'never')
        self.assertFalse(c.ns.PartyFeaturesEnabled())


if __name__ == '__main__':
    unittest.main()
