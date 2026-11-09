"""Packaging contracts used by CI and addon installers."""
import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('builder', ROOT / 'tools/build_release.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BuildAutomationTests(unittest.TestCase):
    def test_missing_declared_source_fails_even_in_data_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'WowTogether_QuestData'
            folder.mkdir()
            (folder / (folder.name + '.toc')).write_text('## Interface: 16001\nMissing.lua\n')
            with self.assertRaisesRegex(ValueError, 'Missing or invalid TOC source'):
                builder.toc_sources(folder)
            (folder / (folder.name + '.toc')).write_text('../Escape.lua\n')
            with self.assertRaises(ValueError):
                builder.toc_sources(folder)

    def test_beta_name_is_safe_and_unmistakable(self):
        self.assertEqual(builder.archive_name('1.2.3', 'core/ui-chips', 'abcdef1234567890'),
                         'WowTogether-beta-core-ui-chips-abcdef123456.zip')
        self.assertEqual(builder.archive_name('1.2.3'), 'WowTogether-1.2.3.zip')
        with self.assertRaises(ValueError):
            builder.archive_name('1.2.3', '...', 'abcdef1')

    def test_real_archive_has_only_the_four_addon_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('sys.argv', ['build_release.py', '--output', tmp, '--label', 'core/test', '--sha', 'abcdef123456']):
                with contextlib.redirect_stdout(io.StringIO()): builder.main()
            archive = next(Path(tmp).glob('*.zip'))
            self.assertEqual(archive.name, 'WowTogether-beta-core-test-abcdef123456.zip')
            with zipfile.ZipFile(archive) as z:
                self.assertEqual({p.split('/')[0] for p in z.namelist()},
                    {'WowTogether', 'WowTogether_QuestData', 'WowTogether_ProfessionData', 'WowTogether_DungeonData'})
                self.assertTrue(all('/' in p and not p.startswith('/') and '..' not in p.split('/') for p in z.namelist()))
                icons = {p for p in z.namelist() if p.startswith('WowTogether/Media/Icons/')}
                self.assertEqual(len(icons), 21)  # Manifest plus twenty generated textures.
                self.assertIn('WowTogether/Media/Icons/kill.tga', icons)

    def test_oversize_splits_without_losing_or_rewriting_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / 'WowTogether-1.2.3.zip'
            files = {'WowTogether/Core.lua': b'core', 'WowTogether_QuestData/QuestCatalogue.lua': b'data'}
            with zipfile.ZipFile(archive, 'w') as z:
                for name, body in files.items(): z.writestr(name, body)
            outputs = builder.split_archive(archive, limit=250)
            self.assertEqual([p.name for p in outputs], ['WowTogether-1.2.3.zip', 'WowTogether-data-1.2.3.zip'])
            actual = {}
            for output in outputs:
                with zipfile.ZipFile(output) as z: actual.update({n: z.read(n) for n in z.namelist()})
            self.assertEqual(actual, files)

    def test_single_oversize_package_fails_instead_of_uploading(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / 'WowTogether-1.2.3.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('WowTogether/Core.lua', b'x' * 1000)
            with self.assertRaisesRegex(ValueError, 'still exceeds'):
                builder.split_archive(archive, limit=100)
            self.assertTrue(archive.exists())

    def test_split_builder_output_is_accepted_by_discord_preparation(self):
        from test_ci_release import build
        from ci_release import prepare
        for kind, name in (('release', 'WowTogether-1.2.3.zip'),
                           ('beta', 'WowTogether-beta-core-test-123abcd.zip')):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                archive = root / name
                build(archive)
                outputs = builder.split_archive(archive, limit=archive.stat().st_size - 1)
                self.assertEqual(len(outputs), 2)
                options = {'branch': 'core/test', 'pr': '42', 'title': 'Test'} if kind == 'beta' else {}
                _, files, _, _ = prepare(root, kind, **options)
                self.assertEqual({name for name, _ in files}, {p.name for p in outputs})
