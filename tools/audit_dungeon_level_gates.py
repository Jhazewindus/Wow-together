"""Report recorded dungeon prerequisites whose minimum level exceeds the child.

This scans only prerequisite edges already present in the catalogue. It cannot
infer a missing edge; use source captures, QuestieDB corrections and in-game
observations to discover and add those separately.
"""
import argparse
import json

from build_quest_dataset import ROOT, own_lua


def scan():
    catalogue = own_lua(ROOT / 'WowTogether_QuestData' / 'QuestCatalogue.lua', 'catalogue')['quests']
    dungeons = own_lua(ROOT / 'WowTogether' / 'DungeonData.lua', 'dungeonData')['dungeons']
    memberships, unique, missing, unknown = 0, set(), [], set()
    edges = {}
    group_ids = {key: set(dungeon.get('questIDs') or []) for key, dungeon in dungeons.items()}
    for child_id, child in catalogue.items():
        path = child.get('categoryPath') or ''
        if child.get('questType') == 'Dungeon' or path.startswith('dungeons/'):
            slug = path[len('dungeons/'):] if path.startswith('dungeons/') else None
            if slug in group_ids:
                group_ids[slug].add(child_id)
    for key, dungeon in sorted(dungeons.items()):
        for child_id in sorted(group_ids[key]):
            memberships += 1
            unique.add(child_id)
            child = catalogue.get(child_id)
            if child is None:
                missing.append({'dungeon': key, 'questID': child_id})
                continue
            if child.get('prerequisitesUnverified') or child.get('prerequisitesRead') is False:
                unknown.add((key, child_id))
            parents = []
            if child.get('previousQuest'):
                parents.append(('previousQuest', child['previousQuest']))
            for parent in child.get('prerequisiteAll') or []:
                parents.append(('prerequisiteAll', parent))
            for parent in child.get('prerequisiteAny') or []:
                parents.append(('prerequisiteAny', parent))
            for relation, parent_id in parents:
                parent = catalogue.get(parent_id)
                if parent is None:
                    missing.append({'dungeon': key, 'parentQuestID': parent_id, 'childQuestID': child_id})
                    continue
                parent_level = parent.get('minLevel') or parent.get('level') or 0
                child_level = child.get('minLevel') or child.get('level') or 0
                if parent_level <= child_level:
                    continue
                edge = edges.setdefault((key, parent_id, child_id), {
                    'dungeon': key,
                    'parentQuestID': parent_id,
                    'parentTitle': parent.get('title'),
                    'parentMinLevel': parent_level,
                    'questID': child_id,
                    'title': child.get('title'),
                    'minLevel': child_level,
                    'relations': [],
                    'prerequisiteSource': child.get('prerequisiteSource'),
                })
                if relation not in edge['relations']:
                    edge['relations'].append(relation)
    rows = sorted(edges.values(), key=lambda row: (row['dungeon'], row['parentQuestID'], row['questID']))
    return {
        'counts': {
            'dungeonCategories': len(dungeons),
            'listedQuestMemberships': memberships,
            'uniqueListedQuests': len(unique),
            'missingCatalogueRecords': len(missing),
            'higherMinimumPrerequisiteEdges': len(rows),
            'unverifiedPrerequisiteMemberships': len(unknown),
        },
        'higherMinimumPrerequisites': rows,
        'unverifiedPrerequisiteMemberships': [
            {'dungeon': dungeon, 'questID': quest_id,
             'title': catalogue[quest_id].get('title')}
            for dungeon, quest_id in sorted(unknown)
        ],
        'missingRecords': missing,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true', help='print the complete report as JSON')
    args = parser.parse_args()
    report = scan()
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    for key, value in report['counts'].items():
        print(f'{key}: {value}')
    for row in report['higherMinimumPrerequisites']:
        relations = ' + '.join(row['relations'])
        print(f"{row['dungeon']}: {row['parentTitle']} ({row['parentMinLevel']}) -> "
              f"{row['title']} ({row['minLevel']}) [{relations}]")
    print('This checks recorded edges only; missing prerequisite links need source review.')


if __name__ == '__main__':
    main()
