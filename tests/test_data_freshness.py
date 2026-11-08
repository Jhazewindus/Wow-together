import unittest

from test_addon import Client
from tools.diff_catalogue import diff


class CatalogueFreshnessTests(unittest.TestCase):
    def test_probe_freshness_warns_after_21_days_and_reports_capture_build(self):
        c = Client(quests=())
        c.ns.catalogue.meta = c.lua.table_from({'captured': '2026-10-01', 'build': '70009', 'count': 8})
        c.lua.execute('time=function(value) if value then return 1000 end return 1000 + 25*86400 end')
        text = c.ns.CatalogueFreshnessText()
        self.assertIn('2026-10-01 (25 days ago)', text)
        self.assertIn('build 70009', text)
        self.assertIn('Data may predate the current patch', text)

    def test_diff_lists_only_actual_quest_changes_and_guide(self):
        old = {'captured': 'old', 'quests': {'10': {'title': 'Known Quest', 'zone': 'The Barrens', 'level': 12},
                                            '11': {'title': 'Removed Quest'}}}
        new = {'captured': 'new', 'quests': {'10': {'title': 'Known Quest', 'zone': 'The Barrens', 'level': 13},
                                            '12': {'title': 'Added Quest'}}}
        audit = {'guides': [{'faction': 'Horde', 'zone': 'The Barrens', 'key': 'level-zone:the-barrens:levels:11-20'}]}
        changes = diff(old, new, audit)
        self.assertEqual([row['questID'] for row in changes], [10, 11, 12])
        self.assertIn('level', changes[0]['change'])
        self.assertEqual(len(changes[0]['guides']), 1)
        self.assertEqual(changes[1]['change'], 'removed')
        self.assertEqual(changes[2]['change'], 'added')

    def test_diff_reports_npc_moves_only_when_map_scale_supports_yard_math(self):
        old_q = {'title': 'Moved', 'zone': 'Durotar', 'starts': [{'entityType': 'npc', 'entityID': 5,
                  'mapID': 1, 'x': .1, 'y': .1}]}
        new_q = {'title': 'Moved', 'zone': 'Durotar', 'starts': [{'entityType': 'npc', 'entityID': 5,
                  'mapID': 1, 'x': .2, 'y': .1}]}
        old = {'quests': {'1': old_q}, 'mapWorldSizes': {'1': {'width': 1000, 'height': 1000}}}
        new = {'quests': {'1': new_q}, 'mapWorldSizes': {'1': {'width': 1000, 'height': 1000}}}
        changes, = diff(old, new)
        self.assertIn('NPC 5 moved 100 yd', changes['change'])


if __name__ == '__main__':
    unittest.main()
