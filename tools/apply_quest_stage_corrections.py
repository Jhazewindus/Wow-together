"""Apply reviewed quest and stage facts to a packed catalogue, without recapture.

The full dataset builder and supplemental importer apply the same corrections.
This command preserves unrelated records and source capture provenance.
"""
import argparse
import collections
import copy
import json
from pathlib import Path

from build_quest_dataset import own_lua
from import_warcraftdb import apply_corrections, apply_stage_corrections
from pack_data import quest_code


def apply(directory):
    path = directory / 'QuestCatalogue.lua'
    catalogue = own_lua(path, 'catalogue')
    before = copy.deepcopy(catalogue['quests'])
    exclusions = json.loads((Path(__file__).resolve().parent / 'quest_exclusions.json').read_text())
    for exclusion in exclusions:
        for ident in exclusion['questIDs']:
            quest = catalogue['quests'].get(ident)
            if quest is None:
                continue
            if quest['title'] != exclusion['title']:
                raise ValueError('Guide exclusion quest identity changed; review required')
            quest['levelingExcluded'] = exclusion['reason']
    apply_corrections(catalogue['quests'])
    stage_changes = apply_stage_corrections(catalogue['quests'])
    changed = sorted(i for i, q in catalogue['quests'].items() if q != before[i])
    if not changed:
        return []
    code = quest_code(catalogue, own_lua(path, 'questEntities'),
                      own_lua(path, 'worldQuestChecks'), own_lua(path, 'xpBaseline'))
    metadata = json.loads((directory / 'QuestCatalogue.json').read_text())
    coverage = json.loads((directory / 'QuestCoverage.json').read_text())
    records = catalogue['quests']
    for key, role in (('with_starters', 'starts'), ('with_objectives', 'objectives'), ('with_turnins', 'ends')):
        metadata[key] = sum(bool(q.get(role)) for q in records.values())
        coverage['summary'][key] = metadata[key]
    metadata['incomplete_objective_locations'] = sum(bool(q.get('objectiveLocationsIncomplete')) for q in records.values())
    reviewed = sorted(set(metadata.get('reviewed_stage_corrections', [])) | set(stage_changes))
    metadata['reviewed_stage_corrections'] = reviewed
    coverage['reviewed_stage_corrections'] = reviewed
    metadata['reviewed_quest_corrections'] = sorted(set(metadata.get('reviewed_quest_corrections', [])) | set(changed))
    zones = collections.defaultdict(lambda: {'quests': 0, 'pickups': 0, 'objectives': 0,
                                            'turnins': 0, 'complete_locations': 0, 'missing_quest_ids': []})
    for ident, q in sorted(records.items()):
        zone = q.get('categoryPath') or q.get('zone') or 'Unknown category'
        if zone == 'uncategorized' and q.get('mapID'):
            zone = 'map:' + str(q['mapID']) + ' / ' + (q.get('zone') or 'Published zone ' + str(q['areaID']))
        row = zones[zone]
        row['quests'] += 1
        for role, key in (('starts', 'pickups'), ('objectives', 'objectives'), ('ends', 'turnins')):
            row[key] += bool(q.get(role))
        complete = bool(q.get('starts') and q.get('ends') and q.get('prerequisitesRead')
                        and not q.get('objectiveLocationsIncomplete') and (q.get('objectives') or not q.get('requirements')))
        if complete:
            row['complete_locations'] += 1
        else:
            row['missing_quest_ids'].append(ident)
    coverage['zones'] = dict(sorted(zones.items()))
    path.write_text(code)
    (directory / 'QuestCatalogue.json').write_text(json.dumps(metadata, indent=2) + '\n')
    (directory / 'QuestCoverage.json').write_text(json.dumps(coverage, indent=2) + '\n')
    return changed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path(__file__).resolve().parents[1] / 'WowTogether')
    args = parser.parse_args()
    print('Changed quest records:', apply(args.directory))
