"""Post a verified Wow Together ZIP and its matching docs to a Discord webhook."""
import argparse
import getpass
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from pathlib import Path


class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class PublicationError(Exception):
    """A sanitized publication failure suitable for user-facing output."""


def prepare(archive):
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError('Release ZIP failed integrity verification.')
        toc = z.read('WowTogether/WowTogether.toc').decode()
        match = re.search(r'^## Version: (\d+\.\d+\.\d+)$', toc, re.M)
        if not match:
            raise ValueError('Release version is missing.')
        version = match.group(1)
        release_name = re.search(r'^## X-ReleaseName: ([A-Za-z0-9 -]{1,80})$', toc, re.M)
        release_label = version + (' — ' + release_name.group(1) if release_name else '')
        if not re.search(r'^## Interface: 16001$', toc, re.M):
            raise ValueError('Expected Forever beta interface 16001.')
        for name in toc.splitlines():
            if name.endswith('.lua'):
                z.getinfo('WowTogether/' + name)
        changelog = z.read('WowTogether/CHANGELOG.md')
        testing = z.read('WowTogether/TESTING.md')
    section = re.search(r'^## ' + re.escape(version) + r'\s*\n(.*?)(?=^## |\Z)',
                        changelog.decode(), re.M | re.S)
    if not section or ('**' + version + '**') not in testing.decode():
        raise ValueError('Changelog/test checklist do not match the release version.')
    message = ('**Wow Together ' + release_label + ' — Forever beta**\n\n'
               + section.group(1).strip()
               + '\n\n**Install:** replace the complete `WowTogether` folder on every party member’s client in '
               '`World of Warcraft\\_classic_beta_\\Interface\\AddOns\\WowTogether\\`, then fully restart the client. '
               'Restart the client if the addon folder does not appear.\n\n'
               '**Testing:** use the attached leveling checklist and report template. '
               'Host checks do not establish beta API/rendering compatibility.')
    if len(message) > 2000:
        raise ValueError('Message exceeds Discord’s content limit.')
    files = [(archive.name, 'application/zip', archive.read_bytes()),
             ('CHANGELOG.md', 'text/markdown', changelog),
             ('TESTING.md', 'text/markdown', testing)]
    payload = {'content': message, 'allowed_mentions': {'parse': []},
               'attachments': [{'id': i, 'filename': name} for i, (name, _, _) in enumerate(files)]}
    boundary = 'WowTogether-' + uuid.uuid4().hex
    parts = []
    def add(header, data):
        parts.extend([('--' + boundary + '\r\n' + header + '\r\n\r\n').encode(), data, b'\r\n'])
    add('Content-Disposition: form-data; name="payload_json"\r\nContent-Type: application/json',
        json.dumps(payload, ensure_ascii=False).encode())
    for i, (name, content_type, data) in enumerate(files):
        add(f'Content-Disposition: form-data; name="files[{i}]"; filename="{name}"\r\nContent-Type: {content_type}', data)
    parts.append(('--' + boundary + '--\r\n').encode())
    return version, message, files, boundary, b''.join(parts)


def webhook_endpoint(value):
    url = urllib.parse.urlsplit(value.strip())
    if (url.scheme != 'https' or url.netloc != 'discord.com'
            or not re.fullmatch(r'/api(?:/v\d+)?/webhooks/\d+/[A-Za-z0-9_-]+', url.path)
            or url.fragment):
        raise ValueError('Use a Discord HTTPS channel webhook URL.')
    query = dict(urllib.parse.parse_qsl(url.query))
    if set(query) - {'wait'}:
        raise ValueError('Use the channel webhook without extra query parameters.')
    return urllib.parse.urlunsplit(('https', 'discord.com', url.path, 'wait=true', ''))


def content_digest(archive):
    """Ignore ZIP timestamps so rebuilding identical release files cannot duplicate a post."""
    digest = hashlib.sha256()
    with zipfile.ZipFile(archive) as z:
        for name in sorted(z.namelist()):
            data = z.read(name)
            digest.update(json.dumps([name, len(data)], separators=(',', ':')).encode())
            digest.update(data)
    return digest.hexdigest()


def read_receipts(path):
    if not path.exists():
        return {}
    try:
        result = json.loads(path.read_text())
    except (ValueError, OSError):
        raise PublicationError('Discord receipt file is unreadable; check channel history before posting.') from None
    if not isinstance(result, dict):
        raise PublicationError('Discord receipt file is invalid; check channel history before posting.')
    return result


def remember_post(archive, webhook_id, message_id, channel_id=None):
    version, _, files, _, _ = prepare(archive)
    path = archive.parent / 'discord-posts.json'
    receipts = read_receipts(path)
    receipt = {'version': version, 'webhook_id': webhook_id, 'message_id': message_id,
               'content_sha256': content_digest(archive), 'files': [name for name, _, _ in files]}
    if channel_id:
        receipt['channel_id'] = channel_id
    receipts[webhook_id + ':' + version] = receipt
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(receipts, indent=2) + '\n')
    temporary.replace(path)
    return receipt


def post_release(archive, webhook, opener=None):
    version, _, files, boundary, body = prepare(archive)
    endpoint = webhook_endpoint(webhook)
    webhook_id = urllib.parse.urlsplit(endpoint).path.split('/')[-2]
    receipts = read_receipts(archive.parent / 'discord-posts.json')
    previous = receipts.get(webhook_id + ':' + version)
    if previous:
        if not isinstance(previous, dict) or not str(previous.get('message_id', '')).isdigit():
            raise PublicationError('Stored Discord receipt is invalid; check channel history before posting.')
        if previous.get('content_sha256') != content_digest(archive):
            raise PublicationError('This version is already posted with different files. Bump the release version before posting an update.')
        print('Already posted Wow Together ' + version + '; message ID: ' + previous['message_id'])
        return previous
    request = urllib.request.Request(endpoint, data=body, method='POST', headers={
        'Content-Type': 'multipart/form-data; boundary=' + boundary,
        'User-Agent': 'WowTogether-release-uploader/1.0'})
    # One POST only: an ambiguous timeout must not silently duplicate a release.
    # Keep the environment proxy and certificate verification; never print the URL.
    try:
        with (opener or urllib.request.build_opener(NoRedirects())).open(request, timeout=45) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        raise PublicationError('Discord upload rejected: HTTP ' + str(error.code) + '. No automatic retry.') from None
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        raise PublicationError('Discord delivery is unconfirmed. Check channel history before retrying.') from None
    if not isinstance(result, dict):
        raise PublicationError('Discord returned an invalid confirmation. Check channel history before retrying.')
    attachments = result.get('attachments')
    actual = sorted(a.get('filename', '') for a in attachments if isinstance(a, dict)) if isinstance(attachments, list) else []
    message_id = str(result.get('id', ''))
    if actual != sorted(name for name, _, _ in files) or not message_id.isdigit():
        raise PublicationError('Discord did not confirm all three attachments. Check channel history before retrying.')
    try:
        receipt = remember_post(archive, webhook_id, message_id, result.get('channel_id'))
    except (OSError, PublicationError):
        raise PublicationError('Discord confirmed message ' + message_id + ' but saving its receipt failed. Do not repost.') from None
    print('Posted Wow Together ' + version + ' with all three attachments. Discord message ID: ' + message_id)
    return receipt


def configured_webhook(prompt=False):
    webhook = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook and prompt:
        webhook = getpass.getpass('Discord webhook URL (hidden): ')
    if not webhook:
        raise PublicationError('Set DISCORD_WEBHOOK_URL securely in environment settings, or use --prompt. Release ZIP is ready; nothing was posted.')
    return webhook


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--dry-run', action='store_true', help='Verify files and preview the post without network access.')
    parser.add_argument('--prompt', action='store_true', help='Read the webhook through a hidden terminal prompt when not configured.')
    args = parser.parse_args()
    version, message, files, boundary, body = prepare(args.archive)
    if args.dry_run:
        print(message)
        print('\nAttachments: ' + ', '.join(name for name, _, _ in files))
        print('Prepared multipart upload:', len(body), 'bytes; no request sent.')
        return
    post_release(args.archive, configured_webhook(args.prompt))


if __name__ == '__main__':
    try:
        main()
    except PublicationError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    except (ValueError, KeyError, OSError, zipfile.BadZipFile):
        # Validation errors deliberately omit any credential-bearing URL/path.
        print('Invalid release files or webhook format; no confirmed upload.', file=sys.stderr)
        sys.exit(1)
