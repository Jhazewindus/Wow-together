"""CI publication validates metadata and sends ZIP bytes, without real webhooks."""
import io
import contextlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import zipfile
from email import policy
from email.parser import BytesParser
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from ci_release import (PublicationError, archive_metadata, blocks, message_for,
                        main, post, preflight, prepare, section_for)

HOOK = 'https://discord.com/api/webhooks/123/synthetic-token'
SECTION = '''**CLEAR GUIDANCE**
For players:
- Routes update in short steps.
Please check:
- Rescan a zone guide.
Developer notes:
- Memoize policy work.
'''
ROOTS = ['WowTogether', 'WowTogether_QuestData', 'WowTogether_ProfessionData', 'WowTogether_DungeonData']


def build(path, roots=ROOTS, section=SECTION):
    with zipfile.ZipFile(path, 'w') as archive:
        for folder in roots:
            archive.writestr(folder + '/test.lua', 'local addonName, ns = ...')
        if 'WowTogether' in roots:
            archive.writestr('WowTogether/WowTogether.toc', '## Version: 1.2.3\n## X-ReleaseName: CLEAR GUIDANCE\n')
            archive.writestr('WowTogether/CHANGELOG.md', '# Changelog\n## 1.2.3\n' + section + '\n## 1.0.0\n- Older\n')


class Transport:
    def __init__(self, filenames, failure=None):
        self.filenames = filenames
        self.failure = failure
        self.requests = []

    def open(self, request, timeout):
        self.requests.append(request)
        if self.failure:
            raise self.failure
        return io.BytesIO(json.dumps({'id': '456', 'channel_id': '789',
            'attachments': [{'filename': name} for name in self.filenames]}).encode())


class CIReleaseTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.archive = self.root / 'WowTogether-1.2.3.zip'
        build(self.archive)

    def test_release_upload_contains_only_zip_and_confirmed_receipt(self):
        message, files, boundary, body = prepare(self.root, 'release')
        parsed = BytesParser(policy=policy.default).parsebytes(
            ('Content-Type: multipart/form-data; boundary=' + boundary + '\r\n\r\n').encode() + body)
        parts = list(parsed.iter_parts())
        self.assertEqual(len(parts), 2)
        payload = json.loads(parts[0].get_payload(decode=True))
        self.assertEqual(payload['allowed_mentions'], {'parse': []})
        self.assertEqual(parts[1].get_filename(), self.archive.name)
        self.assertEqual(parts[1].get_payload(decode=True), self.archive.read_bytes())
        self.assertTrue(message.startswith('**Wow Together 1.2.3 — CLEAR GUIDANCE**'))
        self.assertIn('World of Warcraft: Forever (live)', message)
        self.assertIn('||Developer notes:\n- Memoize policy work.||', message)
        self.assertEqual(message.count('Rescan a zone guide.'), 1)
        self.assertNotIn('Older', message)
        transport = Transport([self.archive.name])
        receipt = post(self.root, 'release', HOOK, transport)
        self.assertEqual(receipt['message_id'], '456')
        self.assertEqual(len(transport.requests), 1)
        self.assertTrue(transport.requests[0].full_url.endswith('?wait=true'))
        stored = (self.root / 'discord-receipt.json').read_text()
        self.assertNotIn('synthetic-token', stored)

    def test_beta_names_branch_pr_title_and_player_checks(self):
        beta = self.root / 'WowTogether-beta-core-ui-chips-123abcd.zip'
        self.archive.rename(beta)
        message, files, _, _ = prepare(self.root, 'beta', branch='core/ui-chips', pr='42', title='Suggestion chips')
        self.assertTrue(message.startswith('**Beta build — `core/ui-chips` (#42) — not a release**'))
        self.assertIn('Suggestion chips', message)
        self.assertIn('Routes update', message)
        self.assertIn('Please check:', message)
        self.assertEqual(files[0][0], beta.name)
        self.assertNotIn('Developer notes', message)

    def test_beta_diff_fallback_uses_at_most_ten_lines(self):
        message = message_for('beta', '1.2.3', 'TEST', '- No structured notes', [],
            branch='core/test', pr='2', title='Test', diff='\n'.join('+change' + str(index) for index in range(15)))
        self.assertIn('change9', message)
        self.assertNotIn('change10', message)

    def test_split_build_posts_both_zips_in_one_message(self):
        build(self.archive, roots=['WowTogether'])
        data = self.root / 'WowTogether-data-1.2.3.zip'
        build(data, roots=ROOTS[1:])
        message, files, _, _ = prepare(self.root, 'release')
        self.assertEqual(len(files), 2)
        self.assertIn('Install both ZIPs', message)
        transport = Transport([self.archive.name, data.name])
        post(self.root, 'release', HOOK, transport)
        self.assertEqual(len(transport.requests), 1)

    def test_incomplete_receipt_and_network_errors_do_not_retry(self):
        for failure in [None, TimeoutError(), urllib.error.URLError('synthetic-token'),
                        urllib.error.HTTPError(HOOK, 403, 'synthetic-token', {}, None)]:
            transport = Transport([], failure)
            with self.assertRaises(PublicationError) as caught:
                post(self.root, 'release', HOOK, transport)
            self.assertNotIn('synthetic-token', str(caught.exception))
            self.assertEqual(len(transport.requests), 1)
            self.assertFalse((self.root / 'discord-receipt.json').exists())

    def test_confirmed_upload_with_receipt_write_failure_warns_against_repost(self):
        transport = Transport([self.archive.name])
        with patch.object(Path, 'write_text', side_effect=OSError('synthetic-token')):
            with self.assertRaisesRegex(PublicationError, 'confirmed message 456.*Do not repost'):
                post(self.root, 'release', HOOK, transport)
        self.assertEqual(len(transport.requests), 1)

    def test_dry_run_previews_without_a_webhook_or_network_request(self):
        output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), patch('sys.argv', [
                'ci_release.py', 'post', '--kind', 'release', '--dist', str(self.root), '--dry-run']), \
                patch('urllib.request.build_opener', side_effect=AssertionError('network forbidden')), \
                contextlib.redirect_stdout(output):
            main()
        self.assertIn('**Wow Together 1.2.3', output.getvalue())
        self.assertIn('Attachments: WowTogether-1.2.3.zip', output.getvalue())
        self.assertIn('no request sent', output.getvalue())
        self.assertFalse((self.root / 'discord-receipt.json').exists())

    def test_invalid_webhook_never_sends(self):
        transport = Transport([self.archive.name])
        with self.assertRaises(ValueError):
            post(self.root, 'release', 'https://other.invalid/synthetic-token', transport)
        self.assertEqual(transport.requests, [])

    def test_bad_layout_missing_data_and_missing_notes_are_rejected(self):
        with zipfile.ZipFile(self.archive, 'a') as package:
            package.writestr('../outside.txt', 'bad')
        with self.assertRaisesRegex(ValueError, 'addon folders'):
            archive_metadata([self.archive])
        build(self.archive, roots=['WowTogether'])
        with self.assertRaisesRegex(ValueError, 'sibling addon'):
            archive_metadata([self.archive])
        build(self.archive, section='- A developer change only')
        with self.assertRaisesRegex(ValueError, 'For players'):
            prepare(self.root, 'release')

    def test_version_and_message_size_guards(self):
        self.assertRaises(ValueError, section_for, '## 2.0.0\n', '1.2.3')
        self.assertRaises(ValueError, blocks, 'For players:\n- One\n- Two\n- Three\n- Four\nPlease check:\n- Test')
        with self.assertRaisesRegex(ValueError, '2,000'):
            message_for('release', '1.2.3', 'TEST', SECTION + '- ' + 'x' * 2100, [self.archive])
        self.archive.rename(self.root / 'wrong.zip')
        with self.assertRaisesRegex(ValueError, 'names'):
            prepare(self.root, 'release')

    def test_preflight_exports_notes_and_blocks_existing_tag(self):
        (self.root / 'WowTogether').mkdir()
        (self.root / 'WowTogether/WowTogether.toc').write_text('## Version: 1.2.3\n## X-ReleaseName: CLEAR GUIDANCE\n')
        (self.root / 'CHANGELOG.md').write_text('## 1.2.3\n' + SECTION)
        output = self.root / 'outputs'
        with patch.dict(os.environ, {'GITHUB_OUTPUT': str(output)}):
            version, name, notes = preflight(self.root, self.root / 'notes.md',
                lambda *args, **kwargs: SimpleNamespace(returncode=1))
        self.assertEqual(version, '1.2.3')
        self.assertEqual((self.root / 'notes.md').read_text().strip(), SECTION.strip())
        self.assertIn('version=1.2.3', output.read_text())
        with self.assertRaisesRegex(ValueError, 'already exists'):
            preflight(self.root, self.root / 'notes.md', lambda *a, **k: SimpleNamespace(returncode=0))
        with self.assertRaisesRegex(ValueError, 'tag history'):
            preflight(self.root, self.root / 'notes.md', lambda *a, **k: SimpleNamespace(returncode=128))


if __name__ == '__main__':
    unittest.main()
