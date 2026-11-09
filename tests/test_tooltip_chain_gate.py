"""Quest tooltip copy and compact travel-path summaries."""
import unittest

from test_addon import Client


class TooltipAndTravelSummaryTests(unittest.TestCase):
    def client(self):
        c = Client(quests=())
        c.ns.profile.name = "Alice"
        return c

    def test_forty_consecutive_trail_legs_collapse_to_one_walk_segment(self):
        c = self.client()
        legs = c.lua.table()
        for index in range(1, 41):
            legs[index] = c.lua.table_from({'method': 'walk', 'seconds': 6,
                'to': {'trail': True, 'mapID': 1, 'x': index / 100, 'y': .5}})
        c.ns.travelPath = c.lua.table_from({'cursor': 1, 'seconds': 240, 'legs': legs,
            'goal': {'mapID': 1, 'x': .4, 'y': .5}})
        c.ns.HasTravelPathTo = lambda *_: True
        summary = c.ns.TravelPathSummary(c.lua.table_from({'kind': 'q', 'mapID': 1, 'x': .4, 'y': .5,
            'travelLeg': {'method': 'walk'}}))
        self.assertEqual(summary, 'Walk ~4 min.')
        self.assertEqual(summary.lower().count('walk'), 1)
        c.lua.execute('''local ns = ...
            ns.GuideDestinationDecision = function() return {code='on-pace', specificBenefit=false} end
            ns.StopInstruction = function() return 'Kill 8 Venture Co. Workers' end
            ns.StopLocationText = function() return 'Stonetalon Mountains • 38.6, 85.9' end''', c.ns)
        goal = c.lua.table_from({'id': 100, 'kind': 'q', 'title': 'Test quest', 'mapID': 1,
            'x': .4, 'y': .5, 'action': 'kill', 'targetName': 'Venture Co. Workers', 'quantity': 8})
        stop = c.lua.table_from({'kind': 'travel', 'goal': goal, 'travelLeg': {'method': 'walk',
            'to': {'mapID': 1, 'x': .4, 'y': .5}}}, recursive=True)
        facts = c.lua.table_from({'stop': goal, 'action': 'kill', 'amount': '8 ', 'target': 'Venture Co. Workers'})
        presentation = c.ns.GuideStepPresentation(stop, facts, c.lua.table(), c.lua.table())
        self.assertEqual(presentation.travel, 'Walk ~4 min.')

    def test_transport_then_line_uses_quest_location_and_objective_action(self):
        c = self.client()
        c.lua.execute('''local ns = ...
          ns.GuideDestinationDecision = function() return {code='chain-value', why='A useful chain.',
            specificBenefit=true, confidence='supported'} end
          ns.StopLocationText = function(stop)
            if stop.mapID == 101 then return 'Orgrimmar • 45.0, 63.0' end
            return 'Stonetalon Mountains • 38.6, 85.9'
          end
          ns.TravelPathSummary = function() return 'Teleport, then walk ~4 min.' end''', c.ns)
        goal = c.lua.table_from({'id': 1093, 'kind': 'q', 'title': 'Super Reaper 6000',
            'mapID': 102, 'x': .386, 'y': .859, 'action': 'kill', 'targetName': 'Venture Co. Workers',
            'quantity': 8, 'memberKey': c.ns.self, 'forPlayer': 'Alice'})
        stop = c.lua.table_from({'kind': 'travel', 'goal': goal, 'travelLeg': {
            'method': 'teleport', 'name': 'Teleport to Orgrimmar',
            'to': {'mapID': 101, 'x': .45, 'y': .63}}}, recursive=True)
        facts = c.lua.table_from({'stop': goal, 'action': 'kill', 'amount': '8 ',
            'target': 'Venture Co. Workers', 'progress': None})
        presentation = c.ns.GuideStepPresentation(stop, facts, c.lua.table(), c.lua.table())
        self.assertIn('Kill 8 Venture Co. Workers', presentation.then_)
        self.assertIn('Stonetalon Mountains • 38.6, 85.9', presentation.then_)
        self.assertNotIn('Orgrimmar', presentation.then_)
        self.assertNotIn('Work on', presentation.what)
        self.assertFalse(any('For Alice' in str(value) for value in presentation.details.values()))
        lines = c.ns.GuidePresentationTooltipLines(presentation, False)
        self.assertEqual(list(lines.values()), ['Then: Kill 8 Venture Co. Workers (Stonetalon Mountains • 38.6, 85.9).',
            'Teleport, then walk ~4 min.'])

    def test_reason_codes_are_hidden_unless_debug_setting_is_enabled(self):
        c = self.client()
        presentation = c.lua.table_from({'what': 'Travel', 'then_': 'Then: Kill the target.',
            'travel': 'Teleport, then walk ~4 min.', 'evidence': 'Reason: chain-value • supported.',
            'details': ['For Bob']}, recursive=True)
        lines = c.ns.GuidePresentationTooltipLines(presentation, False)
        self.assertEqual(lines[len(lines)], 'Teleport, then walk ~4 min.')
        self.assertFalse(any('Reason:' in str(line) for line in lines.values()))
        c.ns.SetOption('debugReasons', True)
        lines = c.ns.GuidePresentationTooltipLines(presentation, False)
        self.assertEqual(lines[len(lines)], 'Reason: chain-value • supported.')


if __name__ == '__main__':
    unittest.main()
