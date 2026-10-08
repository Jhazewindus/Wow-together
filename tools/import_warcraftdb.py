"""Generate an offline Forever quest catalogue from Warcraft DB's public JSON.

Only quest facts are included; no descriptions, artwork, or addon source code.
Missing source fields stay unknown. NPC positions are not inferred from prose.
"""
import argparse
import concurrent.futures
import copy
import datetime
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = 'https://forever.warcraftdb.com'
ROOT = Path(__file__).resolve().parents[1]


def apply_corrections(records):
    """Keep reviewed tester facts separate from source parsing and provenance."""
    applied = []
    corrections = json.loads((ROOT / 'tools' / 'quest_corrections.json').read_text())
    for correction in corrections:
        if correction.get('stageCorrection'):
            continue  # Stage facts apply after enrichment, not as eligibility rules.
        if correction.get('exclusiveQuests'):
            quest = records.get(correction['questID'])
            alternatives = correction['exclusiveQuests']
            if quest is None or any(other not in records for other in alternatives): continue
            if quest['title'] != correction['title'] or any(
                other == correction['questID'] or records[other]['title'] != correction['title'] for other in alternatives):
                raise ValueError('Reviewed alternative quest identity changed; review required')
            quest['exclusiveQuests'] = sorted(set(alternatives))
            quest['exclusiveQuestSource'] = correction['source']
            applied.append(correction['questID'])
            continue
        if correction.get('pickupRequiresOffer'):
            quest = records.get(correction['questID'])
            if quest is None: continue
            if quest['title'] != correction['title']:
                raise ValueError('Tester correction quest identity changed; review required')
            quest['pickupRequiresOffer'] = True
            quest['prerequisitesUnverified'] = True
            quest['pickupReviewSource'] = correction['source']
            applied.append(correction['questID'])
            continue
        quest_id, parent_id = correction['questID'], correction['previousQuest']
        if quest_id not in records or parent_id not in records:
            continue
        quest, parent = records[quest_id], records[parent_id]
        if quest['title'] != correction['title'] or parent['title'] != correction['previousTitle']:
            raise ValueError('Tester correction quest identity changed; review required')
        if quest_id == parent_id or quest.get('previousQuest', parent_id) != parent_id or quest.get('prerequisiteAny'):
            raise ValueError('Tester correction conflicts with a prerequisite; review required')
        quest['previousQuest'] = parent_id
        quest['prerequisiteSource'] = correction['source']
        applied.append(quest_id)
    return applied


def apply_stage_corrections(records):
    """Apply reviewed stage facts last; conflicting new facts require review.

    Keep delivery items in hand-in requirements, but never send players to farm
    an item supplied on acceptance. Location additions preserve existing work.
    Validate all affected records before committing any mutations.
    """
    pending = {}
    corrections = json.loads((ROOT / 'tools' / 'quest_corrections.json').read_text())
    for correction in corrections:
        rule = correction.get('stageCorrection')
        ident = correction['questID']
        if not rule or ident not in records:
            continue
        quest = copy.deepcopy(records[ident])
        expected = (correction['title'], rule['minLevel'], rule['level'], rule['classMask'])
        actual = tuple(quest.get(k) for k in ('title', 'minLevel', 'level', 'classMask'))
        if actual != expected or quest.get('unmodeledObjectiveKinds') or quest.get('otherLocationsIncomplete'):
            raise ValueError('Reviewed stage identity or objective semantics changed: ' + str(ident))
        requirements = list(quest.get('requirements') or [])
        required = rule['requiredItems']
        allowed_items = [required]
        if rule['kind'] in ('objective-facts', 'stage-facts'):
            allowed_items.append(rule['before']['requiredItems'])
        if {(r['itemID'], r['quantity']) for r in quest.get('requiredItems', [])} not in [
                {(r['itemID'], r['quantity']) for r in items} for items in allowed_items]:
            raise ValueError('Reviewed hand-in items changed: ' + str(ident))
        if rule['kind'] == 'provided-delivery':
            item, = required
            supplied = {'entityType': 'item', 'entityID': item['itemID'],
                        'name': item['name'], 'quantity': item['quantity']}
            if quest.get('objectives') or any(r.get('entityType') != 'item' or
                    r.get('entityID') != item['itemID'] or r.get('quantity') != item['quantity']
                    for r in requirements):
                raise ValueError('Delivery correction would remove independent work: ' + str(ident))
            provided = list(quest.get('providedItems') or [])
            if not requirements and supplied not in provided:
                raise ValueError('Delivery evidence no longer matches: ' + str(ident))
            if any(r.get('entityID') == item['itemID'] and r != supplied for r in provided):
                raise ValueError('Conflicting provided item: ' + str(ident))
            if supplied not in provided:
                provided.append(supplied)
            if not quest.get('ends') or any(p.get('action') not in (None, 'talk') for p in quest['ends']):
                raise ValueError('Delivery destination semantics changed: ' + str(ident))
            for point in quest['ends']:
                point['action'] = 'talk'
            destination = rule.get('destinationLocation')
            if destination:
                points = [p for p in quest['ends'] if p.get('entityID') == destination['entityID']]
                if len(points) != 1 or {k: points[0].get(k) for k in ('mapID', 'x', 'y')} not in (
                        destination['before'], destination['after']):
                    raise ValueError('Reviewed delivery destination changed: ' + str(ident))
                points[0].update(destination['after'])
                points[0]['locationSource'] = correction['source']
            quest['providedItems'] = provided
            quest['requirements'] = {}
            if quest.get('worldReferences'):
                quest['worldReferences']['requirements'] = {}
                quest['worldReferences']['provided'] = copy.deepcopy(provided)
        elif rule['kind'] in ('objective-facts', 'stage-facts'):
            core = {'requirements', 'requiredItems', 'objectives', 'npcTargets'}
            allowed = core | {'starts', 'ends', 'startRefs', 'endRefs', 'providedItems',
                              'missingRequirements', 'objectiveLocationsIncomplete'}
            fields = set(rule['before'])
            if not core <= fields or not fields <= allowed or set(rule['after']) != fields or \
                    (rule['kind'] == 'objective-facts' and fields != core) or rule['after']['requiredItems'] != required:
                raise ValueError('Unsupported reviewed objective fields: ' + str(ident))
            def value(field):
                return quest.get(field) if field == 'objectiveLocationsIncomplete' else quest.get(field) or []
            actual = {k: value(k) for k in fields}
            if actual not in (rule['before'], rule['after']):
                raise ValueError('Reviewed objective facts conflict with new evidence: ' + str(ident))
            if quest.get('worldReferences'):
                refs = quest['worldReferences'].get('requirements') or []
                if refs not in (rule['before']['requirements'], rule['after']['requirements']):
                    raise ValueError('Reviewed world requirements changed: ' + str(ident))
                quest['worldReferences']['requirements'] = copy.deepcopy(rule['after']['requirements'])
            for field, value in rule['after'].items():
                current = quest.get(field) if field == 'objectiveLocationsIncomplete' else quest.get(field) or []
                if current != value:
                    quest[field] = copy.deepcopy(value)
        elif rule['kind'] == 'item-exchange':
            item, = required
            if requirements != rule['requirements'] or len(requirements) != 1 or (
                    requirements[0].get('entityType'), requirements[0].get('entityID'), requirements[0].get('quantity')) != (
                        'item', item['itemID'], item['quantity']):
                raise ValueError('Reviewed exchange requirement changed: ' + str(ident))
            point = rule['point']
            if point.get('entityType') != 'object' or point.get('action') != 'item' or (
                    point.get('itemID'), point.get('quantity')) != (item['itemID'], item['quantity']):
                raise ValueError('Unsupported reviewed exchange semantics: ' + str(ident))
            if quest.get('objectives') and quest['objectives'] != [point]:
                raise ValueError('Reviewed exchange conflicts with existing work: ' + str(ident))
            if quest.get('missingRequirements') and quest['missingRequirements'] != requirements:
                raise ValueError('Other exchange work remains unresolved: ' + str(ident))
            quest['objectives'] = [copy.deepcopy(point)]
        elif rule['kind'] in ('unmapped-escort', 'unmapped-objective'):
            if requirements or quest.get('objectives'):
                raise ValueError('Escort correction would replace mapped work: ' + str(ident))
            target = rule['target']
            if rule['kind'] == 'unmapped-escort' and not any(r.get('entityType') == target['entityType'] and r.get('entityID') == target['entityID']
                       for r in quest.get('startRefs', [])):
                raise ValueError('Escort starter identity changed: ' + str(ident))
            if quest.get('missingRequirements') and quest['missingRequirements'] != [target]:
                raise ValueError('Other unmapped escort work needs review: ' + str(ident))
            quest['missingRequirements'] = [copy.deepcopy(target)]
            quest['objectiveLocationsIncomplete'] = True
        elif rule['kind'] == 'npc-location':
            # Replace only an identified representative point. Work semantics,
            # offer requirements and unrelated unresolved facts survive.
            for role in rule['roles']:
                if role not in ('starts', 'ends', 'objectives'):
                    raise ValueError('Unsupported NPC location role: ' + role)
                if role == 'objectives' and not rule.get('objectiveKey'):
                    raise ValueError('Reviewed work location needs an objective identity')
                points = [p for p in quest.get(role, []) if p.get('entityID') == rule['entityID']
                          and (role != 'objectives' or p.get('objectiveKey') == rule['objectiveKey'])]
                if len(points) != 1 or not points[0].get('npc'):
                    raise ValueError('Reviewed NPC identity changed: ' + str(ident))
                point = points[0]
                location = {k: point.get(k) for k in ('mapID', 'x', 'y')}
                if location not in (rule['before'], rule['after']):
                    raise ValueError('Reviewed NPC location conflicts with new evidence: ' + str(ident))
                point.update(rule['after'])
                point['locationSource'] = correction['source']
        elif rule['kind'] == 'item-source':
            if {(r.get('entityType'), r.get('entityID'), r.get('quantity')) for r in requirements} != \
                    {('item', r['itemID'], r['quantity']) for r in required}:
                raise ValueError('Reviewed objective requirements changed: ' + str(ident))
            point = rule['point']
            points = list(quest.get('objectives') or [])
            matches = [p for p in points if p.get('itemID') == point['itemID']]
            if matches and matches != [point]:
                raise ValueError('Reviewed source conflicts with an existing objective: ' + str(ident))
            if not matches:
                points.append(copy.deepcopy(point))
            if {p.get('itemID') for p in points} != {r['itemID'] for r in required}:
                raise ValueError('Other objective locations remain unresolved: ' + str(ident))
            quest['objectives'] = points
            target = {k: point[k] for k in ('entityID', 'name', 'npc', 'action', 'itemName')}
            targets = list(quest.get('npcTargets') or [])
            if target not in targets:
                targets.append(target)
            quest['npcTargets'] = targets
        else:
            raise ValueError('Unknown reviewed stage correction: ' + rule['kind'])
        if rule['kind'] in ('provided-delivery', 'item-source', 'item-exchange'):
            quest.pop('missingRequirements', None)
            quest.pop('objectiveLocationsIncomplete', None)
        quest['stageCorrectionSource'] = correction['source']
        if quest != records[ident]:
            pending[ident] = quest
    records.update(pending)
    return sorted(pending)


def number(value, maximum=2147483647):
    return value if type(value) is int and 0 <= value <= maximum else None


def clean(value):
    return re.sub(r'[\x00-\x1f\x7f|]', ' ', value).strip() if isinstance(value, str) else ''


def normalize(row, detail):
    data = detail.get('data', {})
    result = {'title': clean(data.get('name') or row.get('name')),
              'zone': clean(data.get('zone') or row.get('zone'))}
    for source, target, maximum in [('level', 'level', 255), ('min_level', 'minLevel', 255),
                                    ('zone_id', 'mapID', 1000000), ('suggested_group', 'suggestedGroup', 40)]:
        value = number(data.get(source, row.get(source)), maximum)
        if value is not None:
            result[target] = value
    side = data.get('side')
    if side in ('Horde', 'Alliance', 'Both', 'Neutral'):
        result['side'] = side
    quest_type = clean(data.get('quest_type') or row.get('quest_type'))
    if quest_type:
        result['questType'] = quest_type
    rewards = data.get('rewards', {})
    if isinstance(rewards, dict):
        xp = number(rewards.get('xp'))
        if xp is not None:
            result['xp'] = xp
    tags = clean(data.get('tags'))
    if 'Sharable' in tags:
        result['shareable'] = True
    # The catalogue does not assume that absent faction/prerequisite/giver data
    # means no restrictions, or invent a chain from neighboring quest IDs.
    return result


def lua_value(value):
    if type(value) is bool:
        return 'true' if value else 'false'
    if type(value) in (int, float):
        return str(value)
    if isinstance(value, list):
        return '{' + ', '.join(lua_value(v) for v in value) + '}'
    if isinstance(value, dict):
        return '{' + ', '.join(f'{k} = {lua_value(v)}' for k, v in sorted(value.items())) + '}'
    return json.dumps(value, ensure_ascii=False)


def generate(records, date):
    for exclusion in json.loads((ROOT / 'tools' / 'quest_exclusions.json').read_text()):
        for quest_id in exclusion['questIDs']:
            if quest_id not in records:
                continue
            if records[quest_id]['title'] != exclusion['title']:
                raise ValueError('Guide exclusion quest identity changed; review required')
            records[quest_id]['levelingExcluded'] = exclusion['reason']
    lines = ['local addonName, ns = ...', '',
             '-- Generated by tools/import_warcraftdb.py; public quest facts only.',
             '-- Unknown requirements and locations are deliberately omitted.',
             'ns.catalogue = {',
             f'    source = "{BASE}/list/quests",',
             f'    captured = "{date}",',
             f'    count = {len(records)},',
             '    quests = {']
    for quest_id, record in sorted(records.items()):
        fields = ', '.join(f'{key} = {lua_value(value)}' for key, value in sorted(record.items()))
        lines.append(f'        [{quest_id}] = {{{fields}}},')
    lines += ['    },', '}', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=Path('/tmp/wow-together-warcraftdb'))
    parser.add_argument('--output', type=Path, default=ROOT / 'WowTogether' / 'QuestCatalogue.lua')
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)

    def fetch(path, key, paced=False):
        cache = args.cache / (key + '.json')
        if cache.exists() and not args.refresh:
            return json.loads(cache.read_text())
        if paced:
            time.sleep(0.25)
        for attempt in range(3):
            try:
                request = urllib.request.Request(BASE + path, headers={'User-Agent': 'WowTogether-catalogue-import/0.3'})
                with urllib.request.urlopen(request, timeout=25) as response:
                    data = json.load(response)
                cache.write_text(json.dumps(data, ensure_ascii=False))
                return data
            except urllib.error.HTTPError as error:
                if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise
                time.sleep(min(20, int(error.headers.get('Retry-After', '2')) * (attempt + 1)))
        raise RuntimeError('Fetch did not complete')

    first = fetch('/api/data/list/quests?page=1&per_page=100', 'list-1')
    total = number(first.get('total'), 10000)
    pages = number(first.get('pages'), 1000)
    if total is None or not pages:
        raise RuntimeError('Unexpected catalogue pagination')
    rows = list(first['rows'])
    for page in range(2, pages + 1):
        rows += fetch(f'/api/data/list/quests?page={page}&per_page=100', f'list-{page}', True)['rows']
    ids = [number(row.get('record_id')) for row in rows]
    if len(rows) != total or None in ids or len(set(ids)) != total:
        raise RuntimeError('Catalogue changed or has duplicate/invalid IDs; refresh the cache and retry')
    print(f'Index verified: {total} quests. Reading details with two paced workers.', flush=True)

    def load(row):
        quest_id = row['record_id']
        detail = fetch(f'/api/data/node/quest/{quest_id}', f'quest-{quest_id}', True)
        return quest_id, normalize(row, detail)

    records = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        for quest_id, record in executor.map(load, rows):
            records[quest_id] = record
            if len(records) % 100 == 0:
                print(f'Details: {len(records)}/{total}', flush=True)
    date = datetime.date.today().isoformat()
    corrections = apply_corrections(records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(generate(records, date))
    summary = {'source': BASE, 'captured': date, 'count': total,
               'minimum_levels': sum('minLevel' in r for r in records.values()),
               'factions': sum('side' in r for r in records.values()),
               'zone_maps': sum(bool(r.get('mapID')) for r in records.values()),
               'npc_locations': 0, 'verified_prerequisite_links': 0,
               'tester_corrections': corrections}
    args.output.with_suffix('.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
