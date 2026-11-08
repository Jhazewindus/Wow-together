"""Guard the known dungeon quests whose prequest has a higher minimum level."""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from audit_dungeon_level_gates import scan
from test_0817 import shipped, groups


HIGHER_LEVEL_PREQUESTS = (
    ('city-of-dalaran', 92432, 92457, 30, 24),  # An Alarming Request → Starving Arcane
    ('city-of-dalaran', 92432, 92458, 30, 24),  # An Alarming Request → Heart of Disruption
    ('city-of-dalaran', 92434, 96984, 30, 24),  # Blood in the Streets → Heart of Disruption
    ('gnomeregan', 2841, 2842, 25, 20),         # Rig Wars → Chief Engineer Scooty
    ('the-stockade', 303, 378, 25, 22),         # The Dark Iron War → The Fury Runs Deep
)


class DungeonLevelGateTests(unittest.TestCase):
    def test_audit_scans_the_whole_catalogue_and_reports_review_gaps(self):
        report = scan()
        self.assertEqual(report['counts'], {
            'dungeonCategories': 28,
            'listedQuestMemberships': 382,
            'uniqueListedQuests': 382,
            'missingCatalogueRecords': 0,
            'higherMinimumPrerequisiteEdges': 5,
            'unverifiedPrerequisiteMemberships': 2,
        })
        actual = {(edge['parentQuestID'], edge['questID'])
                  for edge in report['higherMinimumPrerequisites']}
        expected = {(parent, child) for _, parent, child, _, _ in HIGHER_LEVEL_PREQUESTS}
        self.assertEqual(actual, expected)

    def test_known_higher_level_prequests_remain_linked_and_gate_the_child(self):
        c = shipped(60)
        dungeon_groups = groups(c)
        for dungeon, parent_id, child_id, parent_level, child_level in HIGHER_LEVEL_PREQUESTS:
            with self.subTest(dungeon=dungeon, parent=parent_id, child=child_id):
                self.assertIn(child_id, {int(i) for i in dungeon_groups[dungeon].ids.values()})
                parent, child = c.ns.CatalogueQuest(parent_id), c.ns.CatalogueQuest(child_id)
                self.assertGreater(parent.minLevel, child.minLevel)
                self.assertEqual((parent.minLevel, child.minLevel), (parent_level, child_level))
                relations = [int(child.previousQuest)] if child.previousQuest else []
                relations.extend(int(i) for i in (child.prerequisiteAll or {}).values())
                relations.extend(int(i) for i in (child.prerequisiteAny or {}).values())
                self.assertIn(parent_id, relations)
                c.ns.profile.level = child_level
                allowed, reason = c.ns.CataloguePrerequisitesAllowed(child_id, c.ns.self)
                self.assertFalse(allowed)
                self.assertIn(parent.title, reason)

    def test_blood_in_the_streets_relation_retains_capture_provenance(self):
        c = shipped(26)
        source = c.ns.CatalogueQuest(96984).prerequisiteSource
        self.assertIn('wowhead.com/forever/quest=96984', source)
        self.assertIn('ef5a1ca0bbc3a807d53dc35deb5e26f76080abcc7341727388432397b21025b7', source)


if __name__ == '__main__':
    unittest.main()
