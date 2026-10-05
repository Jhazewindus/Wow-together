"""Select individually needed event-location facts from a pinned public source.

Never execute providers or copy quest prose, UI or routing code. This reads
literal coordinates only; quest identity and the older-world event flag must
agree. Multiple/conflicting endpoints remain unresolved rather than guessed.
"""
import hashlib
import re

from forever_map_geometry import COMMIT
from lua_data_literal import LiteralParser, literal


FILES = {
    'data/Forever/foreverQuestDB.lua': 'd5be8516877505334f02073826ea0f22a394ddbf604bb5a33f5a39de5bb1ee87',
    'src/corrections/Forever/legacy/classicQuestFixes.lua': '76cd6a05f035826cabc6180a0ff2a1a37c5e7946c891eb0a06412fab5a4caf2e',
}
SOURCE = 'https://github.com/Questie/QuestieDB/tree/' + COMMIT


def event_rows(root, area_maps, geometry):
    texts = {}
    for name, checksum in FILES.items():
        file = root / name
        if hashlib.sha256(file.read_bytes()).hexdigest() != checksum:
            raise ValueError('Event-coordinate source needs review: ' + name)
        texts[name] = file.read_text()
    rows = {}
    for line in texts['data/Forever/foreverQuestDB.lua'].splitlines():
        match = re.match(r'^\[(\d+)\]\s*=\s*(\{.*\}),\s*$', line)
        if match: rows[int(match[1])] = literal(match[2])
    # Resolve only geographic symbols independently joined to the published
    # map-name/area facts. No provider variables/functions are evaluated.
    symbols = {}
    for row in geometry['geometry']['transforms']:
        if area_maps.get(row['area_id']) == row['ui_map_id']:
            symbol = re.sub(r'\s+', '_', re.sub(r'[^A-Z0-9\s]', '', row['target_name'].upper()))
            symbols['zoneIDs.' + symbol] = row['area_id']
    overrides, ambiguous = {}, set()
    ident = None
    for line in texts['src/corrections/Forever/legacy/classicQuestFixes.lua'].splitlines():
        key = re.match(r'^        \[(\d+)\]\s*=\s*\{', line)
        if key: ident = int(key[1])
        if line.startswith('        },'): ident = None
        if ident is None or '[questKeys.triggerEnd]' not in line: continue
        text = line.split('=', 1)[1].strip()
        try:
            parser = LiteralParser(text, symbols); value = parser.value(); parser.space()
            if not parser.text[parser.pos:].strip().startswith(','): continue
        except ValueError: continue  # Symbolic/conditional expressions are not location facts.
        if ident in overrides and overrides[ident] != value: ambiguous.add(ident)
        overrides[ident] = value
    for ident, value in overrides.items():
        if ident in rows and ident not in ambiguous: rows[ident][9] = value
    return rows, ambiguous


def apply_event_areas(records, rows, ambiguous, eligible, old_quests, items, area_maps):
    used, rejected = [], []
    for ident in sorted(eligible):
        q, row, old = records[ident], rows.get(ident, {}), old_quests[ident]
        if q.get('foreverStatus') != 'unchanged' or not q.get('legacyFactsSource'): continue
        if q.get('objectives') or q.get('requirements') or not old['SpecialFlags'] & 2: continue
        if ident in ambiguous or row.get(1) != q['title'] or row.get(4) != q.get('minLevel') or row.get(5) != q.get('level'): continue
        trigger = row.get(9)
        if not isinstance(trigger, dict) or not isinstance(trigger.get(2), dict): continue
        points = []
        for area, coordinates in trigger[2].items():
            if area not in area_maps or not isinstance(coordinates, dict): continue
            for pair in coordinates.values():
                if not isinstance(pair, dict): continue
                x, y = pair.get(1), pair.get(2)
                if type(x) in (int, float) and type(y) in (int, float) and 0 <= x <= 100 and 0 <= y <= 100:
                    point = {'mapID': area_maps[area], 'x': x/100, 'y': y/100}
                    if point not in points: points.append(point)
        if len(points) != 1:
            rejected.append(ident); continue
        point = points[0]; point.update(name=q['title'], action='event',
            locationSource='Older-world fallback; published Forever event endpoint', eventSource=SOURCE)
        text = ' '.join(str(value) for value in (row.get(8) or {}).values())
        item = items.get(row.get(11), {})
        if item.get('name') and re.search(r'\bUse\s+(?:the\s+)?' + re.escape(item['name']) + r'\b', text, re.I):
            point.update(action='use', useItemName=item['name'], sourceAction='use-at')
            description = trigger.get(1, '')
            name = re.sub(r'^(?:Cleanse|Explore|Find|Reach|Scout)\s+(?:the\s+)?', '', description, flags=re.I)
            if name != description and len(name) <= 70: point['name'] = name
        elif re.search(r'\bEscort\b', text, re.I):
            point['action'] = 'escort'
            if q.get('starts') and q['starts'][0].get('npc'): point['name'] = q['starts'][0]['name']
        q['objectives'] = [point]; q['eventAreaSource'] = SOURCE
        q.pop('objectiveLocationsIncomplete', None); q['otherLocationsIncomplete'] = False
        used.append(ident)
    return {'source': SOURCE, 'files_sha256': FILES, 'event_areas_used': used,
        'ambiguous_or_unmapped_event_areas': rejected, 'conflicting_source_records': sorted(ambiguous),
        'limitations': ['Identity-matched unchanged event quests only',
            'Endpoints do not describe the terrain/escort walking path', 'No source code or quest prose included']}
