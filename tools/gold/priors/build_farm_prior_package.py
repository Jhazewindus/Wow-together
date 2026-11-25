"""Build the optional routable farm index from pinned legacy JSON facts.

Spawn positions are converted using the pinned published Forever map bounds.
The result is still explicitly unconfirmed legacy reference data; it does not
assert that the spawns, levels, or loot are present on the live server.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PRIORS = Path(__file__).resolve().parent
DEST = ROOT / 'WowTogether_GoldData'
SPAWN_PACKAGE = ROOT / 'WowTogether_GoldSpawnData'
sys.path.insert(0, str(ROOT / 'tools'))
from forever_map_geometry import read_geometry
from pack_data import Packer

LEGACY = ('CMaNGOS ClassicDB ec4f596146be6467ea93c57397858e329e2db852; legacy, unconfirmed; '
          'https://github.com/cmangos/classic-db/blob/ec4f596146be6467ea93c57397858e329e2db852/Full_DB/ClassicDB_1_12_1_z2815.sql.gz')
FISH_SOURCE = 'CMaNGOS ClassicDB; legacy, unconfirmed; fishing area/reference loot'
GEOMETRY = ('QuestieDB Forever 1.60.1.69893 published map bounds, commit '
            'e0a6eaa86f181ac99262e34126bcd2ed1a1712d6; '
            'https://github.com/Questie/QuestieDB/blob/e0a6eaa86f181ac99262e34126bcd2ed1a1712d6/data/Forever/conversion.json')


def read_rows(name):
    return json.loads((PRIORS / (name + '.json')).read_text(encoding='utf-8'))['rows']


def build_records(geometry_path: Path, creatures=None, loot_rows=None):
    transforms, _, _ = read_geometry(geometry_path)
    creatures = read_rows('creatures') if creatures is None else creatures
    loot_rows = read_rows('creature_loot') if loot_rows is None else loot_rows
    skinning_rows = read_rows('creature_skinning_loot')
    by_loot = defaultdict(list)
    for row in loot_rows:
        item = row.get('itemId')
        chance = row.get('chanceOrQuestChance')
        # Negative reference IDs encode table links, not item yields; do not guess.
        count = row.get('minCountOrReference')
        if isinstance(item, int) and item > 0 and isinstance(count, int) and count > 0 \
                and isinstance(chance, (int, float)) and 0.5 <= chance <= 100:
            by_loot[row.get('ownerLootId')].append({'itemID': item, 'chance': chance, 'quantity': count,
                'source': LEGACY + '; creature_loot_template chance'})
    by_skinning = defaultdict(list)
    for row in skinning_rows:
        item = row.get('itemId')
        chance = row.get('chanceOrQuestChance')
        count = row.get('minCountOrReference')
        if isinstance(item, int) and item > 0 and isinstance(count, int) and count > 0 \
                and isinstance(chance, (int, float)) and 0.5 <= chance <= 100:
            by_skinning[row.get('ownerLootId')].append({'itemID': item, 'chance': chance,
                'quantity': count, 'source': LEGACY + '; skinning_loot_template chance; legacy, unconfirmed'})

    records = []
    for creature in creatures:
        loot = by_loot.get(creature.get('lootId'), [])
        if not loot:
            # Skinning-only candidates remain part of the creature's normal
            # farm and appear only when the character has Skinning.
            if not by_skinning.get(creature.get('skinLootId')):
                continue
        grouped = defaultdict(set)
        for spawn in creature.get('spawns') or []:
            for transform in transforms.values():
                if transform['continent'] != spawn.get('map'):
                    continue
                x = transform['sx'] * spawn['worldY'] + transform['ox']
                y = transform['sy'] * spawn['worldX'] + transform['oy']
                if 0 <= x <= 1 and 0 <= y <= 1:
                    grouped[(transform['mapID'], transform['targetName'])].add((round(x, 6), round(y, 6)))
        # A legacy creature can have coordinates on both sides of a zone
        # border. Keep the zone with the most converted points as the single
        # routable candidate; ties use the smaller map ID for stable output.
        populated = [(map_id, zone, points) for (map_id, zone), points in grouped.items() if points]
        if not populated:
            continue
        map_id, zone, points = min(populated, key=lambda row: (-len(row[2]), row[0], row[1]))
        if points:
            skinning_loot = by_skinning.get(creature.get('skinLootId'), [])
            records.append({'npcID': creature['id'], 'name': creature['name'],
                'confidence': 'legacy, unconfirmed',
                'minLevel': max(1, creature['minLevel']), 'maxLevel': max(1, creature['maxLevel']),
                'mapID': map_id, 'zoneName': zone,
                'spawnPoints': [{'mapID': map_id, 'x': x, 'y': y, 'source': GEOMETRY + '; converted legacy world coordinate'}
                    for x, y in sorted(points)[:24]],
                'loot': loot[:200], 'skinnable': bool(creature.get('skinLootId')),
                'skinningLoot': skinning_loot[:200],
                'sources': {'npcID': LEGACY + '; creature_template entry', 'name': LEGACY + '; creature_template name',
                    'level': LEGACY + '; creature_template minlevel/maxlevel', 'mapID': GEOMETRY + '; ui_map_id',
                    'zoneName': GEOMETRY + '; target_name',
                    'spawnPoints': 'CMaNGOS pinned legacy world positions converted by QuestieDB Forever map bounds; unconfirmed',
                    'loot': LEGACY + '; creature_loot_template rows',
                    'skinnable': LEGACY + '; creature_template SkinningLootId',
                    'skinningLoot': LEGACY + '; skinning_loot_template rows'}})
    records.sort(key=lambda row: (row['npcID'], row['mapID']))
    return records


def build_gathering_records(geometry_path: Path):
    transforms, area_to_map, _ = read_geometry(geometry_path)
    objects = read_rows('gameobjects')
    loot_rows = read_rows('gameobject_loot')
    fishing_rows = read_rows('fishing_loot')
    reference_rows = read_rows('reference_loot')
    items = read_rows('items')
    item_names = {row.get('id'): row.get('name', '') for row in items}
    from collections import defaultdict
    by_loot = defaultdict(list)
    for row in loot_rows:
        item, chance, count = row.get('itemId'), row.get('chanceOrQuestChance'), row.get('minCountOrReference')
        if isinstance(item, int) and item > 0 and isinstance(count, int) and count > 0 \
                and isinstance(chance, (int, float)) and 0 < chance <= 100:
            by_loot[row.get('ownerLootId')].append({'itemID': item, 'chance': chance, 'quantity': count,
                'source': 'Pinned CMaNGOS gameobject_loot_template; legacy, unconfirmed'})
    node_names = {
        'Copper Vein', 'Tin Vein', 'Silver Vein', 'Iron Deposit', 'Gold Vein', 'Mithril Deposit',
        'Truesilver Deposit', 'Dark Iron Deposit', 'Small Thorium Vein', 'Rich Thorium Vein',
        'Heavy Thorium Vein', 'Peacebloom', 'Silverleaf', 'Earthroot', 'Mageroyal', 'Briarthorn',
        'Stranglekelp', 'Bruiseweed', 'Wild Steelbloom', 'Grave Moss', 'Kingsblood', 'Liferoot',
        'Fadeleaf', 'Goldthorn', "Khadgar's Whisker", 'Wintersbite', 'Firebloom', 'Purple Lotus',
        "Arthas' Tears", 'Sungrass', 'Blindweed', 'Ghost Mushroom', 'Gromsblood', 'Golden Sansam',
        'Dreamfoil', 'Mountain Silversage', 'Plaguebloom', 'Icecap', 'Black Lotus',
    }
    results = {}
    for obj in objects:
        name = obj.get('name', '')
        loot = by_loot.get(obj.get('lootId'), [])
        if obj.get('type') != 3 or not loot:
            continue
        if name not in node_names and not any(word in name.lower() for word in ('school', 'pool', 'floating wreckage')):
            continue
        zones = set()
        for spawn in obj.get('spawns') or []:
            for transform in transforms.values():
                if transform['continent'] != spawn.get('map'):
                    continue
                x = transform['sx'] * spawn['worldY'] + transform['ox']
                y = transform['sy'] * spawn['worldX'] + transform['oy']
                if 0 <= x <= 1 and 0 <= y <= 1:
                    zones.add((transform['mapID'], transform['targetName']))
        for map_id, zone in zones:
            # Pool species are keyed by zone. Named ore/herb nodes stay keyed by
            # their exact source template and map.
            profession, node = ('Fishing', zone) if name not in node_names else (
                'Mining' if 'Vein' in name or 'Deposit' in name else 'Herbalism', name)
            key = profession + '|' + node + '|' + str(map_id)
            current = results.setdefault(key, {'profession': profession, 'node': node,
                'mapID': map_id, 'zoneName': zone, 'loot': [],
                'source': LEGACY + '; gameobject template and loot rows'})
            known = {item['itemID'] for item in current['loot']}
            for item in loot:
                if item['itemID'] not in known:
                    current['loot'].append(item); known.add(item['itemID'])

    # ClassicDB's fishing table is keyed by legacy area ID. Map only areas
    # represented in the pinned Forever map-bound report; never infer a zone
    # from a fishing skill tier or a pool name.
    refs = defaultdict(list)
    for row in reference_rows:
        refs[row.get('ownerLootId')].append(row)
    fish_by_area = defaultdict(list)
    fish_tokens = ('fish', 'eel', 'snapper', 'trout', 'salmon', 'bass', 'catfish',
        'grouper', 'lobster', 'crushfish', 'armorfish', 'mightfish', 'redgill',
        'yellowtail', 'mackerel', 'frenzy')
    def is_fish(item_id):
        return isinstance(item_id, int) and item_id > 0 and any(
            token in item_names.get(item_id, '').lower() for token in fish_tokens)
    def expand_reference(reference_id, parent_chance, path=()):
        # Reference rows may point to further reference rows. Multiply each
        # link's chance, and stop cycles rather than inventing a fallback rate.
        if reference_id in path or len(path) >= 12:
            return []
        expanded = []
        for child in refs.get(reference_id, []):
            item_id = child.get('itemId')
            chance = child.get('chanceOrQuestChance')
            count = child.get('minCountOrReference')
            if not isinstance(chance, (int, float)) or chance <= 0 or chance > 100:
                continue
            combined = parent_chance * chance / 100
            if is_fish(item_id) and isinstance(count, int) and count > 0:
                expanded.append({'itemID': item_id, 'chance': combined,
                    'quantity': count, 'source': FISH_SOURCE})
            elif isinstance(count, int) and count < 0:
                expanded.extend(expand_reference(abs(count), combined, path + (reference_id,)))
        return expanded
    for row in fishing_rows:
        item, chance, count = row.get('itemId'), row.get('chanceOrQuestChance'), row.get('minCountOrReference')
        if not isinstance(chance, (int, float)) or chance <= 0 or chance > 100: continue
        if is_fish(item) and isinstance(count, int) and count > 0:
            fish_by_area[row.get('ownerLootId')].append({'itemID': item, 'chance': chance,
                'quantity': count, 'source': FISH_SOURCE})
        elif isinstance(count, int) and count < 0:
            fish_by_area[row.get('ownerLootId')].extend(expand_reference(abs(count), chance))
    for area_id, fish in fish_by_area.items():
        map_id = area_to_map.get(area_id)
        transform = transforms.get(map_id)
        if not transform: continue
        zone = transform['targetName']
        key = 'Fishing|' + zone + '|' + str(map_id)
        current = results.setdefault(key, {'profession': 'Fishing', 'node': zone,
            'mapID': map_id, 'zoneName': zone, 'loot': [],
            'source': FISH_SOURCE})
        known = {item['itemID'] for item in current['loot']}
        for item in fish:
            if item['itemID'] not in known:
                current['loot'].append(item); known.add(item['itemID'])
    return results


def render(records):
    packer = Packer()
    body = 'ns.farmPriorData = {count = ' + str(len(records)) + '}\n'
    index_records = {}
    for index, source in enumerate(records, 1):
        row = dict(source)
        row['spawnPointCount'] = len(row.get('spawnPoints') or [])
        row.pop('spawnPoints', None)
        row.get('sources', {}).pop('spawnPoints', None)
        index_records[index] = row
    body += packer.records('gold-farm-priors', 'ns.farmPriorData.records',
        index_records, lazy_rows=True)
    return packer.code(body, 'Legacy, unconfirmed farm index; spawn coordinates load by zone when starting a farm.')


def render_spawn_zone(map_id, zone_name, records):
    packer = Packer()
    payloads = {}
    for row in records:
        points = []
        for point in row['spawnPoints']:
            points.append({'mapID': map_id, 'x': point['x'], 'y': point['y'],
                'source': 'QuestieDB Forever map bounds; converted legacy world coordinate'})
        payloads[row['npcID']] = {'npcID': row['npcID'], 'mapID': map_id, 'spawnPoints': points}
    body = 'ns.farmSpawnDataByMap = ns.farmSpawnDataByMap or {}\n'
    body += 'ns.farmSpawnDataByMap[' + str(map_id) + '] = {mapID = ' + str(map_id) \
        + ', zoneName = ' + repr(zone_name) + ', count = ' + str(len(payloads)) + ', records = {}}\n'
    body += packer.records('gold-farm-spawns-' + str(map_id),
        'ns.farmSpawnDataByMap[' + str(map_id) + '].records', payloads, lazy_rows=True)
    source = packer.code(body, 'Legacy, unconfirmed spawn positions; see PRIOR_DATA.md and GPL-3.0.txt.')
    destination = SPAWN_PACKAGE / 'zones' / (str(map_id) + '.lua')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(source, encoding='utf-8')
    return len(payloads)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--geometry', type=Path, required=True)
    args = parser.parse_args()
    records = build_records(args.geometry)
    gathering = build_gathering_records(args.geometry)
    DEST.mkdir(exist_ok=True)
    (DEST / 'FarmPriorData.lua').write_text(render(records), encoding='utf-8')
    zone_rows = defaultdict(list)
    for row in records:
        zone_rows[(row['mapID'], row['zoneName'])].append(row)
    for old in ROOT.glob('WowTogether_GoldSpawnData_*'):
        if old.is_dir():
            import shutil
            shutil.rmtree(old)
    if SPAWN_PACKAGE.exists():
        import shutil
        shutil.rmtree(SPAWN_PACKAGE)
    spawn_counts = {}
    for (map_id, zone_name), rows in sorted(zone_rows.items()):
        spawn_counts[str(map_id)] = render_spawn_zone(map_id, zone_name, rows)
    toc = ['## Interface: 16001', '## Title: Wow Together Gold Spawn Data',
        '## Notes: Legacy, unconfirmed spawn points for farm loops',
        '## LoadOnDemand: 1', '## Dependencies: WowTogether']
    toc.extend('zones\\' + map_id + '.lua' for map_id in sorted(spawn_counts, key=int))
    (SPAWN_PACKAGE / 'WowTogether_GoldSpawnData.toc').write_text('\n'.join(toc) + '\n', encoding='utf-8')
    # Keep the two domains separate in the same LOD package. This file is
    # generated through the same packed-data decoder but has zone-keyed rows.
    gathering_packer = Packer()
    gathering_body = 'ns.gatheringFarmData = {count = ' + str(len(gathering)) + '}\n'
    gathering_body += gathering_packer.records('gold-gathering-priors',
        'ns.gatheringFarmData.records', gathering, lazy_rows=True)
    gathering_payload = gathering_packer.code(gathering_body,
        'Legacy, unconfirmed gathering loot; see LEGACY_DATA_COPYRIGHT.md and LEGACY_DATA_LICENSE.txt.')
    (DEST / 'GatheringPriorData.lua').write_text(gathering_payload, encoding='utf-8')
    print(json.dumps({'records': len(records), 'gatheringZoneRecords': len(gathering),
        'spawnZonePackages': spawn_counts, 'lootChanceFloorPercent': 0.5, 'loadOnDemand': True,
        'confidence': 'legacy, unconfirmed', 'lootRowsWithUnsupportedReferenceIDsOmitted': True}))


if __name__ == '__main__':
    main()
