"""Audit Vanilla encounters and every captured NPC/container loot relationship.

Forever item metadata wins when captured; season-only relationships never do.
Community beta encounter tables are explicitly recorded as reported evidence.
"""
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

from import_dungeon_journal import MAPS, clean, icons, normalize, rows
from import_vanilla_loot import LiteralReader, vanilla_rows
from pack_data import Packer

ROOT = Path(__file__).resolve().parents[1]


def provenance(path, url):
    return {'url': url, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}


def season_allowed(row):
    seasons = row.get('itemSeasonPhaseData', {})
    return not seasons or '0' in seasons


def item_record(row, icon=None, evidence='vanilla'):
    values = {'id': row['id'], 'name': clean(row.get('displayName') or row.get('name')),
        'quality': row.get('quality'), 'classID': row.get('classs'), 'subclass': row.get('subclass'),
        'slot': row.get('slot'), 'level': row.get('level'), 'requiredLevel': row.get('reqlevel'),
        'status': row.get('envChange', {}).get('status', evidence)}
    if icon:
        values['icon'] = 'Interface\\Icons\\' + icon
    return {key: value for key, value in values.items() if value is not None}


def vanilla_icons(page):
    result = {}
    for match in re.finditer(r'_\[(\d+)\]\s*=\s*\{', page):
        value = LiteralReader(page[match.end() - 1:]).value()
        icon = value.get('icon', '')
        if re.fullmatch(r'[a-zA-Z0-9_]+', icon):
            result[int(match.group(1))] = icon
    return result


def reported_tables(page):
    """Only explicit Encounter/Current known drops tables, with comment IDs."""
    marker = page.find('var lv_comments0 = ')
    if marker < 0:
        return []
    comments = json.JSONDecoder().raw_decode(page[marker + len('var lv_comments0 = '):])[0]
    output = []
    for comment in comments:
        body = comment.get('body', '')
        if comment.get('deleted') or 'Current known drops' not in body or '[b]Encounter' not in body:
            continue
        table = re.search(r'\[table[^\]]*\](.*?)\[/table\]', body, re.S)
        if not table:
            continue
        encounters = []
        for row in re.findall(r'\[tr\](.*?)\[/tr\]', table.group(1), re.S):
            cells = re.findall(r'\[td[^\]]*\](.*?)\[/td\]', row, re.S)
            if len(cells) != 2:
                continue
            npc = re.fullmatch(r'\s*\[npc=(\d+)\](?:\s*\(Rare\))?\s*', cells[0])
            items = [int(v) for v in re.findall(r'\[item=(\d+)\]', cells[1])]
            if npc and items:
                encounters.append((int(npc.group(1)), items, 'Rare' in cells[0]))
        output.append({'commentID': comment['id'], 'author': comment.get('user'),
            'date': comment.get('date'), 'encounters': encounters})
    return output


def gather(page, kind):
    result = {}
    for match in re.finditer(r'WH.Gatherer.addData\(' + str(kind) + r',\s*\d+,\s*', page):
        result.update(json.JSONDecoder().raw_decode(page[match.end():])[0])
    return result


def maps(files, key):
    folder, floors = MAPS.get(key), {}
    for _, path in files:
        parts = path.split('/')
        if len(parts) != 4 or parts[2] != folder or not path.endswith('.blp'):
            continue
        match = re.search(r'(\d+)_(\d+)\.blp$', path)
        if match:
            floor, tile = map(int, match.groups())
        else:
            match = re.search(r'(\d+)\.blp$', path)
            if not match:
                continue
            floor, tile = 1, int(match.group(1))
        if tile <= 12:
            floors.setdefault(floor, {})[tile] = path[:-4].replace('/', '\\')
    return [{'name': 'Floor ' + str(floor), 'width': 1002, 'height': 668,
        'tileWidth': 256, 'tileHeight': 256, 'tiles': [tiles[i] for i in range(1, 13)], 'reference': True}
        for floor, tiles in sorted(floors.items()) if set(tiles) == set(range(1, 13))]


def audit(args):
    definitions = json.loads((ROOT / 'WowTogether/DungeonData.json').read_text())['dungeons']
    reviewed = json.loads(args.encounters.read_text())['dungeons']
    files = list(csv.reader(args.listfile.open(), delimiter=';'))
    heads = {normalize(Path(path).stem.removeprefix('UI-EJ-BOSS-')): path[:-4].replace('/', '\\')
        for _, path in files if '/ui-ej-boss-' in path.lower() and path.endswith('.blp')}
    npcs, membership, objects, object_membership, zone_pages, sources = {}, {}, {}, {}, {}, {}
    for path in sorted(args.zones.glob('*.html')):
        key = path.stem.split('@')[0]
        if key not in definitions:
            raise ValueError('Unknown dungeon zone ' + key)
        page = path.read_text(); zone_pages[path.stem] = page
        zone_id = re.search(r'/forever/zone=(\d+)', page)
        sources[path.stem] = provenance(path, 'https://www.wowhead.com/forever/zone=' + zone_id.group(1))
        for row in rows(page, 'npc', 'npcs'):
            if row['id'] < 200000 or row.get('envChange', {}).get('status') == 'new':
                npcs[row['id']] = row
                membership.setdefault(key, set()).add(row['id'])
        for row in rows(page, 'object', 'objects'):
            if row.get('type') == 3 and row['id'] < 200000:
                objects[row['id']] = row
                object_membership.setdefault(key, set()).add(row['id'])
    boss_ids = {row['id'] for group in reviewed.values() for row in group}
    item_rows, loot, specific, ambiguous, vanilla_sources, npc_sources, container_sources = {}, {}, {}, {}, {}, {}, {}
    missing, seasonal, total_rows = [], 0, 0

    def remember(row, page_icons, evidence):
        ident = row.get('id')
        if type(ident) is not int or ident < 1 or not clean(row.get('displayName') or row.get('name')):
            raise ValueError('Invalid item identity')
        value = item_record(row, page_icons.get(ident), evidence)
        if ident not in item_rows or evidence != 'vanilla':
            item_rows[ident] = value
        return ident

    for ident in sorted(npcs):
        vanilla = args.vanilla / (str(ident) + '.html')
        ids, fixed, uncertain = set(), set(), set()
        if ident < 200000:
            if not vanilla.exists():
                raise ValueError('Incomplete Vanilla NPC capture: ' + str(ident))
            page = vanilla.read_text(); page_icons = vanilla_icons(page)
            vanilla_sources[str(ident)] = provenance(vanilla, 'https://classicdb.ch/?npc=' + str(ident))
            for row in vanilla_rows(page):
                total_rows += 1
                ids.add(remember(row, page_icons, 'vanilla'))
        path = args.npcs / (str(ident) + '.html')
        if not path.exists():
            path = args.bosses / (str(ident) + '.html')
        if path.exists():
            page = path.read_text(); page_icons = icons(page)
            npc_sources[str(ident)] = provenance(path, 'https://www.wowhead.com/forever/npc=' + str(ident))
            for row in rows(page, 'item', 'drops'):
                total_rows += 1
                if not season_allowed(row):
                    seasonal += 1
                    continue
                iid = remember(row, page_icons, 'forever')
                owned = any(source.get('t') == 1 and source.get('ti') == ident for source in row.get('sourcemore', []))
                # Vanilla relationships remain the baseline. Captured Forever
                # specific/new rows add explicit relationships, not historic
                # random drop samples mislabeled as encounter loot.
                if iid in ids or row.get('specificDrop') or row.get('envChange', {}).get('status') == 'new':
                    if iid not in ids and not owned:
                        uncertain.add(iid)
                    ids.add(iid)
                if owned and not row.get('commondrop'):
                    fixed.add(iid)
        else:
            missing.append(ident)
        loot[ident], specific[ident], ambiguous[ident] = ids, fixed, uncertain

    # Zone item tables also explicitly name drop sources. This recovers beta
    # additions when an individual NPC page is inaccessible, without guessing.
    for page in zone_pages.values():
        page_icons = icons(page)
        for row in rows(page, 'item', 'drops'):
            if not season_allowed(row):
                continue
            for source in row.get('sourcemore', []):
                ident = source.get('ti')
                if source.get('t') == 1 and ident in loot:
                    iid = remember(row, page_icons, 'forever')
                    if not row.get('commondrop'):
                        loot[ident].add(iid); specific[ident].add(iid)

    reports = {}
    for key, definition in definitions.items():
        if definition['era'] != 'Forever':
            continue
        for source_key, page in zone_pages.items():
            if source_key.split('@')[0] != key:
                continue
            npc_metadata, item_metadata = gather(page, 1), gather(page, 3)
            for report in reported_tables(page):
                for ident, ids, rare in report['encounters']:
                    name = npc_metadata.get(str(ident), {}).get('name_enus')
                    if not name or any(str(iid) not in item_metadata for iid in ids):
                        raise ValueError('Reported encounter lacks matching public item/NPC metadata')
                    reviewed.setdefault(key, []).append({'id': ident, 'name': name, 'reported': True, 'rare': rare})
                    boss_ids.add(ident); membership.setdefault(key, set()).add(ident)
                    loot.setdefault(ident, set()).update(ids); specific.setdefault(ident, set()).update(ids)
                    for iid in ids:
                        meta = item_metadata[str(iid)]; equip = meta.get('jsonequip', {})
                        row = {'id': iid, 'name': meta['name_enus'], 'quality': meta.get('quality'),
                            'reqlevel': equip.get('reqlevel'), 'slot': equip.get('slotbak')}
                        item_rows.setdefault(iid, item_record(row, meta.get('icon'), 'reported'))
                reports.setdefault(key, []).append({k: v for k, v in report.items() if k != 'encounters'})

    container_loot = {}
    for ident in sorted(objects):
        path = args.containers / (str(ident) + '.html')
        if not path.exists():
            raise ValueError('Incomplete Vanilla container capture: ' + str(ident))
        page = path.read_text(); page_icons = vanilla_icons(page)
        container_sources[str(ident)] = provenance(path, 'https://classicdb.ch/?object=' + str(ident))
        ids = {remember(row, page_icons, 'vanilla') for row in vanilla_rows(page, 'contains')}
        total_rows += len(ids); container_loot[ident] = ids

    nonboss_items = set().union(*(values for ident, values in loot.items() if ident not in boss_ids))
    def ordered(ids):
        return sorted(ids, key=lambda ident: (-item_rows[ident].get('quality', 0), item_rows[ident]['name'], ident))
    def creature(ident, name=None):
        npc = npcs.get(ident, {})
        value = {'id': ident, 'name': clean(name or npc.get('name')), 'dropIDs': ordered(loot.get(ident, set()))}
        level = npc.get('maxlevel')
        if type(level) is int and 1 <= level <= 255:
            value['level'] = level
        return value
    data, coverage = {}, {}
    for key, definition in definitions.items():
        entry = {'name': definition['name'], 'bosses': [], 'trash': [], 'containers': [], 'maps': maps(files, key)}
        used = set()
        for boss in reviewed.get(key, []):
            ident = boss['id']
            if ident in used or ident not in membership.get(key, set()):
                raise ValueError('Unverified/duplicate encounter identity: ' + str(ident))
            used.add(ident)
            value = creature(ident, boss['name']); value['rare'] = boss.get('rare', npcs.get(ident, {}).get('classification') in (2, 4))
            if boss.get('reported'):
                value['reported'] = True
            head = heads.get(normalize(value['name']))
            if head:
                value['portrait'] = head
            # Explicit encounter relationships win. Other white/junk or drops
            # also found on ordinary mobs remain separately labeled shared loot.
            shared = {iid for iid in loot.get(ident, set()) if iid not in specific.get(ident, set())
                and (iid in nonboss_items or iid in ambiguous.get(ident, set())
                    or item_rows[iid].get('quality', 0) < 2 and item_rows[iid].get('classID') not in (12, 13))}
            value['dropIDs'], value['sharedDropIDs'] = ordered(loot.get(ident, set()) - shared), ordered(shared)
            entry['bosses'].append(value)
        for ident in sorted(membership.get(key, set()) - used):
            if loot.get(ident):
                entry['trash'].append(creature(ident))
        for ident in sorted(object_membership.get(key, set())):
            if container_loot[ident]:
                entry['containers'].append({'id': ident, 'name': clean(objects[ident]['name']), 'dropIDs': ordered(container_loot[ident])})
        entry['bosses'].sort(key=lambda value: (value.get('level', 0), value['name'], value['id']))
        entry['trash'].sort(key=lambda value: (value['name'], value['id']))
        entry['containers'].sort(key=lambda value: (value['name'], value['id']))
        data[key] = entry
        expected = membership.get(key, set())
        coverage[key] = {'zoneNPCs': len(expected), 'vanillaNPCs': sum(ident < 200000 for ident in expected),
            'vanillaNPCTablesCaptured': sum(str(ident) in vanilla_sources for ident in expected),
            'foreverNPCTablesCaptured': sum(str(ident) in npc_sources for ident in expected),
            'reportedBosses': sum(boss.get('reported', False) for boss in entry['bosses']),
            'bosses': len(entry['bosses']), 'trashSources': len(entry['trash']), 'containers': len(entry['containers']),
            'missingForeverNPCs': sorted(ident for ident in expected if ident not in boss_ids and str(ident) not in npc_sources),
            'unpublished': not expected}
    counts = {'dungeons': len(data), 'dungeonsWithBosses': sum(bool(value['bosses']) for value in data.values()),
        'bosses': sum(len(value['bosses']) for value in data.values()), 'items': len(item_rows),
        'lootEntries': sum(len(boss['dropIDs']) for value in data.values() for boss in value['bosses']),
        'sharedBossDrops': sum(len(boss['sharedDropIDs']) for value in data.values() for boss in value['bosses']),
        'trashSources': sum(len(value['trash']) for value in data.values()),
        'trashDrops': sum(len(npc['dropIDs']) for value in data.values() for npc in value['trash']),
        'containers': sum(len(value['containers']) for value in data.values()),
        'containerDrops': sum(len(obj['dropIDs']) for value in data.values() for obj in value['containers']),
        'portraits': sum('portrait' in boss for value in data.values() for boss in value['bosses']),
        'mapReferences': sum(bool(value['maps']) for value in data.values()),
        'vanillaNPCTables': len(vanilla_sources), 'vanillaContainerTables': len(container_sources),
        'sourceDropRowsAudited': total_rows, 'seasonOnlyRowsExcluded': seasonal}
    result = {'schema': 2, 'captured': '2026-10-06', 'counts': counts, 'dungeons': data, 'items': item_rows}
    packer = Packer()
    from import_travel_network import encode
    body = 'ns.dungeonJournalData = ' + encode({k: v for k, v in result.items() if k not in ('dungeons', 'items')}) + '\n'
    body += packer.records('dungeon-journal', 'ns.dungeonJournalData.dungeons', data)
    body += packer.records('dungeon-loot-items', 'ns.dungeonJournalData.items', item_rows, lazy_rows=True)
    (ROOT / 'WowTogether/DungeonJournalData.lua').write_text(packer.code(body, 'Audited Vanilla/Forever relationships; item records load on demand. See DUNGEON_VIEWER.md.'))
    manifest = {'schema': 2, 'captured': result['captured'], 'counts': counts, 'coverage': coverage,
        'zoneSources': sources, 'bossSources': {key: value for key, value in npc_sources.items() if int(key) in boss_ids},
        'npcSources': npc_sources, 'vanillaNPCSources': vanilla_sources, 'vanillaContainerSources': container_sources,
        'communityReports': reports, 'encounterReviewSHA256': hashlib.sha256(args.encounters.read_bytes()).hexdigest(),
        'clientFilenameSource': {'repository': 'wowdev/wow-listfile', 'commit': '2ee24a9d0ff98f614997587e32ee6a0074d0de65',
            'sha256': hashlib.sha256(args.listfile.read_bytes()).hexdigest()},
        'limitations': ['All captured Vanilla NPC/container drop rows are mapped; this is source coverage, not measured Forever drop rates.',
            'Vanilla identities are used for classic dungeons. Season-only samples and raid duplicates are excluded.',
            'Captured Forever metadata and explicit new/specific relationships supplement the Vanilla baseline.',
            'Community reports for three new dungeons are reported beta evidence, not Blizzard-certified exhaustive loot.',
            'Unpublished new dungeons and missing beta NPC tables remain unknown. No encounter/map/loot relationship is guessed.',
            'Shared/world drops are separate from encounter loot. Containers are not NPC drops.',
            'Loot tables do not include vendor stock, quest rewards, skinning or gathering resources.',
            'No source scripts, guide prose or external artwork are included.']}
    (ROOT / 'WowTogether/DungeonJournalData.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(counts, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('zones', 'npcs', 'bosses', 'vanilla', 'containers', 'listfile'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--encounters', type=Path, default=ROOT / 'tools/dungeon_encounters.json')
    audit(parser.parse_args())


if __name__ == '__main__':
    main()
