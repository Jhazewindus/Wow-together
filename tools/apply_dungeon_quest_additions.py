"""Add explicitly captured dungeon quests missing from the zone catalogue.

This importer accepts only IDs named by the reviewed dungeon category manifest
and verifies the exact category and detail page hashes before writing data.
Missing prerequiste/location facts remain unknown; no route or chain is guessed.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from build_quest_dataset import ROOT, own_lua
from import_wowhead import detail_facts, list_rows
from pack_data import quest_code
from quest_enrichment import enrich, mapper_entities, quest_relations


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply(cache, output_directory=None):
    manifest = json.loads((ROOT / 'tools/dungeon_quest_additions.json').read_text())
    category_path = cache / ('dungeons-' + manifest['dungeonKey'] + '.html')
    if not category_path.exists() or digest(category_path) != manifest['category']['sha256']:
        raise ValueError('Dungeon category capture is missing or has changed; review it first')
    rows = {row['id']: row for row in list_rows(category_path.read_text())}
    expected_ids = set(manifest['category']['questIDs'])
    if set(rows) != expected_ids:
        raise ValueError('Dungeon category membership changed; review the new list first')

    catalogue_path = ROOT / 'WowTogether_QuestData/QuestCatalogue.lua'
    catalogue = own_lua(catalogue_path, 'catalogue')
    entities = own_lua(catalogue_path, 'questEntities')
    world_checks = own_lua(catalogue_path, 'worldQuestChecks')
    metadata_path = ROOT / 'WowTogether/QuestCatalogue.json'
    metadata = json.loads(metadata_path.read_text())
    coverage_path = ROOT / 'WowTogether/QuestCoverage.json'
    coverage = json.loads(coverage_path.read_text())
    area_maps = {int(key): value for key, value in metadata['area_ui_maps'].items()}
    records = catalogue['quests']
    added = []

    manifest_records = {row['id']: row for row in manifest['records']}
    if set(manifest_records) != expected_ids:
        raise ValueError('Quest source manifest and category list disagree')
    for ident in sorted(expected_ids):
        declared = manifest_records[ident]
        page_path = cache / ('quest-' + str(ident) + '.html')
        if not page_path.exists() or digest(page_path) != declared['sha256']:
            raise ValueError('Quest page capture is missing or has changed: ' + str(ident))
        if ident in records:
            if records[ident].get('title') != declared['title']:
                raise ValueError('Quest ID now conflicts with the existing catalogue: ' + str(ident))
            continue

        page = page_path.read_text()
        row = rows[ident]
        fact = detail_facts(page, {'id': ident}, area_maps, records)
        if fact.get('title') != declared['title'] or row.get('name') != declared['title']:
            raise ValueError('Quest title changed; review required: ' + str(ident))
        relation = quest_relations(page)
        fact['categoryPath'] = 'dungeons/' + manifest['dungeonKey']
        fact['dungeonSource'] = declared['url'] + ' (SHA-256 ' + declared['sha256'] + ')'
        fact['dungeonCategorySource'] = manifest['category']['url'] + ' (SHA-256 ' + manifest['category']['sha256'] + ')'
        fact['worldReferences'] = copy.deepcopy(relation)
        fact['startRefs'] = copy.deepcopy(relation.get('starts', []))
        fact['endRefs'] = copy.deepcopy(relation.get('ends', []))
        fact['requirements'] = copy.deepcopy(relation.get('requirements', []))
        if relation.get('provided'):
            fact['providedItems'] = copy.deepcopy(relation['provided'])
        # A detail page with no visible series is not proof that no prerequisite
        # exists. Keep the quest blocked from an invented automatic chain.
        fact.pop('prerequisitesRead', None)
        fact['prerequisitesUnverified'] = True
        fact['objectiveLocationsIncomplete'] = True
        fact['otherLocationsIncomplete'] = True
        for kind, entity_id, entity in mapper_entities(page, area_maps):
            current = entities[kind].setdefault(entity_id, {'name': entity.get('name', ''), 'locations': []})
            if not current.get('name') and entity.get('name'):
                current['name'] = entity['name']
            for point in entity.get('locations', []):
                if point not in current['locations']:
                    current['locations'].append(point)
        for ref in [*relation.get('starts', []), *relation.get('ends', []), *relation.get('requirements', []), *relation.get('provided', [])]:
            if ref.get('entityType') in ('item', 'object', 'npc') and type(ref.get('entityID')) is int:
                current = entities[ref['entityType']].setdefault(ref['entityID'], {'name': ref.get('name', ''), 'locations': []})
                if not current.get('name') and ref.get('name'):
                    current['name'] = ref['name']
        enrich(fact, relation, entities)
        # Enrichment preserves the source's explicit missing points and does
        # not infer item-to-NPC drops or quest pickup locations.
        fact['objectiveLocationsIncomplete'] = True
        fact['otherLocationsIncomplete'] = True
        records[ident] = fact
        added.append(ident)

    if not added:
        print('No new dungeon quest records; catalogue already includes the reviewed list.')
        return []
    catalogue['count'] = len(records)
    (ROOT / 'WowTogether_QuestData/QuestCatalogue.lua').write_text(
        quest_code(catalogue, entities, world_checks, None))
    now = manifest['captured']
    metadata['captured'] = now
    metadata['count'] = len(records)
    metadata['detailed_quests'] += len(added)
    metadata['with_starters'] = sum(bool(q.get('starts')) for q in records.values())
    metadata['with_objectives'] = sum(bool(q.get('objectives')) for q in records.values())
    metadata['with_turnins'] = sum(bool(q.get('ends')) for q in records.values())
    metadata['with_series'] = sum(bool(q.get('series')) for q in records.values())
    metadata['with_prerequisites'] = sum(bool(q.get('previousQuest') or q.get('prerequisiteAny') or q.get('prerequisiteAll')) for q in records.values())
    metadata['unverified_prerequisites'] = sum(bool(q.get('prerequisitesUnverified')) for q in records.values())
    metadata['incomplete_objective_locations'] = sum(bool(q.get('objectiveLocationsIncomplete')) for q in records.values())
    metadata['zones'] = sorted(set(metadata['zones']) | {'dungeons/' + manifest['dungeonKey']})
    metadata['entities'] = {kind: len(rows) for kind, rows in entities.items()}
    metadata['dungeon_quest_additions'] = {
        'captured': now, 'category': manifest['category'], 'records': added,
        'limitations': manifest['limitations']}
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + '\n')

    zones = {}
    for ident, quest in sorted(records.items()):
        zone = quest.get('categoryPath') or quest.get('zone') or 'Unknown category'
        if zone == 'uncategorized' and quest.get('mapID'):
            zone = 'map:' + str(quest['mapID']) + ' / ' + (quest.get('zone') or 'Published zone ' + str(quest['areaID']))
        entry = zones.setdefault(zone, {'quests': 0, 'pickups': 0, 'objectives': 0, 'turnins': 0,
                                        'complete_locations': 0, 'missing_quest_ids': []})
        entry['quests'] += 1
        for field, label in (('starts', 'pickups'), ('objectives', 'objectives'), ('ends', 'turnins')):
            if quest.get(field):
                entry[label] += 1
        complete = bool(quest.get('starts') and quest.get('ends') and quest.get('prerequisitesRead')
                        and not quest.get('objectiveLocationsIncomplete')
                        and (quest.get('objectives') or not quest.get('requirements')))
        if complete:
            entry['complete_locations'] += 1
        else:
            entry['missing_quest_ids'].append(ident)
    coverage['captured'] = now
    coverage['summary'].update({key: metadata[key] for key in (
        'count', 'detailed_quests', 'with_starters', 'with_objectives', 'with_turnins', 'with_prerequisites')})
    coverage['summary']['entities'] = metadata['entities']
    coverage['zones'] = dict(sorted(zones.items()))
    coverage['dungeon_quest_additions'] = metadata['dungeon_quest_additions']
    coverage_path.write_text(json.dumps(coverage, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'added': added, 'catalogueCount': len(records), 'detailedQuestCount': metadata['detailed_quests']}, indent=2))
    return added


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True, help='Captured dungeon category and quest pages')
    args = parser.parse_args()
    apply(args.cache)


if __name__ == '__main__':
    main()
