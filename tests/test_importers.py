"""Source parsing checks use small public-format fixtures, without network calls."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from import_wowhead import base_facts, category_paths, detail_facts, list_rows, series_ids
from import_warcraftdb import normalize, generate


def detail(points, missing=0):
    return '$.extend(g_quests[42], ' + json.dumps({'id': 42, 'name': 'Test', 'category': 14}) + ');' \
        + 'new Mapper(' + json.dumps({'objectives': {'14': {'zone': 'Durotar', 'levels': [points]}}, 'missing': missing}) + ');'


class ImportTests(unittest.TestCase):
    def test_list_requires_json_and_preserves_minimum_level_and_faction(self):
        page = "new Listview({template: 'quest', data: " + json.dumps([{'id': 42, 'name': 'Test', 'level': 12, 'reqlevel': 4, 'side': 2}]) + '});'
        facts = base_facts(list_rows(page)[0])
        self.assertEqual((facts['level'], facts['minLevel'], facts['side']), (12, 4, 'Horde'))
        with self.assertRaises(ValueError):
            list_rows("new Listview({template: 'quest', data: executeSomething()});")

    def test_area_ids_are_never_used_as_ui_map_ids(self):
        page = detail([{'point': 'start', 'id': 7, 'type': 1, 'name': 'NPC', 'coord': [55.2, 75.4]}])
        self.assertNotIn('starts', detail_facts(page, {'id': 42}, {}))
        mapped = detail_facts(page, {'id': 42}, {14: 1411})
        self.assertEqual(mapped['starts'][0]['mapID'], 1411)
        self.assertAlmostEqual(mapped['starts'][0]['x'], .552)

    def test_direct_entity_objectives_and_alternative_item_sources(self):
        points = [{'point': 'requirement', 'objective': 3111, 'id': 3111, 'name': 'Kill target', 'coord': [50, 40]},
                  {'point': 'sourcerequirement', 'objective': 0, 'id': 7, 'name': 'Possible drop A', 'coord': [30, 20]},
                  {'point': 'sourcerequirement', 'objective': 0, 'id': 8, 'name': 'Possible drop B', 'coord': [70, 80]}]
        facts = detail_facts(detail(points), {'id': 42}, {14: 1411})
        self.assertEqual(len(facts['objectives']), 2)
        self.assertEqual(facts['objectives'][0]['entityID'], 3111)
        self.assertNotIn('objectiveLocationsIncomplete', facts)
        self.assertEqual(len(facts['objectiveAlternatives'][0]['locations']), 2)
        self.assertNotIn('objectiveIndex', facts['objectives'][0])

    def test_branching_series_is_not_invented_as_linear_prerequisites(self):
        linear = '<table class="series"><tr><a href="/forever/quest=40">A</a></tr><tr><b>Current</b></tr><tr><a href="/forever/quest=43">C</a></tr></table>'
        self.assertEqual(series_ids(linear, 42), [40, 42, 43])
        branch = linear.replace('<b>Current</b>', '<a href="/forever/quest=41">B</a><a href="/forever/quest=42">C</a>')
        self.assertEqual(series_ids(branch, 42), [])

    def test_absent_metadata_is_not_filled_with_fake_locations(self):
        facts = normalize({'record_id': 42, 'name': 'Unknown'}, {'data': {}})
        self.assertNotIn('starts', facts)
        self.assertNotIn('mapID', facts)
        self.assertNotIn('side', facts)
        self.assertTrue(generate({42: facts}, '2026-10-04').startswith('local addonName, ns = ...'))

    def test_category_tree_uses_published_leaf_paths_and_rejects_foreign_paths(self):
        tree = {'categories': [{'url': 'kalimdor', 'categories': [{'url': 'durotar'}, {'url': 'the-barrens'}]},
                              {'url': 'https://another-host.test'}, {'url': '../escape'}]}
        self.assertEqual(category_paths('Filter.init(' + json.dumps(tree) + ');'),
                         ['kalimdor/durotar', 'kalimdor/the-barrens'])

    def test_map_entity_roles_do_not_invent_kill_targets_for_items_or_friendly_npcs(self):
        points = [{'point': 'requirement', 'objective': 100, 'id': 100, 'type': 1,
                   'reacthorde': -1, 'name': 'Enemy', 'coord': [50, 50]},
                  {'point': 'sourcerequirement', 'objective': 1, 'id': 200, 'type': 1,
                   'item': 'Drop', 'name': 'Drop source', 'coord': [60, 60]},
                  {'point': 'requirement', 'objective': 300, 'id': 300, 'type': 1,
                   'reacthorde': 1, 'name': 'Friendly', 'coord': [70, 70]}]
        facts = detail_facts(detail(points), {'id': 42}, {14: 1411})
        self.assertEqual(facts['objectives'][0]['action'], 'kill')
        self.assertEqual(facts['objectives'][1]['action'], 'collect')
        self.assertEqual(facts['objectives'][1]['itemName'], 'Drop')
        self.assertNotIn('action', facts['objectives'][2])

if __name__ == '__main__':
    unittest.main()
