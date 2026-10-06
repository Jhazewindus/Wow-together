"""Capture public Forever dungeon/NPC facts through the configured HTTPS proxy.

Bounded workers, validated literal tables, resumable files, SHA-256 provenance.
No website scripts are executed and no source artwork or guide text is bundled.
"""
import argparse
import concurrent.futures
import hashlib
import json
import re
import time
import urllib.request
import urllib.error
from pathlib import Path

from import_dungeon_journal import rows

BASE = 'https://www.wowhead.com/forever/'


def capture(directory, tasks, workers=3, base=BASE, expected=' - Forever</title>'):
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / 'capture.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    def fetch(task):
        key, relative, filename = task
        path = directory / filename
        if not path.exists():
            for attempt in range(3):
                try:
                    request = urllib.request.Request(base + relative, headers={'User-Agent': 'WoWTogether-data-audit/0.8.31'})
                    with urllib.request.urlopen(request, timeout=35) as response:
                        data = response.read()
                    text = data.decode('utf-8')
                    if expected not in text and 'for Forever' not in text:
                        raise ValueError('Unexpected source page for ' + relative)
                    path.write_bytes(data)
                    break
                except Exception as error:
                    if isinstance(error, urllib.error.HTTPError) and error.code in (403, 404):
                        raise
                    if attempt == 2:
                        raise
                    time.sleep(attempt + 1)
        data = path.read_bytes()
        return str(key), {'url': base + relative, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}

    failures = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        pending = {pool.submit(fetch, task): task[0] for task in tasks}
        for index, future in enumerate(concurrent.futures.as_completed(pending), 1):
            try:
                key, record = future.result()
                manifest[key] = record
            except Exception as error:
                if isinstance(error, urllib.error.HTTPError) and error.code == 403:
                    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
                    pool.shutdown(wait=False, cancel_futures=True)
                    raise RuntimeError('Source denied access; capture paused without retrying the denied host') from error
                failures[str(pending[future])] = str(error)
            if index % 50 == 0:
                manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
                print(f'Captured {index}/{len(tasks)}; failures {len(failures)}', flush=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    if failures:
        (directory / 'failures.json').write_text(json.dumps(failures, indent=2) + '\n')
        raise RuntimeError(f'{len(failures)} captures failed; see failures.json')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--zone-index', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    definitions = json.loads((root / 'WowTogether/DungeonData.json').read_text())['dungeons']
    page = args.zone_index.read_text()
    marker = re.search(r'"template":"zone","data":', page)
    if not marker:
        raise ValueError('Expected literal Forever zone index')
    zones = json.JSONDecoder().raw_decode(page[marker.end():])[0]
    normalized = lambda value: re.sub(r'[^a-z0-9]', '', value.lower())
    tasks = []
    for key, definition in definitions.items():
        names = {normalized(value) for value in [definition['name']] + definition.get('aliases', [])}
        candidates = [zone for zone in zones if normalized(zone['name']) in names
            and (zone.get('instance') == 2 or zone['id'] in definition.get('areaIDs', []))]
        if not candidates:
            continue
        candidates.sort(key=lambda zone: (zone['id'] not in definition.get('areaIDs', []), -zone.get('popularity', 0)))
        for index, zone in enumerate(candidates):
            source_key = key if index == 0 else key + '@' + str(zone['id'])
            tasks.append((source_key, 'zone=' + str(zone['id']), source_key + '.html'))
    source = capture(args.directory / 'zones', tasks)
    npcs = {}
    for key in source:
        for npc in rows((args.directory / 'zones' / (key + '.html')).read_text(), 'npc', 'npcs'):
            # Mixed season imports occur on classic zone pages. Vanilla identities
            # and explicitly NEW Forever NPCs are audited; old SoD duplicates are not.
            if npc['id'] < 200000 or npc.get('envChange', {}).get('status') == 'new':
                npcs[npc['id']] = npc
    (args.directory / 'npcs.json').write_text(json.dumps(npcs, indent=2) + '\n')
    capture(args.directory / 'npcs', [(ident, 'npc=' + str(ident), str(ident) + '.html') for ident in sorted(npcs)])
    print(f'Finished {len(source)} zone pages and {len(npcs)} NPC pages', flush=True)


if __name__ == '__main__':
    main()
