"""The November source sweep supplies routable dungeon prerequisite parents."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from audit_dungeon_level_gates import scan
from build_quest_dataset import own_lua
from import_warcraftdb import apply_corrections


class DungeonPrerequisiteSweepTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue = own_lua(ROOT / 'WowTogether_QuestData/QuestCatalogue.lua', 'catalogue')
        cls.quests = cls.catalogue['quests']
        cls.sweep = json.loads((ROOT / 'research/dungeon-prerequisite-sweep-2026-11-28.json').read_text())

    def test_all_current_dungeon_gates_are_resolved(self):
        report = scan()
        self.assertEqual(report['counts']['unverifiedPrerequisiteMemberships'], 0)
        self.assertEqual(report['unverifiedPrerequisiteMemberships'], [])

    def test_new_linear_series_relations_match_the_capture_manifest(self):
        for row in self.sweep['newlyVerifiedEdges']:
            with self.subTest(quest=row['questID']):
                quest = self.quests[row['questID']]
                self.assertEqual(quest['previousQuest'], row['previousQuest'])
                self.assertTrue(quest['prerequisitesRead'])
                self.assertIn(row['url'], quest['prerequisiteSource'])
                self.assertIn(row['sha256'], quest['prerequisiteSource'])

    def test_new_parent_quest_is_reproducible_and_links_the_razorfen_chain(self):
        parent = self.quests[93601]
        self.assertEqual(parent['title'], 'Passing the Blame')
        self.assertEqual(parent['previousQuest'], 93404)
        self.assertEqual(parent['starts'][0]['name'], 'Woodwyrd')
        self.assertEqual(parent['ends'][0]['name'], "Kog'thug the Brave")
        self.assertEqual(self.quests[93604]['previousQuest'], 93601)
        self.assertEqual(parent['zone'], "Shen'dralas")

        rebuilt = {93404: self.quests[93404]}
        apply_corrections(rebuilt)
        self.assertEqual(rebuilt[93601]['title'], 'Passing the Blame')
        self.assertEqual(rebuilt[93601]['previousQuest'], 93404)

    def test_kroldok_prechain_is_routable_with_group_gates(self):
        expected = {
            94483: [93786, 93787],
            94727: [94672, 94680],
            95427: [95601, 95602],
            95428: [95424, 95425],
            94768: [94745, 94748],
        }
        for quest_id, parents in expected.items():
            with self.subTest(quest=quest_id):
                quest = self.quests[quest_id]
                self.assertEqual(quest['prerequisiteAll'], parents)
                self.assertTrue(quest['starts'])
                self.assertTrue(quest['ends'])
                self.assertTrue(quest['prerequisitesRead'])
        for quest_id, parent in {94672: 94483, 94680: 94483, 95417: 94727,
                                 95601: 95417, 95602: 94727, 95418: 95427,
                                 95420: 95418, 95424: 95420, 95425: 95420,
                                 94744: 95428, 94745: 94744, 94748: 94744,
                                 95278: 94768, 94975: 94768, 94968: 95278,
                                 94972: 95278}.items():
            with self.subTest(quest=quest_id):
                self.assertEqual(self.quests[quest_id]['previousQuest'], parent)
        for quest_id in (94975, 94968, 94972):
            self.assertTrue(self.quests[quest_id]['starts'])
            self.assertTrue(self.quests[quest_id]['ends'])
            self.assertTrue(self.quests[quest_id]['objectiveLocationsIncomplete'])

    def test_breadcrumb_and_false_series_edge_stay_out_of_the_route(self):
        tiara = self.quests[2846]
        self.assertNotIn('previousQuest', tiara)
        self.assertFalse(tiara.get('prerequisitesUnverified', False))
        self.assertEqual(self.quests[95682]['previousQuest'], 95663)
        self.assertFalse(self.quests[95682].get('prerequisitesUnverified', False))
        self.assertNotIn('previousQuest', self.quests[6563])

    def test_sweep_records_all_memberships_and_refused_pages(self):
        scope = self.sweep['scope']
        self.assertEqual(scope['uniqueListedQuestIDs'], 380)
        self.assertEqual(scope['pagesCaptured'], 369)
        self.assertEqual(scope['pagesUnavailableCurrentSweep'], 11)
        self.assertEqual(self.sweep['overviewGuideSweep']['capturedGuides'], 21)
        self.assertEqual(self.sweep['overviewGuideSweep']['requestedGuides'], 28)
        self.assertEqual(len(self.sweep['memberships']), 380)
        self.assertEqual(sum(row['status'] == 200 for row in self.sweep['memberships']), 366)

    def test_wetlands_guide_gates_and_breadcrumb_exception_are_recorded(self):
        expected = {
            98815: 484,
            95646: 275,
            95647: 95737,
            98824: 95810,
            98823: 95664,
        }
        for child_id, parent_id in expected.items():
            with self.subTest(child=child_id):
                self.assertEqual(self.quests[child_id]['previousQuest'], parent_id)
                self.assertTrue(self.quests[child_id]['prerequisitesRead'])
                self.assertIn('Wowhead Forever', self.quests[child_id]['prerequisiteSource'])
        self.assertNotIn('previousQuest', self.quests[484])
        self.assertFalse(self.quests[484].get('prerequisitesUnverified', False))
        self.assertEqual(self.quests[275]['previousQuest'], 277)
        self.assertEqual(self.quests[277]['previousQuest'], 276)
        self.assertEqual(self.quests[276]['previousQuest'], 463)


if __name__ == '__main__':
    unittest.main()
