"""Read published Blizzard map-bound facts, not another addon's implementation.

The pinned report contains DBC build/checksum evidence. Only numeric map IDs and
world rectangles are selected. It cannot locate new NPCs or prove old spawns
survived Forever. Callers must still gate older-world facts by quest identity.
"""
import hashlib
import json
import math


COMMIT = 'e0a6eaa86f181ac99262e34126bcd2ed1a1712d6'
SHA256 = '0229566017126c2577e77d2bcc7c9f995648fb27ed32a7918fa44ace0664fb22'
SOURCE = 'https://github.com/Questie/QuestieDB/blob/' + COMMIT + '/data/Forever/conversion.json'
TARGET_BUILD = '1.60.1.69893'


def geometry_facts(document):
    if document.get('format') != 1 or document.get('tool') != 'QuestieDB convert-forever':
        raise ValueError('Unrecognized map geometry report')
    geometry = document.get('geometry', {})
    if geometry.get('target_build') != TARGET_BUILD:
        raise ValueError('Map geometry build needs review')
    for table in ('ui_map_assignment', 'ui_map'):
        evidence = geometry.get('target_tables', {}).get(table, {})
        if evidence.get('coverage') != 'ok' or not isinstance(evidence.get('rows'), int) or evidence['rows'] <= 0:
            raise ValueError('Map geometry lacks complete target-table evidence')
        if len(evidence.get('snapshot_sha256', '')) != 64:
            raise ValueError('Map geometry lacks target-table checksums')
    transforms, areas = {}, {}
    for row in geometry.get('transforms', []):
        if row.get('map_id') not in (0, 1) or row.get('area_transform_supported') is not True:
            continue  # Instance, continent and unsupported views are not outdoor destinations.
        map_id, area = row.get('ui_map_id'), row.get('area_id')
        if type(map_id) is not int or type(area) is not int or map_id <= 0 or area <= 0:
            raise ValueError('Invalid map identity')
        if map_id in transforms or area in areas:
            raise ValueError('Ambiguous map identity')
        bounds = row.get('target_bounds', {})
        values = [bounds.get(key) for key in ('left', 'right', 'top', 'bottom')]
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in values):
            raise ValueError('Invalid map rectangle')
        left, right, top, bottom = values
        if not (100 < abs(right-left) < 100000 and 100 < abs(bottom-top) < 100000):
            raise ValueError('Degenerate map rectangle')
        # Blizzard's left/right bounds use world Y; top/bottom use world X.
        transforms[map_id] = {'continent': row['map_id'], 'sx': 1/(right-left),
            'ox': -left/(right-left), 'sy': 1/(bottom-top), 'oy': -top/(bottom-top),
            'geometryBuild': TARGET_BUILD, 'locationSource':
                'Older-world fallback; published Forever ' + TARGET_BUILD + ' map bounds'}
        areas[area] = map_id
    if not transforms:
        raise ValueError('No supported outdoor map rectangles')
    provenance = {'source': SOURCE, 'commit': COMMIT, 'report_sha256': SHA256,
        'target_build': TARGET_BUILD, 'target_tables': geometry['target_tables'],
        'outdoor_maps': len(transforms), 'limitations': [
            'Map rectangles do not establish current NPC/object spawns or walkable terrain',
            'New/changed quests cannot reuse older-world facts',
            'Current beta map bounds must still be checked in the client']}
    return transforms, areas, provenance


def read_geometry(path):
    if hashlib.sha256(path.read_bytes()).hexdigest() != SHA256:
        raise ValueError('Map geometry report differs from the reviewed source')
    return geometry_facts(json.loads(path.read_text()))
