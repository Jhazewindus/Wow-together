"""Scoped Swamp audit must cover title-cased guide labels without hiding gaps."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from test_addon import ROOT


class SwampCoverageTests(unittest.TestCase):
    def test_catalogue_spelling_compiles_all_faction_chapters_and_keeps_global_report(self):
        global_path = ROOT / 'WowTogether/GuideAudit.json'
        before = global_path.read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'audit.json'
            run = subprocess.run([sys.executable, str(ROOT / 'tools/audit_quest_guides.py'),
                                  '--zone', 'Swamp of Sorrows', '--output', str(output),
                                  '--require-complete'], cwd=ROOT, capture_output=True,
                                 text=True, timeout=120)
            self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
            report = json.loads(output.read_text())
        self.assertEqual(global_path.read_bytes(), before)
        self.assertEqual(report['fixed_zone_guides_checked'], 6)
        chapters = {(g['faction'], g['key'].split(':')[-1]): g['steps'] for g in report['guides']}
        self.assertEqual(chapters, {('Horde','31-40'):51, ('Horde','41-50'):43,
                                   ('Horde','51-60'):21, ('Alliance','31-40'):42,
                                   ('Alliance','41-50'):14, ('Alliance','51-60'):9})
        gaps = {s: set() for s in ('a','q','t')}
        quantities = set()
        for guide in report['guides']:
            self.assertTrue(guide['flow_state_valid'])
            for stage, ids in guide['missing_location_quest_ids_by_stage'].items():
                gaps[stage].update(ids)
            quantities.update(guide['unverified_objective_quantity_quest_ids'])
        self.assertEqual(gaps['a'], {93429,93430,93464})
        self.assertEqual(gaps['q'], {3374,93176,93429,93464,93585,93663})
        self.assertEqual(gaps['t'], {93429,93430,93464,93585})
        self.assertEqual(quantities, {3374})
