"""Merge Forever quest facts and published map points into the offline catalogue.

Use bounded zone lists rather than treating the truncated main list as complete.
Only public game facts are extracted. Scripts are parsed as JSON, never executed.
"""
import argparse
import collections
import concurrent.futures
import datetime
import html
import json
import re
import time
import threading
import urllib.error
import urllib.request
from pathlib import Path
from import_warcraftdb import ROOT, clean, generate, number

BASE = 'https://www.wowhead.com/forever'


def json_after(page, marker):
    start = page.find(marker)
    if start < 0:
        return None
    try:
        return json.JSONDecoder().raw_decode(page[start + len(marker):].lstrip())[0]
    except json.JSONDecodeError:
        return None


def list_rows(page):
    start = page.find("new Listview({template: 'quest'")
    if start < 0:
        raise ValueError('Quest list not found')
    rows = json_after(page[start:], 'data:')
    if not isinstance(rows, list):
        raise ValueError('Quest list data was not JSON')
    return rows


def base_facts(row):
    result = {'title': clean(row.get('name'))}
    for old, new, cap in [('level', 'level', 255), ('reqlevel', 'minLevel', 255),
                           ('category', 'areaID', 1000000), ('reqclass', 'classMask', 4294967295),
                           ('reqrace', 'raceMask', 4294967295), ('xp', 'xp', 2147483647), ('money', 'money', 2147483647)]:
        value = number(row.get(old), cap)
        if value is not None:
            result[new] = value
    side = {1: 'Alliance', 2: 'Horde', 3: 'Both'}.get(row.get('side'))
    if side:
        result['side'] = side
    kind = {1: 'Elite', 21: 'Life', 41: 'PvP', 62: 'Raid', 81: 'Dungeon', 82: 'World Event', 83: 'Legendary'}.get(row.get('type'))
    if kind:
        result['questType'] = kind
    return result


def category_paths(page):
    config = json_after(page, 'Filter.init(')
    if not isinstance(config, dict):
        raise ValueError('Published category tree missing')
    result = []
    def visit(nodes, prefix=''):
        for node in nodes:
            slug = node.get('url', '')
            if not re.fullmatch(r'[a-z0-9-]+', slug):
                continue
            path = prefix + slug
            if node.get('categories'):
                visit(node['categories'], path + '/')
            else:
                result.append(path)
    visit(config.get('categories', []))
    return result


def series_ids(page, current_id):
    table = re.search(r'<table[^>]*class=["\'][^"\']*\bseries\b[^"\']*["\'][^>]*>(.*?)</table>', page, re.S)
    if not table:
        return []
    ids = []
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>', table.group(1), re.S):
        links = list(dict.fromkeys(int(v) for v in re.findall(r'/forever/quest=(\d+)', row)))
        if len(links) == 1:
            ids.append(links[0])
        elif not links and re.search(r'<b\b', row):
            ids.append(current_id)
        else:
            return []  # Branching displays are not a proven linear prerequisite.
    return ids if current_id in ids and len(set(ids)) == len(ids) and len(ids) <= 24 else []


def prerequisite_facts(page, current_id):
    """Preserve branch gates without turning a branch into a linear chain.

    Same-named variants in one published step are alternatives (e.g. class
    variants of Vile Familiars). Distinct branches keep an unknown gate; we
    cannot establish AND versus OR from the presentation alone.
    """
    table = re.search(r'<table[^>]*class=["\'][^"\']*\bseries\b[^"\']*["\'][^>]*>(.*?)</table>', page, re.S)
    if not table:
        return {}
    rows, current = [], None
    for body in re.findall(r'<tr[^>]*>(.*?)</tr>', table.group(1), re.S):
        links = re.findall(r'<a\b[^>]*href=["\']/forever/quest=(\d+)[^"\']*["\'][^>]*>(.*?)</a>', body, re.S)
        row = dict((int(id), clean(html.unescape(re.sub('<[^>]+>', '', title)))) for id, title in links)
        if re.search(r'<b\b', body):
            row[current_id] = ''
        if not row or len(rows) >= 24:
            return {'prerequisitesUnverified': True}
        if current_id in row:
            if current is not None:
                return {'prerequisitesUnverified': True}
            current = len(rows)
        rows.append(row)
    if current is None:
        return {'prerequisitesUnverified': True}
    if current == 0:
        return {}
    previous = rows[current - 1]
    if len(previous) == 1:
        return {'previousQuest': next(iter(previous))}
    titles = set(previous.values())
    if len(titles) == 1 and '' not in titles and len(previous) <= 8:
        return {'prerequisiteAny': sorted(previous), 'prerequisiteSource': 'Wowhead Forever series variants'}
    return {'prerequisiteCandidates': sorted(previous)[:8], 'prerequisitesUnverified': True}


def detail_facts(page, row, area_maps):
    quest_id = row['id']
    metadata = json_after(page, f'$.extend(g_quests[{quest_id}], ')
    if not isinstance(metadata, dict) or metadata.get('id') != quest_id:
        raise ValueError(f'Quest {quest_id} metadata missing')
    result = base_facts(dict(row, **metadata))
    gather = json_after(page, 'WH.Gatherer.addData(5, 16, ')
    entry = gather.get(str(quest_id), {}) if isinstance(gather, dict) else {}
    for key, target in [('reqclass', 'classMask'), ('reqrace', 'raceMask')]:
        value = number(entry.get(key), 4294967295)
        if value is not None:
            result[target] = value
    mapper = json_after(page, 'new Mapper(')
    starts, ends, objectives, npc_targets = [], [], [], []
    objective_groups = collections.defaultdict(list)
    incomplete = isinstance(mapper, dict) and bool(mapper.get('missing'))
    for area, group in (mapper.get('objectives', {}) if isinstance(mapper, dict) else {}).items():
        map_id = area_maps.get(int(area))
        if not map_id:
            incomplete = True  # NPC IDs can still be retained without assigning a UI map.
        for floor in group.get('levels', []):
            if not isinstance(floor, list):
                continue
            for p in floor:
                if p.get('type') == 1 and p.get('point') in ('requirement', 'sourcerequirement') and number(p.get('id')):
                    target = {'entityID': p['id'], 'npc': True, 'name': clean(html.unescape(p.get('name', '')))}
                    if p.get('point') == 'sourcerequirement':
                        target['action'] = 'collect'
                    elif p.get('reacthorde') == -1 or p.get('reactalliance') == -1:
                        target['action'] = 'kill'
                    if p.get('item'):
                        target['itemName'] = clean(p['item'])
                    if target not in npc_targets and len(npc_targets) < 96:
                        npc_targets.append(target)
                if not map_id:
                    continue  # An AreaTable ID is not a C_Map UI ID.
                coords = p.get('coord')
                if not isinstance(coords, list) or len(coords) != 2 or any(type(n) not in (int, float) or not 0 <= n <= 100 for n in coords):
                    continue
                point = {'mapID': map_id, 'x': coords[0] / 100, 'y': coords[1] / 100,
                         'name': clean(html.unescape(p.get('name', ''))), 'entityID': number(p.get('id')) or 0}
                if p.get('type') == 1:
                    point['npc'] = True
                if p.get('point') == 'requirement' and p.get('type') == 1 and (p.get('reacthorde') == -1 or p.get('reactalliance') == -1):
                    point['action'] = 'kill'
                elif p.get('point') == 'sourcerequirement':
                    point['action'] = 'collect'
                    if p.get('item'):
                        point['itemName'] = clean(p['item'])
                if p.get('point') == 'start':
                    starts.append(point)
                elif p.get('point') == 'end':
                    ends.append(point)
                elif p.get('point') in ('requirement', 'sourcerequirement') and number(p.get('objective')) is not None:
                    # Direct requirements use entity IDs; item source requirements
                    # use slot IDs. Neither is a client quest-objective index.
                    point['sourceObjective'] = p['objective']
                    objective_groups[(p['point'], p['objective'])].append(point)
    for (kind, _), points in objective_groups.items():
        if kind == 'sourcerequirement' and len({p['entityID'] for p in points}) > 1:
            incomplete = True  # Alternative item drops do not prove a best target.
        else:
            objectives.append(points[0])
    if len(objectives) > 8:
        incomplete = True
    if incomplete:
        result['objectiveLocationsIncomplete'] = True
    for key, points in [('starts', starts), ('ends', ends), ('objectives', objectives)]:
        if points:
            result[key] = points[:8]
    if npc_targets:
        result['npcTargets'] = npc_targets
    item_data = json_after(page, 'WH.Gatherer.addData(3, 16, ')
    boundary = page.find('new Mapper(')
    if boundary < 0:
        heading = re.search(r'<h2[^>]*>(?:Description|Completion|Rewards)', page)
        boundary = heading.start() if heading else 0
    tables = re.findall(r'<table[^>]*class=["\'][^"\']*\bicon-list\b[^"\']*["\'][^>]*>(.*?)</table>', page[:boundary], re.S)
    required = []
    for table in tables[:1]:
        for count, body in re.findall(r'<tr[^>]*data-icon-list-quantity=["\'](\d+)["\'][^>]*>(.*?)</tr>', table, re.S):
            match = re.search(r'<a[^>]*href=["\']/forever/item=(\d+)[^"\']*["\'][^>]*>(.*?)</a>', body, re.S)
            if not match or not 0 < int(count) <= 10000:
                continue
            item_id = int(match[1])
            data = item_data.get(str(item_id), {}) if isinstance(item_data, dict) else {}
            requirement = {'itemID': item_id, 'quantity': int(count), 'name': clean(html.unescape(re.sub('<[^>]+>', '', match[2])))}
            price = number(data.get('jsonequip', {}).get('buyprice'))
            if price and price > 0:
                requirement['buyable'], requirement['buyPrice'] = True, price
            required.append(requirement)
    if required:
        result['requiredItems'] = required[:12]
    seq = series_ids(page, quest_id)
    if len(seq) > 1:
        result['series'] = seq
        result['seriesRoot'] = seq[0]
        result['seriesPosition'] = seq.index(quest_id) + 1
        if seq.index(quest_id) > 0:
            result['previousQuest'] = seq[seq.index(quest_id) - 1]
    result.update(prerequisite_facts(page, quest_id))
    result['prerequisitesRead'] = True
    if isinstance(mapper, dict):
        own_area = str(result.get('areaID'))
        group = mapper.get('objectives', {}).get(own_area)
        if group:
            result['zone'] = clean(group.get('zone'))
            if result.get('areaID') in area_maps:
                result['mapID'] = area_maps[result['areaID']]
    result['locationSource'] = 'Wowhead Forever'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=Path('/tmp/wow-together-wowhead'))
    parser.add_argument('--zone', action='append', default=[])
    parser.add_argument('--all-categories', action='store_true', help='Read bounded published category lists for broad quest facts')
    parser.add_argument('--detail-level-max', type=int, help='Only fetch new detailed pages up to this quest level; retain cached details')
    parser.add_argument('--cached-details', action='store_true', help='Build with accessible cached details without new detail-page requests')
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)

    def fetch(path, key):
        cache = args.cache / (key + '.html')
        if cache.exists():
            return cache.read_text()
        time.sleep(0.4)
        request = urllib.request.Request(BASE + path, headers={'User-Agent': 'WowTogether-quest-data-import/0.4'})
        with urllib.request.urlopen(request, timeout=25) as response:
            page = response.read().decode('utf-8')
        cache.write_text(page)
        return page

    cache = Path('/tmp/wow-together-warcraftdb')
    records = {}
    for path in cache.glob('quest-*.json'):
        quest_id = int(path.stem.split('-')[-1])
        from import_warcraftdb import normalize
        raw = json.loads(path.read_text())
        records[quest_id] = normalize({'record_id': quest_id}, raw)
    if not records:
        raise RuntimeError('Run import_warcraftdb.py first to provide the base catalogue and map-ID evidence')
    root_page = fetch('/quests', 'index')
    root_rows = list_rows(root_page)
    zones = category_paths(root_page) if args.all_categories else (args.zone or ['kalimdor/durotar', 'kalimdor/the-barrens'])
    zone_rows = {}
    def load_list(zone):
        rows = list_rows(fetch('/quests/' + zone, zone.replace('/', '-')))
        if len(rows) >= 1000:
            raise RuntimeError('Zone list is truncated; use a narrower scope')
        return zone, rows
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
      for index, (zone, rows) in enumerate(executor.map(load_list, zones), 1):
        for row in rows:
            row['categoryPath'] = zone
            zone_rows[row['id']] = row
        if index % 20 == 0:
            print(f'Category lists: {index}/{len(zones)}; {len(zone_rows)} distinct quests.', flush=True)
    evidence = collections.defaultdict(collections.Counter)
    for row in root_rows + list(zone_rows.values()):
        old = records.get(row['id'], {})
        if old.get('mapID') and number(row.get('category'), 1000000):
            evidence[row['category']][old['mapID']] += 1
    area_maps = {area: next(iter(counts)) for area, counts in evidence.items() if len(counts) == 1}
    area_names = {}
    for record in records.values():
        if record.get('mapID') and record.get('zone'):
            area_names.setdefault(record['mapID'], record['zone'])
    for row in root_rows + list(zone_rows.values()):
        record = records.setdefault(row['id'], {})
        record.update(base_facts(row))
        map_id = area_maps.get(record.get('areaID'))
        if map_id and not record.get('mapID'):
            record['mapID'] = map_id
            record['zone'] = area_names.get(map_id, '')
        if row.get('categoryPath'):
            record['categoryPath'] = row['categoryPath']
    details = [row for row in zone_rows.values() if args.detail_level_max is None
               or (number(row.get('level'), 255) is not None and row['level'] <= args.detail_level_max)
               or (args.cache / ('quest-' + str(row['id']) + '.html')).exists()]
    print(f'Reading {len(details)} detailed pages; {len(area_maps)} unambiguous Area-to-UI map joins.', flush=True)

    unavailable = []
    lock = threading.Lock()
    denial_streak, requests_stopped = 0, False
    def load(row):
        nonlocal denial_streak, requests_stopped
        cached = (args.cache / ('quest-' + str(row['id']) + '.html')).exists()
        with lock:
            if not cached and (args.cached_details or requests_stopped):
                return row['id'], None
        try:
            page = fetch('/quest=' + str(row['id']), 'quest-' + str(row['id']))
            facts = detail_facts(page, row, area_maps)
            if not cached:
                with lock:
                    denial_streak = 0
            return row['id'], facts
        except urllib.error.HTTPError as error:
            if error.code not in (403, 404):
                raise
            with lock:
                unavailable.append({'questID': row['id'], 'status': error.code})
                if error.code == 403:
                    denial_streak += 1
                    if denial_streak >= 3:
                        requests_stopped = True
            return row['id'], None

    detailed_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        for index, (quest_id, facts) in enumerate(executor.map(load, details), 1):
            if facts is not None:
                records.setdefault(quest_id, {}).update(facts)
                detailed_count += 1
            if index % 40 == 0:
                print(f'Detailed zone quests: {index}/{len(details)}', flush=True)
    for quest_id, record in records.items():
        if record.get('seriesRoot'):
            root = records.get(record['seriesRoot'])
            record['seriesName'] = root.get('title', 'Quest series') if root else 'Quest series'
    date = datetime.date.today().isoformat()
    previous_summary = {}
    summary_path = ROOT / 'WowTogether' / 'QuestCatalogue.json'
    if args.cached_details and summary_path.exists():
        previous_summary = json.loads(summary_path.read_text())
        # Reprocessing cached HTML does not establish a new source capture.
        date = previous_summary.get('captured', date)
    output = ROOT / 'WowTogether' / 'QuestCatalogue.lua'
    code = generate(records, date).replace('-- Generated by tools/import_warcraftdb.py;', '-- Generated by the Warcraft DB and Wowhead import tools;')
    code = code.replace('    count =', f'    detailSource = "{BASE}/quests",\n    count =', 1)
    output.write_text(code)
    summary = {'captured': date, 'count': len(records), 'detailed_quests': detailed_count, 'zones': zones,
               'listed_quests': len(zone_rows), 'detail_level_max': args.detail_level_max,
               'unavailable_details': unavailable, 'detail_requests_stopped_after_denials': requests_stopped,
               'with_starters': sum(bool(r.get('starts')) for r in records.values()),
               'with_objectives': sum(bool(r.get('objectives')) for r in records.values()),
               'with_turnins': sum(bool(r.get('ends')) for r in records.values()),
               'with_series': sum(bool(r.get('series')) for r in records.values()),
               'with_prerequisites': sum(bool(r.get('previousQuest') or r.get('prerequisiteAny')) for r in records.values()),
               'unverified_prerequisites': sum(bool(r.get('prerequisitesUnverified')) for r in records.values()),
               'incomplete_objective_locations': sum(bool(r.get('objectiveLocationsIncomplete')) for r in records.values()),
               'area_ui_maps': area_maps}
    if args.cached_details:
        summary['reprocessed'] = datetime.date.today().isoformat()
        for field in ('unavailable_details', 'detail_requests_stopped_after_denials'):
            if field in previous_summary:
                summary[field] = previous_summary[field]
    output.with_suffix('.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
