"""Structured guide card presentation checks under the addon's Lua 5.1 host."""
import unittest
from pathlib import Path

from test_addon import Client

ROOT = Path(__file__).resolve().parents[1]


class PresentationTests(unittest.TestCase):
    def setUp(self):
        self.client = Client()
        self.lua, self.ns = self.client.lua, self.client.ns
        self.ns.profile.faction = 'Horde'
        self.lua.execute(r'''
          local ns = ...
          ns.CatalogueQuest = function(id) return id and {id=id, level=35, minLevel=24, providedItems={}} end
          ns.CatalogueCompletion = function() return false end
          ns.StopLocationText = function(stop) return stop.location or "Orgrimmar • 38.6, 85.9" end
          ns.StopIcon = function(stop) return stop.icon or "Interface\\GossipFrame\\AvailableQuestIcon" end
          ns.MapName = function(map) return map == 1454 and "Orgrimmar" or "Alterac Mountains" end
          ns.TravelPathSummary = function() return nil end
          ns.PersonalTransportLabel = function(leg) return "Cast Teleport: Orgrimmar" end
          ns.GuideDestinationDecision = function(stop)
            return stop.testDecision or {code="quest-objective", why="Required for this quest chain.",
              specificBenefit=true, confidence="confirmed"}
          end
        ''', self.ns)

    def stop(self, values):
        return self.lua.table_from(values, recursive=True)

    def present(self, stop, facts, guide=None, route=None, state=None):
        return self.ns.GuideStepPresentation(stop, facts, guide, route, state)

    def assert_presentation_rules(self, card):
        for field in ('what', 'why', 'status', 'stepLine', 'location'):
            value = card[field]
            if value:
                self.assertNotRegex(value, r'[.!]+$')
        forbidden = ('saved or previewed', 'selected guide', 'dijkstra', 'published', 'snapshot', 'revision', 'beta', 'guide step')
        visible = [card.title, card.stepLine, card.what, card.why, card.status, card.location, card.then_, card.travel]
        visible += list(card.details.values())
        for field in visible:
            if field:
                lowered = field.lower()
                for phrase in forbidden:
                    self.assertNotIn(phrase, lowered)
        lines = list(self.ns.GuidePresentationTooltipLines(card, False).values())
        self.assertLessEqual(len(lines) + 1, 6)  # Include the gold title line.
        shown = {value.rstrip('.!').lower() for value in (card.what, card.why, card.status) if value}
        seen = set()
        for line in lines:
            key = line.rstrip('.!').lower()
            self.assertNotIn(key, seen)
            self.assertNotIn(key, shown)
            seen.add(key)

    def test_pickups_kill_turnin_later_and_done_fields(self):
        guide = self.lua.table_from({'mode': 'zone', 'zone': 'The Barrens'})
        facts = lambda stop, **extra: self.lua.table_from({'stop': stop, **extra}, recursive=True)
        npc = self.stop({'id': 100, 'kind': 'a', 'title': 'The Lost Supplies', 'npcName': 'Sergra Darkthorn',
                         'action': 'talk', 'guideStep': 12, 'location': 'The Barrens • 35.0, 27.0'})
        npc_card = self.present(npc, facts(npc, npc='Sergra Darkthorn', action='talk'), guide)
        self.assertEqual(npc_card.what, 'Accept The Lost Supplies from Sergra Darkthorn')
        self.assertEqual(npc_card.status, 'Required')
        self.assertEqual(npc_card.stepLine, 'Step 12 • Horde / The Barrens')
        self.assert_presentation_rules(npc_card)

        book = self.stop({'id': 101, 'kind': 'a', 'title': 'Defensive Magics 101', 'entityType': 'object',
                          'npcName': 'Manual of Defensive Magics', 'action': 'talk', 'guideStep': 7})
        book_card = self.present(book, facts(book, npc='Manual of Defensive Magics', action='talk'),
                                 self.lua.table_from({'mode': 'chain', 'zone': 'Mage class quests', 'classLineGuide': True}))
        self.assertEqual(book_card.what, 'Read Manual of Defensive Magics (object) to start Defensive Magics 101')
        self.assertLessEqual(len(book_card.what), 70)
        self.assert_presentation_rules(book_card)

        kill = self.stop({'id': 102, 'kind': 'q', 'title': 'The Lost Supplies', 'action': 'kill', 'targetName': 'Razormane Scout'})
        kill_card = self.present(kill, facts(kill, action='kill', target='Razormane Scout', amount='3 more ',
                                             have=5, need=8, progress='5/8'))
        self.assertEqual(kill_card.what, 'Kill 3 more Razormane Scout')
        self.assertEqual(kill_card.progress, '5/8')
        self.assert_presentation_rules(kill_card)

        turnin = self.stop({'id': 103, 'kind': 't', 'title': 'The Lost Supplies', 'npcName': 'Sergra Darkthorn'})
        turnin_card = self.present(turnin, facts(turnin, npc='Sergra Darkthorn'))
        self.assertEqual(turnin_card.what, 'Turn in The Lost Supplies to Sergra Darkthorn')
        self.assert_presentation_rules(turnin_card)

        later = self.stop({'id': 104, 'kind': 'q', 'title': 'A Distant Quest',
                           'testDecision': {'code': 'outside-level-range', 'why': 'Outside level range.', 'specificBenefit': False}})
        later_card = self.present(later, facts(later, action='talk'), guide)
        self.assertIsNone(later_card.why)
        self.assertEqual(later_card.status, 'Later (level 24)')
        self.assert_presentation_rules(later_card)

        done = self.stop({'id': 105, 'kind': 'q', 'title': 'The Lost Supplies', 'action': 'kill', 'targetName': 'Razormane Scout'})
        done_card = self.present(done, facts(done, action='kill', target='Razormane Scout', finished=True))
        self.assertEqual(done_card.status, 'Done')
        self.assert_presentation_rules(done_card)

    def test_borrowed_teleport_card_fields_and_time(self):
        goal = self.stop({'id': 106, 'kind': 'q', 'title': 'Assassination Plot', 'action': 'use',
                          'targetName': 'Galak Messenger', 'useItemName': 'Sealed Letter', 'guideStep': 12,
                          'location': 'Orgrimmar • 38.6, 85.9'})
        facts = self.lua.table_from({'stop': goal, 'action': 'use', 'target': 'Galak Messenger', 'tool': 'Sealed Letter', 'amount': ''})
        leg = self.stop({'id': 106, 'kind': 'travel', 'title': 'Assassination Plot', 'goal': goal,
                         'travelLeg': {'method': 'teleport', 'name': 'Orgrimmar', 'to': {'mapID': 1454}},
                         'guideStep': 12})
        guide = self.lua.table_from({'mode': 'zone', 'zone': 'The Barrens'})
        route = self.lua.table()
        route.stops = self.lua.table(); route.stops[1] = leg
        state = self.lua.table_from({'distance': 212, 'walkSeconds': 30})
        card = self.present(leg, facts, guide, route, state)
        self.assertEqual(card.title, 'Assassination Plot')
        self.assertEqual(card.kind, 'travel-teleport')
        self.assertEqual(card.what, 'Cast Teleport: Orgrimmar')
        self.assertEqual(card.then_, 'Then: Use Sealed Letter on Galak Messenger (Orgrimmar • 38.6, 85.9).')
        self.assertEqual(card.time, '212 yd, ~30 s')
        self.assertEqual(card.status, 'Required')
        self.assert_presentation_rules(card)

    def test_tooltip_is_bounded_and_deduplicates_card_fields(self):
        stop = self.stop({'id': 107, 'kind': 'q', 'title': 'The Lost Supplies', 'action': 'kill', 'targetName': 'Scout'})
        facts = self.lua.table_from({'stop': stop, 'action': 'kill', 'target': 'Scout', 'amount': '2 '})
        card = self.present(stop, facts)
        lines = self.ns.GuidePresentationTooltipLines(card, False)
        self.assertLessEqual(len(lines) + 1, 6)  # The tooltip title is the sixth line at most.
        self.assertNotIn(card.what, list(lines.values()))
        self.assertNotIn(card.why, list(lines.values()))
        for field in (card.what, card.why, card.status, card.stepLine, card.location):
            if field:
                self.assertNotRegex(field, r'[.!]+$')

    def test_superseded_meta_prompts_are_removed(self):
        checks = {
            'WowTogether/GuideText.lua': (
                'Follow the travel instructions for this leg.',
                'Check the guide status below.',
            ),
            'WowTogether/TravelNetwork.lua': (
                'The route re-plans after you arrive.',
                'Continue towards your guide destination.',
                '; the map line follows it.',
            ),
            'WowTogether/LevelingGuides.lua': ('Follow your class quest guide.',),
            'WowTogether/GuideReasons.lua': ('this saved or previewed step can be skipped',),
        }
        for name, phrases in checks.items():
            source = (ROOT / name).read_text()
            for phrase in phrases:
                self.assertNotIn(phrase, source)


if __name__ == '__main__':
    unittest.main()
