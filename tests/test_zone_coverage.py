"""Focused guide audits retain supported Dun Morogh facts and honest gaps."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_addon import ROOT

sys.path.insert(0, str(ROOT / 'tools'))
from build_quest_dataset import own_lua


class ZoneCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        cls.output = Path(cls.folder.name) / 'audit.json'
        cls.command = [sys.executable, str(ROOT / 'tools/audit_quest_guides.py')]
        cls.completed = subprocess.run(
            [*cls.command, '--zone', 'Dun Morogh', '--output', str(cls.output), '--require-complete'],
            cwd=ROOT, capture_output=True, text=True, timeout=120)
        if not cls.output.exists():
            raise AssertionError(cls.completed.stdout + cls.completed.stderr)
        cls.report = json.loads(cls.output.read_text())
        cls.quests = own_lua(ROOT / 'WowTogether/QuestCatalogue.lua', 'catalogue')['quests']
        cls.review = json.loads((ROOT / 'research/2026-10-08-dun-morogh-review.json').read_text())

    def test_one_zone_compiles_both_chapters_without_claiming_completeness(self):
        self.assertEqual(self.completed.returncode, 2, self.completed.stderr)
        self.assertIn('INCOMPLETE: 2 guides', self.completed.stderr)
        self.assertEqual(self.report['scope']['zone'], 'Dun Morogh')
        self.assertEqual(self.report['fixed_zone_guides_checked'], 2)
        self.assertEqual(self.report['source_data_gap_free_guides'], 0)
        self.assertEqual({g['zone'] for g in self.report['guides']}, {'Dun Morogh'})
        self.assertEqual({g['key'].split(':')[-1]: g['steps'] for g in self.report['guides']},
                         {'1-10': 151, '11-20': 30})
        self.assertTrue(all(g['flow_state_valid'] for g in self.report['guides']))

    def test_record_and_point_counts_are_scoped_to_the_selected_zone(self):
        quests = [q for q in self.quests.values() if q.get('zone') == 'Dun Morogh']
        self.assertGreater(len(quests), 0)
        self.assertLess(len(quests), len(self.quests))
        self.assertEqual(self.report['quest_records'], len(quests))
        points = sum(len(q.get(role, [])) for q in quests for role in ('starts', 'objectives', 'ends'))
        self.assertEqual(self.report['static_points_checked'], points)

    def test_a_scoped_run_cannot_overwrite_the_full_audit(self):
        full = ROOT / 'WowTogether/GuideAudit.json'
        before = full.read_bytes()
        for output in ([], ['--output', str(full)]):
            with self.subTest(output=output):
                result = subprocess.run([*self.command, '--zone', 'Dun Morogh', *output],
                                        cwd=ROOT, capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 2)
                self.assertIn('preserve the full GuideAudit.json', result.stderr)
        self.assertEqual(full.read_bytes(), before)

    def test_unknown_zone_fails_without_replacing_an_existing_report(self):
        output = Path(self.folder.name) / 'unknown.json'
        output.write_text('existing report')
        result = subprocess.run([*self.command, '--zone', 'Unknown test zone', '--output', str(output)],
                                cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Unknown catalogue zone', result.stderr)
        self.assertEqual(output.read_text(), 'existing report')

    def test_senir_records_keep_distinct_givers_and_prerequisites(self):
        first, second = self.quests[282], self.quests[420]
        self.assertEqual(first['previousQuest'], 218)
        self.assertTrue(first['prerequisitesUnverified'])
        self.assertEqual(second['previousQuest'], 282)
        self.assertEqual([p['entityID'] for p in first['startRefs']], [786])
        self.assertEqual([p['entityID'] for p in first['endRefs']], [1965])
        self.assertEqual([p['entityID'] for p in second['startRefs']], [1965])
        self.assertEqual([p['entityID'] for p in second['endRefs']], [1252])

    def test_quarry_preserves_counts_boar_spawn_and_unmapped_copper(self):
        quest = self.quests[95217]
        self.assertEqual({r['entityID']: r['quantity'] for r in quest['requirements']},
                         {2840: 12, 267416: 4})
        point, = quest['objectives']
        self.assertEqual((point['entityID'], point['itemID'], point['action']), (1689, 267416, 'loot'))
        self.assertEqual(point['mapID'], 1426)
        self.assertAlmostEqual(point['x'], .738)
        self.assertAlmostEqual(point['y'], .526)
        self.assertTrue(quest['objectiveLocationsIncomplete'])
        self.assertEqual([r['entityID'] for r in quest['missingRequirements']], [2840])

    def test_treaty_starter_does_not_invent_a_pickup_location(self):
        quest = self.quests[98423]
        self.assertEqual([(r['entityType'], r['entityID']) for r in quest['startRefs']], [('item', 281030)])
        self.assertFalse(quest.get('starts'))
        self.assertEqual([r['entityID'] for r in quest['endRefs']], [2784])
        self.assertEqual(quest['ends'][0]['mapID'], 1455)

    def test_review_sources_match_pinned_hashes_and_all_remaining_needs(self):
        manifest = json.loads((ROOT / 'tools/forever_source_manifest.json').read_text())
        self.assertEqual(self.review['source_commit'], manifest['commit'])
        for source in self.review['files']:
            self.assertEqual(source['sha256'], manifest['files_sha256'][source['path']])
            self.assertIn(manifest['commit'], source['url'])
        queue = json.loads((ROOT / 'WowTogether/GuideSourceQueue.json').read_text())
        actual = {r['questID']: r['needs'] for r in queue['quests'] if 'Alliance / Dun Morogh' in r['guides']}
        self.assertEqual({r['questID']: r['needs'] for r in self.review['remaining_needs']}, actual)


if __name__ == '__main__':
    unittest.main()
