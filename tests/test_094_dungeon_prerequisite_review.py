"""Current dungeon prerequisite review preserves exact quest variants."""
import json
from pathlib import Path
import sys
import unittest

from test_0817 import shipped, groups

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from audit_dungeon_level_gates import scan
from build_quest_dataset import own_lua


class DungeonPrerequisiteReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.quests = own_lua(ROOT / 'WowTogether_QuestData' / 'QuestCatalogue.lua', 'catalogue')['quests']

    def test_only_the_two_conflicting_gates_remain_unverified(self):
        report = scan()
        self.assertEqual(report['counts']['unverifiedPrerequisiteMemberships'], 2)
        self.assertEqual({row['questID'] for row in report['unverifiedPrerequisiteMemberships']}, {2846, 95682})

    def test_known_prerequisite_variants_use_their_specific_parent(self):
        parents = {
            5127: 5126,
            8966: 8962, 8967: 8963, 8968: 8964, 8969: 8965,
            8989: 8986, 8990: 8985, 8991: 8987, 8992: 8988,
            2952: 2951, 2953: 2952, 4603: 4605, 4604: 4606,
            4605: 4601, 4606: 4602,
            3375: 2201, 8733: 8555,
        }
        for child_id, parent_id in parents.items():
            with self.subTest(child=child_id):
                child = self.quests[child_id]
                self.assertEqual(child['previousQuest'], parent_id)
                self.assertFalse(child.get('prerequisiteAny'))
                self.assertFalse(child.get('prerequisitesUnverified', False))
                self.assertTrue(child['prerequisitesRead'])
                self.assertIn(f'quest={child_id}', child['prerequisiteSource'])

    def test_review_manifest_keeps_page_hashes_and_conflicts(self):
        audit = json.loads((ROOT / 'research/dungeon-prerequisite-audit-2026-11-08.json').read_text())
        self.assertEqual(audit['scope']['reviewedFormerlyUnverifiedMemberships'], 27)
        self.assertEqual(audit['scope']['currentWowheadPagesRetrieved'], 27)
        self.assertEqual(audit['sources']['questieCommit'], '0f7d8adc92b28ac6594f4ad8745257f4d9784edf')
        for row in audit['reviewedMemberships']:
            with self.subTest(quest=row['questID']):
                expected_status = 'unresolved-conflicting-evidence' if row['questID'] in (2846, 95682) else 200
                self.assertEqual(row['status'], expected_status)
                self.assertRegex(row['sha256'], r'^[0-9a-f]{64}$')

    def test_dungeon_preparation_expands_a_verified_gnomeregan_parent(self):
        c = shipped(60)
        guide = c.ns.DungeonGuide(groups(c)['gnomeregan'])
        self.assertIsNotNone(guide)
        dependencies = guide.collectionDependencies[2952]
        self.assertIn(2951, {int(i) for i in dependencies.values()})
        self.assertTrue(guide.collectionRequired[2951])


if __name__ == '__main__':
    unittest.main()
