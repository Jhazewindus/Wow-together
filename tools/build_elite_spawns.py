"""Compile full elite-target spawn facts without altering guide destinations.

Read owned quest facts and a checksum-pinned Vanilla numeric spawn snapshot.
Older-world positions are restricted to identity-matched unchanged quests.
Only published map bounds convert coordinates; no terrain or live spawn state
is inferred and no source SQL, JavaScript or addon code is executed.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path

from build_quest_dataset import own_lua
from forever_map_geometry import read_geometry
from import_dungeon_positions import sql_spawns
from legacy_quest_facts import COMMIT, SNAPSHOT_SHA256
from pack_data import elite_spawn_code

ROOT = Path(__file__).resolve().parents[1]
ACTIONS = {'kill', 'loot', 'collect'}


def sequence(value):
    return value if isinstance(value, list) else []


def target_ids(quest):
    result = set()
    for point in sequence(quest.get('objectives')) + sequence(quest.get('npcTargets')):
        if point.get('npc') and point.get('action') in ACTIONS:
            result.add(point.get('entityID'))
            result.update(sequence(point.get('alternativeEntityIDs')))
    for ref in sequence(quest.get('requirements')):
        if ref.get('entityType') == 'npc' and ref.get('action', 'kill') in ACTIONS:
            result.add(ref.get('entityID'))
            result.update(sequence(ref.get('alternativeEntityIDs')))
    return {ident for ident in result if type(ident) is int and ident > 0}


def reference_allowed(quest):
    return bool(quest.get('legacyFactsSource') and quest.get('foreverStatus') == 'unchanged')


def build(args):
    digest = hashlib.sha256(args.snapshot.read_bytes()).hexdigest()
    if digest != SNAPSHOT_SHA256:
        raise ValueError('Spawn snapshot differs from the reviewed Vanilla source')
    transforms, _, geometry = read_geometry(args.geometry)
    catalogue = own_lua(ROOT / 'WowTogether/QuestCatalogue.lua', 'catalogue')
    entities = own_lua(ROOT / 'WowTogether/QuestCatalogue.lua', 'questEntities')['npc']
    targets, references = {}, {}
    for ident, quest in catalogue['quests'].items():
        for npc in target_ids(quest):
            entity = entities.get(npc, {})
            rank = entity.get('classification')
            if rank not in (1, 2, 3) and not (rank is None and quest.get('questType') == 'Elite'):
                continue
            targets.setdefault(npc, set()).add(ident)
            if reference_allowed(quest):
                references.setdefault(npc, set()).add(ident)
    spawns = sql_spawns(args.snapshot)['npc']
    rows = {}
    for ident, ids in sorted(targets.items()):
        published, fallback = set(), set()
        for quest_id in sorted(ids):
            quest = catalogue['quests'][quest_id]
            points = list(sequence(quest.get('objectives')))
            for alternatives in sequence(quest.get('objectiveAlternatives')):
                points.extend(sequence(alternatives.get('locations')))
            for point in points:
                if point.get('entityID') != ident or not point.get('npc'):
                    continue
                map_id, x, y = point.get('mapID'), point.get('x'), point.get('y')
                if type(map_id) is not int or type(x) not in (int, float) or type(y) not in (int, float) or not (0 <= x <= 1 and 0 <= y <= 1):
                    continue
                value = (map_id, round(x, 6), round(y, 6))
                basis = point.get('locationSource', '').lower()
                if point.get('worldFallback') or 'older-world' in basis or 'converted-baseline' in basis:
                    if quest_id in references.get(ident, set()):
                        fallback.add(value)
                else:
                    published.add(value)
        if ident in references:
            for point in spawns.get(ident, []):
                for map_id, transform in transforms.items():
                    if point['map'] != transform['continent']:
                        continue
                    x = transform['sx'] * point['worldY'] + transform['ox']
                    y = transform['sy'] * point['worldX'] + transform['oy']
                    if 0 <= x <= 1 and 0 <= y <= 1:
                        fallback.add((map_id, round(x, 6), round(y, 6)))
        if published or fallback:
            rows[ident] = {'name': entities.get(ident, {}).get('name', ''),
                'classification': entities.get(ident, {}).get('classification'),
                'published': [list(value) for value in sorted(published)],
                'reference': [list(value) for value in sorted(fallback - published)],
                'referenceQuestIDs': sorted(references.get(ident, []))}
            if rows[ident]['classification'] is None:
                del rows[ident]['classification']
    counts = {'targets': len(rows), 'publishedPoints': sum(len(row['published']) for row in rows.values()),
        'referencePoints': sum(len(row['reference']) for row in rows.values()),
        'quests': len(set().union(*targets.values()))}
    meta = {'schema': 1, 'captured': datetime.date.today().isoformat(), 'counts': counts}
    (ROOT / 'WowTogether/EliteSpawnData.lua').write_text(elite_spawn_code(dict(meta, npcs=rows)))
    manifest = dict(meta, questCatalogueSHA256=hashlib.sha256((ROOT / 'WowTogether/QuestCatalogue.lua').read_bytes()).hexdigest(),
        sources=[{'url': 'https://github.com/cmangos/classic-db/blob/' + COMMIT + '/Full_DB/ClassicDB_1_12_1_z2815.sql.gz',
            'commit': COMMIT, 'sha256': digest}, geometry],
        limitations=['Every selected reference spawn is retained; duplicate coordinates are merged.',
            'Published objective/alternative points can be representative rather than exhaustive.',
            'Vanilla positions are gated by unchanged quest identity and matching objective NPC IDs.',
            'Possible locations do not establish current beta spawns, respawn times, patrol position or walkable access.'])
    (ROOT / 'WowTogether/EliteSpawnData.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(counts))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--geometry', type=Path, required=True)
    build(parser.parse_args())
