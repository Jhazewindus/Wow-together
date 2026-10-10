"""Add missing structured facts from captured Forever quest pages without rebuilding older sources.

No network access or downloaded code execution. Existing coordinates, reviewed
requirements and prerequisite/identity rules take precedence over supplements.
"""
import argparse
import collections
import copy
import datetime
import hashlib
import json
from pathlib import Path

from build_quest_dataset import own_lua
from import_wowhead import detail_facts
from pack_data import quest_code
from quest_enrichment import enrich, mapper_entities, quest_relations
from import_warcraftdb import apply_corrections, apply_stage_corrections

ROLES = ('starts', 'ends', 'objectives')

def supplement(quest, detail, refs, entities):
    result = copy.deepcopy(quest)
    for role in ROLES:
        if not result.get(role) and detail.get(role):
            result[role] = copy.deepcopy(detail[role])
    for key in ('startRefs', 'endRefs', 'requiredItems', 'providedItems', 'npcTargets', 'objectiveAlternatives'):
        value = detail.get(key)
        if not result.get(key) and value:
            result[key] = copy.deepcopy(value)
    for role, key in (('starts', 'startRefs'), ('ends', 'endRefs')):
        if not result.get(key) and refs.get(role): result[key] = copy.deepcopy(refs[role])
    # An existing requirement can contain reviewed item-use/escort/alternative
    # semantics. Never replace it with a less specific new page table.
    selected = copy.deepcopy(refs)
    if result.get('requirements'): selected['requirements'] = copy.deepcopy(result['requirements'])
    if selected.get('requirements'):
        result.pop('missingRequirements', None)
        enrich(result, selected, entities)
    # Enrichment may prefer another named drop source. A supplement cannot
    # displace an existing reviewed point or change its action; only add fields
    # it lacks and append independently matched missing requirements.
    for role in ROLES:
        for index, point in enumerate(quest.get(role) or []):
            result[role][index].update(copy.deepcopy(point))
    if not result.get('requirements') and refs.get('requirements'):
        result['requirements'] = copy.deepcopy(refs['requirements'])
    # Source tables can be partial: neither an empty table nor a supplement
    # clears an existing unknown-objective/branch gate by itself.
    if quest.get('objectiveLocationsIncomplete') and not selected.get('requirements'):
        result['objectiveLocationsIncomplete'] = True
    return result


def capture_history(previous, history):
    """Retain the prior hashed evidence report when a newer batch is captured."""
    result = copy.deepcopy(history or [])
    if previous and previous not in result:
        result.append(copy.deepcopy(previous))
    return result


def build(directory, cache, output):
    source=directory/'QuestCatalogue.lua'
    catalogue=own_lua(source, 'catalogue')
    entities=own_lua(source, 'questEntities')
    checks=own_lua(source, 'worldQuestChecks');xp=own_lua(source, 'xpBaseline')
    metadata=json.loads((directory/'QuestCatalogue.json').read_text())
    maps={int(k):v for k,v in metadata['area_ui_maps'].items()}
    records=catalogue['quests']; before_records=copy.deepcopy(records); parsed=[]; geography={'npc':{},'object':{},'item':{}}
    evidence={};invalid=[]
    for file in sorted(cache.glob('quest-*.html')):
        ident=int(file.stem.split('-')[1]);quest=records.get(ident)
        if not quest:continue
        page=file.read_text()
        try:detail=detail_facts(page,dict(quest,id=ident),maps,records)
        except ValueError:invalid.append(ident);continue
        if detail['title']!=quest['title']:invalid.append(ident);continue
        refs=quest_relations(page);parsed.append((ident,detail,refs))
        evidence[str(ident)]={'source':f'https://www.wowhead.com/forever/quest={ident}',
            'sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
        for kind,entity,value in mapper_entities(page,maps):
            target=geography[kind].setdefault(entity,{'name':value['name'],'locations':[]})
            for point in value['locations']:
                if point not in target['locations']:target['locations'].append(point)
    changed=[]; added=collections.Counter(); old=sum(bool(q.get('objectiveLocationsIncomplete')) for q in records.values())
    for ident,detail,refs in parsed:
        quest=records[ident];result=supplement(quest,detail,refs,geography)
        if result!=quest:
            changed.append(ident)
            for role in ROLES:added[role]+=max(0,len(result.get(role) or [])-len(quest.get(role) or []))
            records[ident]=result
    # Names/short reference facts only; geography is compiled into quest points
    # and is not kept as another resident spawn database in the client.
    for kind,rows in geography.items():
        for ident,value in rows.items():
            target=entities[kind].get(ident)
            if target and not target.get('name') and value['name']:target['name']=value['name']
    corrections=apply_corrections(records)
    stage_corrections=apply_stage_corrections(records)
    changed=sorted(ident for ident,quest in records.items() if quest!=before_records[ident])
    added=collections.Counter()
    for ident in changed:
        for role in ROLES:
            added[role]+=max(0,len(records[ident].get(role) or [])-len(before_records[ident].get(role) or []))
    now=datetime.date.today().isoformat()
    report={'captured':now,'pages':len(parsed),'changed_quest_ids':changed,'added_points':dict(added),
        'invalid_quest_ids':invalid,'incomplete_objectives_before':old,
        'incomplete_objectives_after':sum(bool(q.get('objectiveLocationsIncomplete')) for q in records.values()),'evidence':evidence}
    report['reviewed_stage_corrections']=stage_corrections
    report['reviewed_quest_corrections']=corrections
    catalogue['captured']=now;output.mkdir(parents=True,exist_ok=True)
    (output/'QuestCatalogue.lua').write_text(quest_code(catalogue,entities,checks,xp))
    for key,role in [('with_starters','starts'),('with_objectives','objectives'),('with_turnins','ends')]:metadata[key]=sum(bool(q.get(role)) for q in records.values())
    metadata_history=capture_history(metadata.get('supplemental_capture'),
                                     metadata.get('supplemental_capture_history'))
    if metadata_history:
        metadata['supplemental_capture_history']=metadata_history
    metadata['captured']=now;metadata['incomplete_objective_locations']=report['incomplete_objectives_after']
    metadata['supplemental_capture']={key:value for key,value in report.items() if key!='evidence'}
    (output/'QuestCatalogue.json').write_text(json.dumps(metadata,indent=2)+'\n')
    coverage=json.loads((directory/'QuestCoverage.json').read_text())
    previous_capture=coverage.get('supplemental_capture')
    prior_history=coverage.get('supplemental_capture_history')
    if prior_history is None:
        prior_history=metadata.get('supplemental_capture_history', [])
    history=capture_history(previous_capture, prior_history)
    if history:
        coverage['supplemental_capture_history']=history
    coverage['captured']=now
    for key in ['with_starters','with_objectives','with_turnins']:coverage['summary'][key]=metadata[key]
    zones=collections.defaultdict(lambda:{'quests':0,'pickups':0,'objectives':0,'turnins':0,'complete_locations':0,'missing_quest_ids':[]})
    for ident,q in sorted(records.items()):
        zone=q.get('categoryPath') or q.get('zone') or 'Unknown category'
        if zone=='uncategorized' and q.get('mapID'):zone='map:'+str(q['mapID'])+' / '+(q.get('zone') or 'Published zone '+str(q['areaID']))
        row=zones[zone];row['quests']+=1
        for role,key in [('starts','pickups'),('objectives','objectives'),('ends','turnins')]:row[key]+=bool(q.get(role))
        complete=bool(q.get('starts') and q.get('ends') and q.get('prerequisitesRead') and not q.get('objectiveLocationsIncomplete') and (q.get('objectives') or not q.get('requirements')))
        if complete:row['complete_locations']+=1
        else:row['missing_quest_ids'].append(ident)
    coverage['zones']=dict(sorted(zones.items()));coverage['supplemental_capture']=report
    (output/'QuestCoverage.json').write_text(json.dumps(coverage,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='evidence'},indent=2))
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,default=Path(__file__).resolve().parents[1]/'WowTogether')
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();build(args.directory,args.cache,args.output)

if __name__=='__main__':main()
