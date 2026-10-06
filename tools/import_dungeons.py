"""Combine factual Forever dungeon ranges, entrance points and quest membership.

Reads captured files only. No web scripts, source addon engine/UI, images or
guide prose are executed or bundled. Network capture is a separate operation.
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

from import_wowhead import list_rows
from import_travel_network import COMMIT, encode
from import_guide_services import POIS_SHA256

ROOT = Path(__file__).resolve().parents[1]
OVERVIEW = 'https://www.wowhead.com/forever/guide/dungeons-overview-locations-details'
FAMILIES = {
    'Ragefire Chasm': ('ragefire-chasm', 2437),
    'Wailing Caverns': ('wailing-caverns', 718),
    'The Deadmines': ('the-deadmines', 1581),
    'Shadowfang Keep': ('shadowfang-keep', 209),
    'The Stockade': ('the-stockade', 717),
    'Blackfathom Deeps': ('blackfathom-deeps', 719),
    'Gnomeregan': ('gnomeregan', 133),
    'Scarlet Monastery': ('scarlet-monastery', 796),
    'Razorfen Kraul': ('razorfen-kraul', 491),
    'Razorfen Downs': ('razorfen-downs', 722),
    'Uldaman': ('uldaman', 1337),
    "Zul'Farrak": ('zulfarrak', 978),
    'Maraudon': ('maraudon', 2100),
    'Sunken Temple': ('the-temple-of-atalhakkar', 1417),
    'Blackrock Depths': ('blackrock-depths', 1584),
    'Blackrock Spire': ('blackrock-spire', 1583),
    'Dire Maul': ('dire-maul', 2557),
    'Scholomance': ('scholomance', 2057),
    'Stratholme': ('stratholme', 2017),
    'Hall of Thanes': ('the-hall-of-thanes', None),
    'Ruins of Lordaeron': ('ruins-of-lordaeron', None),
    'Excavation Site: Wetlands': ('excavation-site-wetlands', None),
    'City of Dalaran': ('city-of-dalaran', None),
    'The Drowned City': ('the-drowned-city', None),
    "Krol'dok Stronghold": ('kroldok-stronghold', None),
    'Alcaz Prison': ('alcaz-prison', None),
    'Blackmaw Hold': ('blackmaw-hold', None),
    "Shaper's Terrace": ('shapers-terrace', None),
}
ALIASES = {'the-temple-of-atalhakkar': ["The Temple of Atal'Hakkar", 'The Temple Of Atalhakkar'],
           'the-hall-of-thanes': ['The Hall of Thanes'],
           'excavation-site-wetlands': ['Excavation Site Wetlands']}
NEW_LOCATIONS = {'the-hall-of-thanes': 'Ironforge', 'ruins-of-lordaeron': 'Lordaeron',
    'excavation-site-wetlands': 'Wetlands', 'city-of-dalaran': 'Dalaran',
    'blackmaw-hold': 'Northern Azshara', 'the-drowned-city': 'Stranglethorn coast',
    'kroldok-stronghold': 'Riverglades', 'alcaz-prison': 'Alcaz Island, Dustwallow Marsh',
    'shapers-terrace': "Un'Goro Crater"}
POI_ALIASES = {'STORMWIND_STOCKADE': 'the-stockade', 'DEADMINES': 'the-deadmines',
               'SUNKEN_TEMPLE': 'the-temple-of-atalhakkar'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def overview_ranges(path):
    page = path.read_text()
    if 'Dungeons Overview for Forever' not in page:
        raise ValueError('Expected the Forever dungeon overview')
    bodies = []
    for token in re.findall(r'"(?:[^"\\]|\\.){500,}"', page):
        try:
            body = json.loads(token)
        except json.JSONDecodeError:
            continue  # HTML attribute spans are not literal JSON strings.
        if 'Ragefire Chasm' in body and '[table' in body:
            bodies.append(body.replace('\\r\\n', '\n'))
    if len(bodies) != 1:
        raise ValueError('Expected one literal guide body; no scripts are evaluated')
    rows = re.findall(r'\[td[^\]]*background=(blue|c1)[^\]]*\]\[center\]([^\[]+) \((\d+)-(\d+)\)', bodies[0])
    records = {}
    for color, name, low, high in rows:
        family = 'Blackrock Spire' if name == 'BRS Upper' else name.split(': ')[0]
        if name == 'Excavation Site: Wetlands':
            family = name
        if family not in FAMILIES:
            raise ValueError('Unreviewed dungeon in overview: ' + family)
        key, area = FAMILIES[family]
        low, high = int(low), int(high)
        if not 1 <= low <= high <= 60:
            raise ValueError('Invalid dungeon range')
        record = records.setdefault(key, {'name': family, 'era': 'Classic' if color == 'c1' else 'Forever',
            'runLevelLow': low, 'runLevelHigh': high, 'wings': [], 'aliases': ALIASES.get(key, []),
            'areaIDs': [area] if area else [], 'entrances': [], 'questIDs': []})
        record['runLevelLow'] = min(record['runLevelLow'], low)
        record['runLevelHigh'] = max(record['runLevelHigh'], high)
        if name != family:
            record['wings'].append({'name': 'Upper Blackrock Spire' if name == 'BRS Upper' else name,
                                   'runLevelLow': low, 'runLevelHigh': high})
        if key in NEW_LOCATIONS:
            record['locationHint'] = NEW_LOCATIONS[key]
    if len(records) != 28 or sum(r['era'] == 'Classic' for r in records.values()) != 19:
        raise ValueError('Incomplete overview: expected all 19 Classic complexes and 9 Forever dungeons')
    return records


def combine(overview, pois, quest_cache):
    records = overview_ranges(overview)
    if digest(pois) != POIS_SHA256:
        raise ValueError('Expected the pinned Forever geographic snapshot')
    points = 0
    for line in pois.read_text().splitlines():
        if 'kind = "instance"' not in line or 'raid = true' in line:
            continue
        fields = dict(re.findall(r'(\w+)\s*=\s*"([^"]*)"', line))
        numbers = {k: float(v) for k, v in re.findall(r'(mapID|x|y|area)\s*=\s*(-?\d+(?:\.\d+)?)', line)}
        source_id = fields['id'].removeprefix('INSTANCE_')
        key = POI_ALIASES.get(source_id, source_id.lower().replace('_', '-'))
        if key not in records:
            raise ValueError('Unreviewed non-raid instance point: ' + source_id)
        if not all(math.isfinite(v) for v in numbers.values()) or not 0 <= numbers['x'] <= 1 or not 0 <= numbers['y'] <= 1:
            raise ValueError('Invalid published entrance point')
        point = {k: numbers[k] for k in ('mapID', 'x', 'y')}
        point['mapID'] = int(point['mapID'])
        point.update(name=records[key]['name'] + ' entrance area', sourceID=fields['id'],
                     source='Published Forever entrance area', published=True, container=fields['container'])
        records[key]['entrances'].append(point)
        if numbers.get('area') and int(numbers['area']) not in records[key]['areaIDs']:
            records[key]['areaIDs'].append(int(numbers['area']))
        points += 1
    if points != 23 or any(not r['entrances'] for r in records.values() if r['era'] == 'Classic'):
        raise ValueError('Expected entrances for every Classic dungeon and four Forever dungeons')
    sources = {}
    for path in sorted(quest_cache.glob('*.html')):
        key = path.stem
        if key not in records:
            raise ValueError('Unreviewed quest category: ' + key)
        rows = list_rows(path.read_text())
        if len(rows) >= 1000:
            raise ValueError('Truncated dungeon list')
        ids = [r['id'] for r in rows]
        if any(type(i) is not int or not 0 < i < 2147483647 for i in ids):
            raise ValueError('Invalid quest membership')
        records[key]['questIDs'] = sorted(set(ids))
        sources[key] = {'url': 'https://www.wowhead.com/forever/quests/dungeons/' + key,
                        'sha256': digest(path), 'quests': len(set(ids))}
    if any(key not in sources for key, r in records.items() if r['entrances']):
        raise ValueError('Missing captured quest lists for mapped dungeons')
    metadata = {'schema': 1, 'captured': '2026-10-06', 'overview': {'url': OVERVIEW, 'sha256': digest(overview)},
        'entrance_source': {'url': 'https://github.com/tr0tsky0/Mapzeroth/blob/' + COMMIT + '/Data/Forever/Pois.lua',
                            'commit': COMMIT, 'sha256': POIS_SHA256, 'license': 'MIT'},
        'quest_categories': sources, 'classic_complexes': 19, 'forever_dungeons': 9,
        'published_entrance_areas': points, 'unmapped_entrances': sorted(k for k, r in records.items() if not r['entrances']),
        'level_conflicts': {'city-of-dalaran': {'chart': [28, 33], 'paragraph': [20, 35]},
                            'kroldok-stronghold': {'chart': [40, 45], 'paragraph': [40, 55]}},
        'limitations': ['Dungeon level ranges are recommendations, not minimum entry or quest pickup requirements',
            'Overview chart/table takes precedence over its conflicting paragraphs; retest beta levels',
            'Published points mark entrance areas, not collision-safe cave paths or exact portals',
            'Five new dungeon entrances and quest sets remain unspecified; no coordinates or membership are inferred'],
        'dungeons': records}
    return records, metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--overview', type=Path, required=True)
    parser.add_argument('--pois', type=Path, required=True)
    parser.add_argument('--quest-cache', type=Path, required=True)
    args = parser.parse_args()
    records, metadata = combine(args.overview, args.pois, args.quest_cache)
    (ROOT / 'WowTogether/DungeonData.lua').write_text('local addonName, ns = ...\n\n'
        '-- Factual dungeon ranges/membership from Wowhead Forever; geographic facts from\n'
        '-- the attributed MIT Forever snapshot. See DUNGEONS.md / DungeonData.json.\n'
        '-- No source guide prose, artwork or addon engine/UI is included.\n'
        'ns.dungeonData = ' + encode({'schema': 1, 'dungeons': records}) + '\n')
    (ROOT / 'WowTogether/DungeonData.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + '\n')
    print(f'Generated {len(records)} dungeon entries; {sum(len(r["questIDs"]) for r in records.values())} quest memberships; 23 entrance areas.')


if __name__ == '__main__':
    main()
