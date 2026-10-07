"""Discord wire format and confirmed-receipt checks; no real network requests."""
import io
import contextlib
import json
import sys
import tempfile
import unittest
import urllib.error
import zipfile
from email import policy
from email.parser import BytesParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from post_discord_release import PublicationError, content_digest, post_release, prepare

WEBHOOK = 'https://discord.com/api/webhooks/123/synthetic-token'


def release(path, note='A change', version='1.2.3'):
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('WowTogether/WowTogether.toc', '## Interface: 16001\n## Version: '+version+'\nCore.lua\n')
        z.writestr('WowTogether/Core.lua', 'local addonName, ns = ...\n')
        z.writestr('WowTogether/CHANGELOG.md', '# Changelog\n\n## '+version+'\n\n- '+note+'\n\n## 1.0.0\n\n- Older\n')
        z.writestr('WowTogether/TESTING.md', 'For **'+version+'**. Test this change.\n')


class Transport:
    def __init__(self, error=None, attachments=None):
        self.requests = []
        self.error = error
        self.attachments = attachments or ['WowTogether-1.2.3.zip', 'CHANGELOG.md', 'TESTING.md']

    def open(self, request, timeout):
        self.requests.append(request)
        if self.error:
            raise self.error
        return io.BytesIO(json.dumps({'id': '456', 'channel_id': '789',
            'attachments': [{'filename': n} for n in self.attachments]}).encode())


class DiscordReleaseTests(unittest.TestCase):
    def setUp(self):
        output = contextlib.redirect_stdout(io.StringIO())
        output.__enter__(); self.addCleanup(output.__exit__, None, None, None)
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.archive = Path(self.folder.name) / 'WowTogether-1.2.3.zip'
        release(self.archive)

    def test_upload_contains_exact_archive_docs_matching_ids_and_no_mentions(self):
        _, message, files, boundary, body = prepare(self.archive)
        parsed = BytesParser(policy=policy.default).parsebytes(
            ('Content-Type: multipart/form-data; boundary='+boundary+'\r\n\r\n').encode()+body)
        parts = list(parsed.iter_parts())
        payload = json.loads(parts[0].get_payload(decode=True))
        self.assertEqual(payload['allowed_mentions'], {'parse': []})
        self.assertIn('A change', message)
        self.assertNotIn('Older', message)
        self.assertEqual(len(parts), 4)
        for index, part in enumerate(parts[1:]):
            self.assertEqual(part.get_filename(), files[index][0])
            self.assertEqual(part.get_payload(decode=True), files[index][2])
            self.assertEqual(part.get_param('name', header='content-disposition'), f'files[{index}]')
            self.assertEqual(payload['attachments'][index]['id'], index)

    def test_confirmed_post_is_recorded_and_skipped_on_a_second_run(self):
        transport = Transport()
        first = post_release(self.archive, WEBHOOK, transport)
        second = post_release(self.archive, WEBHOOK, transport)
        self.assertEqual(first, second)
        self.assertEqual(len(transport.requests), 1)
        self.assertEqual(transport.requests[0].method, 'POST')
        self.assertTrue(transport.requests[0].full_url.endswith('?wait=true'))
        receipts = (self.archive.parent / 'discord-posts.json').read_text()
        self.assertIn('456', receipts)
        self.assertNotIn('synthetic-token', receipts)

    def test_long_notes_keep_complete_preview_bullets_and_exact_full_attachments(self):
        note = 'First complete change.\n- ' + ('A detailed later change. ' * 150)
        release(self.archive, note=note)
        _, message, files, _, _ = prepare(self.archive)
        self.assertLessEqual(len(message), 2000)
        self.assertIn('First complete change.', message)
        self.assertNotIn('A detailed later change.', message)
        self.assertIn('Full changelog attached.', message)
        self.assertIn('**Install:**', message)
        self.assertIn('**Testing:**', message)
        with zipfile.ZipFile(self.archive) as z:
            self.assertEqual(files[1][2], z.read('WowTogether/CHANGELOG.md'))
            self.assertEqual(files[2][2], z.read('WowTogether/TESTING.md'))

    def test_changed_contents_under_a_posted_version_require_a_new_version(self):
        transport = Transport()
        post_release(self.archive, WEBHOOK, transport)
        release(self.archive, note='Different change')
        with self.assertRaisesRegex(PublicationError, 'Bump the release version'):
            post_release(self.archive, WEBHOOK, transport)
        self.assertEqual(len(transport.requests), 1)

    def test_zip_timestamp_changes_do_not_change_release_identity(self):
        before = content_digest(self.archive)
        with zipfile.ZipFile(self.archive) as z:
            files = [(name, z.read(name)) for name in z.namelist()]
        with zipfile.ZipFile(self.archive, 'w') as z:
            for name, data in files:
                z.writestr(zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0)), data)
        self.assertEqual(content_digest(self.archive), before)

    def test_incomplete_attachment_confirmation_does_not_create_a_receipt(self):
        transport = Transport(attachments=['WowTogether-1.2.3.zip'])
        with self.assertRaisesRegex(PublicationError, 'confirm all three'):
            post_release(self.archive, WEBHOOK, transport)
        self.assertFalse((self.archive.parent / 'discord-posts.json').exists())

    def test_connection_and_http_failures_do_not_retry_or_expose_the_webhook(self):
        for error in (TimeoutError(), urllib.error.URLError('synthetic-token'),
                      urllib.error.HTTPError(WEBHOOK, 403, 'synthetic-token', {}, None)):
            transport = Transport(error=error)
            with self.assertRaises(PublicationError) as failure:
                post_release(self.archive, WEBHOOK, transport)
            self.assertNotIn('synthetic-token', str(failure.exception))
            self.assertEqual(len(transport.requests), 1)
            self.assertFalse((self.archive.parent / 'discord-posts.json').exists())

    def test_mismatched_testing_version_blocks_preparation(self):
        with zipfile.ZipFile(self.archive) as z:
            files = {name: z.read(name) for name in z.namelist()}
        files['WowTogether/TESTING.md'] = b'For **1.0.0**.'
        with zipfile.ZipFile(self.archive, 'w') as z:
            for name, data in files.items(): z.writestr(name, data)
        with self.assertRaisesRegex(ValueError, 'do not match'):
            prepare(self.archive)


if __name__ == '__main__':
    unittest.main()
