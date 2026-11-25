"""Import the licensed GatherMate2_Data Forever node coordinates as data only."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
SOURCE = Path(__file__).resolve().parent / 'source'
DEST = ROOT / 'WowTogether_GatheringPositionData'
COMMIT = '29fe725eb9ab1c71d08025f47f94bb10043ed1cf'
REPOSITORY = 'https://github.com/Nevcairiel/GatherMate2_Data'
LICENSE = 'All Rights Reserved; redistributed with written permission from the project owner. Facts remain legacy, unconfirmed.'
GATHERLITE_COMMIT = '4ace5b625a1ee724ca912262509f641b4f35992a'
GATHERLITE_REPOSITORY = 'https://github.com/Wuild/GatherLite'
GATHERLITE_SHA256 = '6bca890f7dbb66117512f68ca4d09d6990bdf48a3d65dc37e302ed262c366f4d'
FISHING_POOL_IDS = {180655, 180685, 180662, 180901, 180751, 180750,
    180900, 180682, 180664, 180582, 180656, 180663}
NODE_IDS = {
    'Mining': {
        201: 'Copper Vein', 202: 'Tin Vein', 203: 'Iron Deposit', 204: 'Silver Vein',
        205: 'Gold Vein', 206: 'Mithril Deposit', 207: 'Mithril Deposit',
        208: 'Truesilver Deposit', 209: 'Silver Vein', 210: 'Gold Vein',
        211: 'Truesilver Deposit', 212: 'Rich Thorium Vein', 213: 'Small Thorium Vein',
        214: 'Small Thorium Vein', 215: 'Rich Thorium Vein', 217: 'Dark Iron Deposit',
    },
    'Herbalism': {
        401: 'Peacebloom', 402: 'Silverleaf', 403: 'Earthroot', 404: 'Mageroyal',
        405: 'Briarthorn', 407: 'Stranglekelp', 408: 'Bruiseweed',
        409: 'Wild Steelbloom', 410: 'Grave Moss', 411: 'Kingsblood',
        412: 'Liferoot', 413: 'Fadeleaf', 414: 'Goldthorn',
        415: "Khadgar's Whisker", 416: 'Wintersbite', 417: 'Firebloom',
        418: 'Purple Lotus', 420: "Arthas' Tears", 421: 'Sungrass',
        422: 'Blindweed', 423: 'Ghost Mushroom', 424: 'Gromsblood',
        425: 'Golden Sansam', 426: 'Dreamfoil', 427: 'Mountain Silversage',
        428: 'Plaguebloom', 429: 'Icecap', 431: 'Black Lotus',
    },
}
PINS = {
    'Herbalism': 'dd2adc8bccc6aedf5e461fbe6bcde7330d841e102da9b5ffe16d2f9d5c957c9a',
    'Mining': '32875fd2c4856861045efcb75d025cfb7c11867bc499f4b2e4f4087906fe9c02',
}


def read_nodes(path: Path, digest: str, profession: str):
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError(f'GatherMate2_Data source differs from pinned revision: {path.name}')
    source = payload.decode('utf-8')
    expected_global = 'GatherMateData2HerbDB' if profession == 'Herbalism' else 'GatherMateData2MineDB'
    if not source.startswith(expected_global + ' = {'):
        raise ValueError(f'Unexpected data table in {path.name}')
    current_map = None
    records = {}
    ignored_types = set()
    for line in source.splitlines():
        outer = re.match(r'\s*\[(\d+)\]\s*=\s*\{\s*$', line)
        if outer:
            current_map = int(outer.group(1))
            continue
        if current_map is None:
            continue
        point = re.match(r'\s*\[(\d{10})\]\s*=\s*(\d+)\s*,?\s*$', line)
        if point:
            coordinate, node_id = int(point.group(1)), int(point.group(2))
            name = NODE_IDS[profession].get(node_id)
            if not name:
                ignored_types.add(node_id)
                continue
            packed = f'{coordinate:010d}'
            x, y = int(packed[:4]) / 10000, int(packed[4:8]) / 10000
            if not (0 <= x <= 1 and 0 <= y <= 1):
                continue
            key = f'{profession}|{name}|{current_map}'
            row = records.setdefault(key, {'profession': profession, 'node': name,
                'mapID': current_map, 'points': [], 'source': source_fact(profession)})
            row['points'].append({'mapID': current_map, 'x': x, 'y': y,
                'source': source_fact(profession)})
        elif line.strip() == '},':
            current_map = None
    for row in records.values():
        unique = {(p['x'], p['y']): p for p in row['points']}
        row['points'] = [unique[key] for key in sorted(unique)]
    return records, ignored_types


def source_fact(profession: str) -> str:
    file_name = 'forever/HerbalismData.lua' if profession == 'Herbalism' else 'forever/MiningData.lua'
    digest = PINS[profession]
    return (f'GatherMate2_Data {COMMIT[:12]}/{file_name}; SHA-256 {digest}; '
        'written permission; legacy, unconfirmed')


def read_fishing_pools(path: Path):
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != GATHERLITE_SHA256:
        raise ValueError('GatherLite Forever position data differs from pinned revision')
    lines = payload.decode('utf-8').splitlines()
    object_id = map_id = None
    coords, records = [], {}
    source = (f'GatherLite {GATHERLITE_COMMIT[:12]}/plugins/database/data/forever.lua; '
        f'SHA-256 {GATHERLITE_SHA256}; GPL-3.0-or-later; legacy, unconfirmed')
    def save():
        if object_id not in FISHING_POOL_IDS or not map_id or not coords:
            return
        key = f'Fishing|{map_id}'
        row = records.setdefault(key, {'profession': 'Fishing', 'node': 'fishing pools',
            'mapID': map_id, 'points': [], 'source': source})
        row['points'].extend({'mapID': map_id, 'x': coords[i], 'y': coords[i + 1], 'source': source}
            for i in range(0, len(coords) - 1, 2))
    for line in lines:
        object_row = re.match(r'^ {4}\[(\d+)\]\s*=\s*\{\s*$', line)
        if object_row:
            object_id = int(object_row.group(1)); map_id = None
            continue
        map_row = re.match(r'^ {8}\[(\d+)\]\s*=\s*\{\s*$', line)
        if map_row:
            map_id = int(map_row.group(1)); coords = []
            continue
        if map_id is not None:
            coords.extend(float(value) for value in re.findall(r'(?<![\w.])0?\.\d+(?![\w.])', line))
            if line.startswith('        },'):
                save(); map_id = None; coords = []
        if line.startswith('    },') and object_id is not None:
            object_id = None
    for row in records.values():
        unique = {(p['x'], p['y']): p for p in row['points']}
        row['points'] = [unique[key] for key in sorted(unique)]
    return records


def build():
    records, ignored = {}, {}
    for profession, name in [('Herbalism', 'GatherMate2_Forever_HerbalismData.lua'),
                             ('Mining', 'GatherMate2_Forever_MiningData.lua')]:
        rows, ignored[profession] = read_nodes(SOURCE / name, PINS[profession], profession)
        records.update(rows)
    records.update(read_fishing_pools(SOURCE / 'GatherLite_Forever.lua'))
    from pack_data import Packer
    packer = Packer()
    body = 'ns.gatheringPositionData = {count = ' + str(len(records)) + '}\n'
    body += packer.records('gathering-positions', 'ns.gatheringPositionData.records', records, lazy_rows=True)
    output = packer.code(body, LICENSE + ' Source files and credits are in PRIOR_DATA.md.')
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / 'GatheringPositionData.lua').write_text(output, encoding='utf-8')
    return {'records': len(records), 'positions': sum(len(row['points']) for row in records.values()),
        'ignoredNodeTypes': {key: sorted(value) for key, value in ignored.items()}}


if __name__ == '__main__':
    print(json.dumps(build(), sort_keys=True))
