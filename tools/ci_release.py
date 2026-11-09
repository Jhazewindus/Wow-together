"""Validate release notes and publish CI-built ZIP attachments to Discord."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
import zipfile
from pathlib import Path, PurePosixPath

from post_discord_release import NoRedirects, PublicationError, webhook_endpoint

MAX_ATTACHMENT = 25 * 1024 * 1024
ROOTS = {'WowTogether', 'WowTogether_QuestData', 'WowTogether_ProfessionData', 'WowTogether_DungeonData'}
ALLOWED_ROOTS = ROOTS | {'WowTogether_Gold'}


def metadata(toc):
    version = re.search(r'^## Version: (\d+\.\d+\.\d+)\s*$', toc, re.M)
    name = re.search(r'^## X-ReleaseName: ([A-Za-z0-9 -]{1,80})\s*$', toc, re.M)
    if not version or not name:
        raise ValueError('TOC must declare a version and release name.')
    return version.group(1), name.group(1)


def section_for(changelog, version):
    match = re.search(r'^## ' + re.escape(version) + r'[ \t]*\n(.*?)(?=^## |\Z)', changelog, re.M | re.S)
    if not match:
        raise ValueError('CHANGELOG.md has no heading for the TOC version.')
    return match.group(1).strip()


def blocks(section, required=True):
    result = {'players': [], 'check': [], 'developer': []}
    current = 'developer'
    for line in section.splitlines():
        heading = line.strip().strip('*# :').lower()
        if heading == 'for players':
            current = 'players'
        elif heading == 'please check':
            current = 'check'
        elif heading in {'developer notes', 'development notes'}:
            current = 'developer'
        elif line.strip():
            # The release-name heading is already supplied by the TOC.
            if current == 'developer' and re.fullmatch(r'\*\*[A-Z0-9 —-]+\*\*', line.strip()):
                continue
            result[current].append(line)
    if required:
        for key, title in [('players', 'For players'), ('check', 'Please check')]:
            if not result[key]:
                raise ValueError('Release notes require a ' + title + ' block.')
            items = sum(bool(re.match(r'^\s*(?:[-*]|\d+[.)])\s+', line)) for line in result[key])
            if items > 3 or len(result[key]) > 3:
                raise ValueError(title + ' must contain at most three short items.')
    return {key: '\n'.join(lines).strip() for key, lines in result.items()}


def preflight(root, notes, runner=subprocess.run):
    version, name = metadata((root / 'WowTogether/WowTogether.toc').read_text())
    section = section_for((root / 'CHANGELOG.md').read_text(), version)
    blocks(section)
    probe = runner(['git', 'show-ref', '--verify', '--quiet', 'refs/tags/v' + version], cwd=root)
    if probe.returncode == 0:
        raise ValueError('Tag v' + version + ' already exists; bump the TOC version before releasing.')
    if probe.returncode != 1:
        raise ValueError('Could not verify release tag history; fetch tags before releasing.')
    notes.parent.mkdir(parents=True, exist_ok=True)
    notes.write_text(section + '\n')
    output = os.environ.get('GITHUB_OUTPUT')
    if output:
        with open(output, 'a') as stream:
            stream.write('version=' + version + '\nrelease_name=' + name + '\n')
    return version, name, section


def archive_metadata(archives):
    roots, seen, values = set(), set(), {}
    for archive in archives:
        if archive.stat().st_size > MAX_ATTACHMENT:
            raise ValueError('A ZIP exceeds Discord\'s 25 MB attachment limit; split the build first.')
        with zipfile.ZipFile(archive) as package:
            for entry in package.infolist():
                path = PurePosixPath(entry.filename)
                if (path.is_absolute() or '..' in path.parts or '\\' in entry.filename
                        or len(path.parts) < 2 or path.parts[0] not in ALLOWED_ROOTS):
                    raise ValueError('ZIP entries must be contained in the addon folders at its root.')
                if entry.filename in seen:
                    raise ValueError('Duplicate ZIP member in release attachments.')
                seen.add(entry.filename)
                roots.add(path.parts[0])
                if entry.filename in {'WowTogether/WowTogether.toc', 'WowTogether/CHANGELOG.md'}:
                    if entry.file_size > 2 * 1024 * 1024:
                        raise ValueError('Release metadata is unexpectedly large.')
                    values[entry.filename] = package.read(entry).decode()
    if not ROOTS.issubset(roots):
        raise ValueError('The build is missing required sibling addon folders.')
    try:
        version, name = metadata(values['WowTogether/WowTogether.toc'])
        section = section_for(values['WowTogether/CHANGELOG.md'], version)
    except KeyError:
        raise ValueError('The build is missing its TOC or changelog.') from None
    return version, name, section


def message_for(kind, version, name, section, archives, branch='', pr='', title='', diff=''):
    notes = blocks(section, required=kind == 'release')
    install = ('Install: replace `WowTogether` and the matching `WowTogether_*` sibling folders in '
               '`Interface\\AddOns\\` on every member\'s client, then fully restart.')
    if len(archives) > 1:
        install += ' Install both ZIPs: ' + ', '.join('`' + path.name + '`' for path in archives) + '.'
    if kind == 'beta':
        if not branch or not str(pr).isdigit() or not title:
            raise ValueError('Beta posts require branch, PR number and title.')
        clean_branch = branch.replace('`', '').replace('\n', ' ')[:160]
        clean_title = title.replace('\n', ' ')[:200]
        preview = notes['players']
        if not preview:
            preview = '\n'.join(line[1:] if line.startswith('+') else line
                                for line in diff.splitlines() if not line.startswith(('+++', '---', '@@')))[:1500]
            preview = '\n'.join(preview.splitlines()[:10])
        text = '**Beta build — `' + clean_branch + '` (#' + str(pr) + ') — not a release**\n' + clean_title
        if preview:
            text += '\n\n' + preview
        if notes['check']:
            text += '\n\nPlease check:\n' + notes['check']
    else:
        text = '**Wow Together ' + version + ' — ' + name + '** — World of Warcraft: Forever (live)'
        text += '\n\n' + notes['players'] + '\n\n' + install + '\n\nPlease check:\n' + notes['check']
        if notes['developer']:
            text += '\n\n||Developer notes:\n' + notes['developer'].replace('||', '') + '||'
    if len(text) > 2000:
        raise ValueError('Discord message exceeds 2,000 characters; shorten this release\'s notes.')
    return text


def prepare(dist, kind, **options):
    archives = sorted(dist.glob('*.zip'))
    if not archives or len(archives) > 2:
        raise ValueError('Expected one complete ZIP or two split ZIP attachments.')
    version, name, section = archive_metadata(archives)
    if kind == 'release':
        expected = {'WowTogether-' + version + '.zip', 'WowTogether-data-' + version + '.zip'}
        if any(path.name not in expected for path in archives):
            raise ValueError('Release archive names do not match the TOC version.')
    elif any(not re.fullmatch(r'WowTogether-beta-[A-Za-z0-9_.-]+-[0-9a-f]{7,40}(?:-data)?\.zip', path.name) for path in archives):
        raise ValueError('Beta ZIPs must have a beta label and commit SHA.')
    message = message_for(kind, version, name, section, archives, **options)
    files = [(path.name, path.read_bytes()) for path in archives]
    boundary = 'WowTogetherCI-' + uuid.uuid4().hex
    payload = {'content': message, 'allowed_mentions': {'parse': []},
               'attachments': [{'id': index, 'filename': name} for index, (name, _) in enumerate(files)]}
    body = []
    def part(header, data):
        body.extend([('--' + boundary + '\r\n' + header + '\r\n\r\n').encode(), data, b'\r\n'])
    part('Content-Disposition: form-data; name="payload_json"\r\nContent-Type: application/json', json.dumps(payload).encode())
    for index, (filename, data) in enumerate(files):
        part(f'Content-Disposition: form-data; name="files[{index}]"; filename="{filename}"\r\nContent-Type: application/zip', data)
    body.append(('--' + boundary + '--\r\n').encode())
    return message, files, boundary, b''.join(body)


def post(dist, kind, webhook, opener=None, **options):
    message, files, boundary, body = prepare(dist, kind, **options)
    endpoint = webhook_endpoint(webhook)
    request = urllib.request.Request(endpoint, data=body, method='POST', headers={
        'Content-Type': 'multipart/form-data; boundary=' + boundary,
        'User-Agent': 'WowTogether-CI/1.0'})
    try:
        with (opener or urllib.request.build_opener(NoRedirects())).open(request, timeout=45) as response:
            receipt = json.load(response)
    except urllib.error.HTTPError as error:
        raise PublicationError('Discord rejected the upload: HTTP ' + str(error.code) + '; no retry.') from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        raise PublicationError('Discord delivery is unconfirmed; check channel history before retrying.') from None
    actual = receipt.get('attachments') if isinstance(receipt, dict) else None
    names = sorted(item.get('filename', '') for item in actual if isinstance(item, dict)) if isinstance(actual, list) else []
    if not isinstance(receipt, dict) or not str(receipt.get('id', '')).isdigit() or names != sorted(name for name, _ in files):
        raise PublicationError('Discord did not confirm the message ID and every ZIP attachment; do not retry automatically.')
    saved = {'message_id': str(receipt['id']), 'channel_id': str(receipt.get('channel_id', '')),
             'attachments': [name for name, _ in files], 'sha256': [hashlib.sha256(data).hexdigest() for _, data in files]}
    try:
        (dist / 'discord-receipt.json').write_text(json.dumps(saved, indent=2) + '\n')
    except OSError:
        raise PublicationError('Discord confirmed message ' + saved['message_id'] + '; saving its receipt failed. Do not repost.') from None
    print('Discord confirmed message ' + saved['message_id'] + ' and all ZIP attachments.')
    return saved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    check = commands.add_parser('preflight')
    check.add_argument('--root', type=Path, default=Path('.'))
    check.add_argument('--notes', type=Path, required=True)
    publish = commands.add_parser('post')
    publish.add_argument('--kind', choices=['beta', 'release'], required=True)
    publish.add_argument('--dist', type=Path, required=True)
    publish.add_argument('--dry-run', action='store_true', help='Validate and preview message/ZIP names without webhook access.')
    for option in ('branch', 'pr', 'title', 'diff-file'):
        publish.add_argument('--' + option, default='')
    args = parser.parse_args()
    if args.command == 'preflight':
        preflight(args.root, args.notes)
    else:
        diff = Path(args.diff_file).read_text() if args.diff_file else ''
        options = dict(branch=args.branch, pr=args.pr, title=args.title, diff=diff)
        if args.dry_run:
            message, files, _, _ = prepare(args.dist, args.kind, **options)
            print(message)
            print('Attachments: ' + ', '.join(name for name, _ in files))
            print('Dry run: no request sent.')
            return
        webhook = os.environ.get('CI_DISCORD_WEBHOOK')
        if not webhook:
            raise PublicationError('Configure the required repository Discord webhook secret; nothing was posted.')
        post(args.dist, args.kind, webhook, **options)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, zipfile.BadZipFile, PublicationError) as error:
        # Arbitrary OS/network exceptions can contain paths or credential-bearing URLs.
        print(str(error) if isinstance(error, (PublicationError, ValueError)) else 'Invalid CI build files.', file=sys.stderr)
        sys.exit(1)
