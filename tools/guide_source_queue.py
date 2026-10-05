"""Write exact remaining guide-source needs; this performs no network requests."""
import collections
import json
from pathlib import Path

from build_quest_dataset import own_lua


ROOT=Path(__file__).resolve().parents[1]


def queue(audit,quests):
    needs=collections.defaultdict(lambda:{'guides':set(),'needs':set()})
    for guide in audit['guides']:
        name=guide['faction']+' / '+guide['zone']
        for stage,ids in guide['missing_location_quest_ids_by_stage'].items():
            for ident in ids:needs[ident]['guides'].add(name);needs[ident]['needs'].add({'a':'pickup','q':'objective area','t':'hand-in'}[stage])
        for field,label in (('unverified_pickup_requirement_quest_ids','pickup requirements'),
            ('unverified_objective_quantity_quest_ids','objective quantities')):
            for ident in guide.get(field,[]):needs[ident]['guides'].add(name);needs[ident]['needs'].add(label)
    rows=[]
    for ident,need in sorted(needs.items()):
        quest=quests[ident];entities=set()
        for role in ('startRefs','endRefs','missingRequirements'):
            for ref in quest.get(role,[]):entities.add((ref['entityType'],ref['entityID']))
        rows.append({'questID':ident,'title':quest['title'],'guides':sorted(need['guides']),'needs':sorted(need['needs']),
            'quest_url':'https://www.wowhead.com/forever/quest='+str(ident),
            'entity_urls':['https://www.wowhead.com/forever/'+kind+'='+str(entity) for kind,entity in sorted(entities)]})
    return {'source_data_complete':False if rows else True,'remaining_quest_records':len(rows),
        'limitations':['This queue identifies missing facts, not a license to invent them',
            'Source capture must respect access policy and stop after denials',
            'Even an empty queue does not certify live beta behavior or walkable terrain'], 'quests':rows}


def main():
    result=queue(json.loads((ROOT/'WowTogether/GuideAudit.json').read_text()),
        own_lua(ROOT/'WowTogether/QuestCatalogue.lua','catalogue')['quests'])
    (ROOT/'WowTogether/GuideSourceQueue.json').write_text(json.dumps(result,indent=2)+'\n')
    print(str(result['remaining_quest_records'])+' quest records still need source facts.')


if __name__=='__main__':main()
