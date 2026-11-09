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
VERSION_PATTERN = r'\d+\.\d+\.\d+(?:-beta\.\d+\.[0-9a-f]{7,40})?'


def metadata(toc):
    version = re.search(r'^## Version: (' + VERSION_PATTERN + r')\s*$', toc, re.M)
    name = re.search(r'^## X-ReleaseName: ([A-Za-z0-9 -]{1,80})\s*$', toc, re.M)
    if not version or not name:
        raise ValueError('Packaged TOC must declare a stamped version and release name.')
    return version.group(1), name.group(1)


def section_for(changelog, version):
    match = re.search(r'^## ' + re.escape(version) + r'[ \t]*\n(.*?)(?=^## |\Z)', changelog, re.M | re.S)
    if not match:
        raise ValueError('Packaged CHANGELOG.md has no heading for its stamped version.')
    return match.group(1).strip()


def blocks(section, required=True, max_items=3):
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
            if current == 'developer' and re.fullmatch(r'\*\*[A-Z0-9 —-]+\*\*', line.strip()):
                continue
            result[current].append(line)
    if required:
        for key, title in [('players', 'For players'), ('check', 'Please check')]:
            if not result[key]:
                raise ValueError('Release notes require a ' + title + ' block.')
            items = sum(bool(re.match(r'^\s*(?:[-*]|\d+[.)])\s+', line)) for line in result[key])
            if max_items is not None and (items > max_items or len(result[key]) > max_items):
                raise ValueError(title + ' must contain at most ' + str(max_items) + ' short items.')
    return {key: '\n'.join(lines).strip() for key, lines in result.items()}


def parse_fragment(path):
    text = Path(path).read_text()
    lines = text.splitlines()
    first = next((line.strip() for line in lines if line.strip()), '')
    if not re.fullmatch(r"# [A-Za-z0-9][A-Za-z0-9 &’'():_./+-]{0,78}", first):
        raise ValueError(str(path) + ': first line must be a release name heading (# RELEASE NAME).')
    release_name = first[2:].strip()
    internal = bool(re.search(r'^internal:\s*true\s*$', text, re.M | re.I))
    if internal:
        return {'path': str(path), 'name': release_name, 'internal': True, 'players': '', 'check': '', 'developer': ''}
    note_blocks = blocks(text, required=False)
    for key, heading in [('players', 'For players'), ('check', 'Please check')]:
        if not note_blocks[key]:
            raise ValueError(str(path) + ': missing ' + heading + ' section.')
    if len(note_blocks['players'].splitlines()) > 3:
        raise ValueError(str(path) + ': For players must contain at most three lines.')
    check_items = sum(bool(re.match(r'^\s*(?:[-*]|\d+[.)])\s+', line)) for line in note_blocks['check'].splitlines())
    if not check_items or check_items > 3 or len(note_blocks['check'].splitlines()) > 3:
        raise ValueError(str(path) + ': Please check must contain one to three items.')
    if not note_blocks['developer']:
        raise ValueError(str(path) + ': missing Developer notes section.')
    return {'path': str(path), 'name': release_name, 'internal': False, **note_blocks}


def next_version(root, runner=subprocess.run):
    probe = runner(['git', 'describe', '--tags', '--abbrev=0', '--match', 'v[0-9]*'], cwd=root,
                   capture_output=True, text=True)
    if probe.returncode != 0:
        raise ValueError('Could not find the latest reachable v* release tag.')
    match = re.fullmatch(r'v(\d+)\.(\d+)\.(\d+)', probe.stdout.strip())
    if not match:
        raise ValueError('Latest release tag is not a numeric vMAJOR.MINOR.PATCH tag.')
    major, minor, patch = map(int, match.groups())
    return f'{major}.{minor}.{patch + 1}'


def release_fragments(root, runner=subprocess.run):
    tag = runner(['git', 'describe', '--tags', '--abbrev=0', '--match', 'v[0-9]*'], cwd=root,
                 capture_output=True, text=True)
    if tag.returncode != 0:
        raise ValueError('Could not find the latest reachable v* release tag.')
    result = runner(['git', 'diff', '--diff-filter=A', '--name-only', tag.stdout.strip() + '..HEAD', '--', 'changes/'],
                    cwd=root, capture_output=True, text=True)
    if result.returncode != 0:
        raise ValueError('Could not collect changelog fragments since the last release tag.')
    paths = [line for line in result.stdout.splitlines() if line.startswith('changes/') and line.endswith('.md')]
    return [parse_fragment(Path(root) / name) for name in sorted(paths)]


def assemble_notes(fragments):
    visible = [item for item in fragments if not item['internal']]
    if not visible:
        return '', ''
    release_name = visible[0]['name'] if len(visible) == 1 else 'MULTIPLE IMPROVEMENTS'
    players, checks, developer = [], [], []
    for item in visible:
        players.append('**' + item['name'] + '**')
        players.append(item['players'])
        checks.append('**' + item['name'] + '**')
        checks.append(item['check'])
        if item['developer']:
            developer.extend(['**' + item['name'] + '**', item['developer']])
    notes = 'For players:\n' + '\n'.join(players) + '\n\nPlease check:\n' + '\n'.join(checks)
    if developer:
        notes += '\n\nDeveloper notes:\n' + '\n'.join(developer)
    return release_name, notes


def plan_release(root, notes_path, runner=subprocess.run):
    fragments = release_fragments(root, runner)
    release_name, notes = assemble_notes(fragments)
    output = os.environ.get('GITHUB_OUTPUT')
    if not notes:
        if output:
            with open(output, 'a') as stream:
                stream.write('release=false\n')
        return None
    version = next_version(root, runner)
    notes_path.parent.mkdir(parents=True, exist_ok=True)
    notes_path.write_text(notes + '\n')
    if output:
        with open(output, 'a') as stream:
            stream.write('release=true\nversion=' + version + '\nrelease_name=' + release_name + '\n')
    return version, release_name, notes


def validate_pr(root, base, head, branch, runner=subprocess.run):
    changed = runner(['git', 'diff', '--name-status', base + '...' + head], cwd=root, capture_output=True, text=True)
    if changed.returncode != 0:
        raise ValueError('Could not inspect the pull request diff.')
    records = [line.split('\t') for line in changed.stdout.splitlines() if line.strip()]
    bootstrap = branch == 'core/release-fragments'
    if not bootstrap and any(len(row) > 1 and row[1] == 'CHANGELOG.md' for row in records):
        raise ValueError('Pull requests must not edit CHANGELOG.md; add a changes/<branch>.md fragment.')
    toc_diff = runner(['git', 'diff', '--unified=0', base + '...' + head, '--', 'WowTogether/WowTogether.toc'],
                      cwd=root, capture_output=True, text=True)
    if toc_diff.returncode != 0:
        raise ValueError('Could not inspect the TOC diff.')
    if not bootstrap and any(re.match(r'^[+-]## Version:', line) for line in toc_diff.stdout.splitlines()):
        raise ValueError('Pull requests must not edit ## Version in the TOC.')
    fragment_changes = [row for row in records if len(row) > 1 and row[1].startswith('changes/')]
    added = [row[1] for row in fragment_changes if row[0] == 'A' and row[1].endswith('.md')]
    if len(added) != 1 or len(fragment_changes) != 1:
        raise ValueError('Each pull request must add exactly one new changes/<branch>.md file and edit no other fragments.')
    expected = 'changes/' + branch + '.md'
    if added[0] != expected:
        raise ValueError("Expected this branch's fragment at " + expected + '.')
    fragment = parse_fragment(Path(root) / added[0])
    output = os.environ.get('GITHUB_OUTPUT')
    if output:
        with open(output, 'a') as stream:
            stream.write('fragment=' + added[0] + '\nrelease_name=' + fragment['name'] + '\n')
    return added[0]


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
        blocks(section, required='-beta.' not in version, max_items=None)
    except KeyError:
        raise ValueError('The build is missing its TOC or changelog.') from None
    return version, name, section

def message_for(kind, version, name, section, archives, branch='', pr='', title='', diff=''):
    notes = blocks(section, required=kind == 'release', max_items=None)
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
    plan = commands.add_parser('plan')
    plan.add_argument('--root', type=Path, default=Path('.'))
    plan.add_argument('--notes', type=Path, required=True)
    validate = commands.add_parser('validate-pr')
    validate.add_argument('--root', type=Path, default=Path('.'))
    validate.add_argument('--base', required=True)
    validate.add_argument('--head', required=True)
    validate.add_argument('--branch', required=True)
    version = commands.add_parser('next-version')
    version.add_argument('--root', type=Path, default=Path('.'))
    publish = commands.add_parser('post')
    publish.add_argument('--kind', choices=['beta', 'release'], required=True)
    publish.add_argument('--dist', type=Path, required=True)
    publish.add_argument('--dry-run', action='store_true', help='Validate and preview message/ZIP names without webhook access.')
    for option in ('branch', 'pr', 'title', 'diff-file'):
        publish.add_argument('--' + option, default='')
    args = parser.parse_args()
    if args.command == 'plan':
        plan_release(args.root, args.notes)
    elif args.command == 'validate-pr':
        validate_pr(args.root, args.base, args.head, args.branch)
    elif args.command == 'next-version':
        print(next_version(args.root))
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
