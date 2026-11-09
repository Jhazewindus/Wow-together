"""Shared non-modal suggestion strip and trigger dismissal behavior."""
import unittest

from test_addon import Client


class SuggestionChipTests(unittest.TestCase):
    def test_newest_replaces_previous_and_only_one_frame_is_shown(self):
        c = Client()
        empty = c.lua.table_from([])
        c.ns.ShowSuggestionChip('first', 'one', 'First', empty)
        first = c.ns.suggestionChipFrame
        self.assertTrue(first.IsShown(first))
        c.ns.ShowSuggestionChip('second', 'two', 'Second', empty)
        self.assertTrue(c.ns.suggestionChipFrame.IsShown(c.ns.suggestionChipFrame))
        self.assertEqual(c.ns.CurrentSuggestionChip().kind, 'second')
        self.assertTrue(c.lua.eval('rawequal')(first, c.ns.suggestionChipFrame))

    def test_expiry_hides_chip_and_suppresses_same_trigger(self):
        c = Client()
        empty = c.lua.table_from([])
        self.assertTrue(c.ns.ShowSuggestionChip('tip', 'flight:4', 'Flight master', empty))
        c.ns.suggestionChipFrame.OnUpdate(c.ns.suggestionChipFrame, 29)
        self.assertTrue(c.ns.suggestionChipFrame.IsShown(c.ns.suggestionChipFrame))
        c.ns.suggestionChipFrame.OnUpdate(c.ns.suggestionChipFrame, 1)
        self.assertFalse(c.ns.suggestionChipFrame.IsShown(c.ns.suggestionChipFrame))
        self.assertFalse(c.ns.ShowSuggestionChip('tip', 'flight:4', 'Flight master', empty))
        c.ns.ClearSuggestionChip('tip', 'flight:4')
        self.assertTrue(c.ns.ShowSuggestionChip('tip', 'flight:4', 'Flight master', empty))

    def test_activity_prompt_source_routes_actions_through_chip(self):
        c = Client()
        c.lua.execute('activityAccepted = false')
        c.ns.ShowActivityPrompt('collection:razorfen', 'Collect Razorfen quests?',
            'Three quests are available.', c.lua.eval('function() activityAccepted = true end'),
            'Show plan', 'Later')
        self.assertEqual(c.ns.CurrentSuggestionChip().kind, 'activity')
        self.assertIsNone(c.lua.globals().WowTogetherActivityPrompt)
        c.ns.activityPrompt.accept.OnClick()
        self.assertTrue(c.lua.globals().activityAccepted)
        self.assertIsNone(c.ns.CurrentSuggestionChip())

    def test_party_mode_question_is_nonmodal_and_dismissal_is_group_scoped(self):
        c = Client(party_mode='ask')
        c.unit_names({'player': ('Alice', 'TestRealm'), 'party1': ('Bob', 'TestRealm')})
        c.lua.execute('function IsInGroup() return true end; function IsInRaid() return false end')
        c.ns.handlers.GROUP_ROSTER_UPDATE()
        self.assertEqual(c.ns.CurrentSuggestionChip().kind, 'partyMode')
        self.assertIsNone(c.lua.globals().WowTogetherPartyModePrompt)
        c.ns.partyPrompt.later.OnClick()
        c.ns.handlers.GROUP_ROSTER_UPDATE()
        self.assertFalse(c.ns.partyPrompt.IsShown(c.ns.partyPrompt))


if __name__ == '__main__':
    unittest.main()
