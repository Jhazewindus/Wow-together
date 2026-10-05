"""Join cached public quest/entity facts and write an auditable zone catalogue.

All source access happens in the capture tools. This build performs no network
calls, does not execute downloaded scripts/SQL, and retains unknown fields.
"""
import argparse
import collections
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess

from lupa.lua51 import LuaRuntime
from import_warcraftdb import ROOT, apply_corrections, generate, normalize
from import_wowhead import base_facts, detail_facts, json_after, list_rows
from import_travel_network import encode
from quest_enrichment import enrich, entity_facts, mapper_entities, quest_relations
from legacy_quest_facts import COMMIT, SOURCE, calibrate, indexed, mapped_locations, matches, read_snapshot, requirements, world_locations


def plain(value):
    if hasattr(value,'items'):
        result={key:plain(item) for key,item in value.items()}
        if result and set(result)==set(range(1,len(result)+1)):
            return [result[i] for i in range(1,len(result)+1)]
        return result
    return value


def own_lua(path, field):
    lua=LuaRuntime(unpack_returned_tuples=True);ns=lua.table()
    lua.eval('function(text,ns) assert(loadstring(text))("WowTogether",ns) end')(path.read_text(),ns)
    return plain(ns[field])


def merge_entity(entities,kind,ident,value):
    target=entities[kind].setdefault(ident,{'name':value.get('name',''),'locations':[]})
    if not target['name']:target['name']=value.get('name','')
    for point in value.get('locations',[]):
        if point not in target['locations']:target['locations'].append(point)
    for key in ('sources','minlevel','maxlevel','classification','source'):
        if key in value:target[key]=value[key]


def forever_pois(path, entities):
    """Read only the reviewed data rows, never the source addon's engine."""
    metadata=json.loads((ROOT/'WowTogether/TravelData.json').read_text())
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=path.parents[2],text=True).strip()
    if commit!=metadata['commit']:raise ValueError('Forever NPC geography revision needs review')
    count=0
    for row in path.read_text().splitlines():
        point=re.search(r'\bmapID\s*=\s*(\d+),\s*x\s*=\s*([\d.]+),\s*y\s*=\s*([\d.]+)',row)
        if not point or 'npcs = {' not in row:continue
        map_id,x,y=int(point[1]),float(point[2]),float(point[3])
        if not 0<=x<=1 or not 0<=y<=1:raise ValueError('Invalid Forever NPC data coordinates')
        for ident in re.findall(r'\bid\s*=\s*(\d+)',row.split('npcs = {',1)[1]):
            entity=entities['npc'].setdefault(int(ident),{'name':'','locations':[]})
            # These source records contain IDs/coordinates, not names. A name
            # is joined only from a published quest or matched numeric source.
            location={'mapID':map_id,'x':x,'y':y,'geographySource':'Mapzeroth Forever 0.6.0 NPC facts (MIT)'}
            if location not in entity['locations']:entity['locations'].append(location);count+=1
    return {'commit':commit,'file_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'npc_locations':count,
        'source':metadata['source'],'license':'MIT'}


def build(args):
    # Rebuild from captured sources, never yesterday's generated fallback.
    # Removing a source or correcting a requirement must remove stale facts.
    records={}
    source_requirements={}
    previous=json.loads((ROOT/'WowTogether/QuestCatalogue.json').read_text())
    area_maps={int(k):v for k,v in previous['area_ui_maps'].items()}
    for file in sorted(args.warcraftdb_cache.glob('quest-*.json')):
        ident=int(file.stem.split('-')[1]);raw=json.loads(file.read_text());facts=normalize({'record_id':ident},raw)
        requirements_raw=[]
        for objective in raw.get('data',{}).get('objectives',[]):
            kind=objective.get('link_node');entity=objective.get('link_id');quantity=objective.get('amount')
            if kind in ('npc','object','item') and type(entity) is int and entity>0 and type(quantity) is int and quantity>0:
                ref={'entityType':kind,'entityID':entity,'name':objective.get('description',''),'quantity':quantity}
                if objective.get('type')==3:
                    ref['name']=re.sub(r'^Speak (?:with|to)\s+','',ref['name'])
                action={0:'kill',3:'talk',2:'interact',1:'collect'}.get(objective.get('type'))
                if action:ref['action']=action
                requirements_raw.append(ref)
        if requirements_raw:source_requirements[ident]=requirements_raw
        # Keep Forever list metadata and existing detailed facts authoritative.
        current=records.setdefault(ident,{})
        for key,value in facts.items():
            if key not in current or current[key] in ('',0):current[key]=value
    lists=[('',args.quest_cache/'index.html')]+[(zone,args.quest_cache/(zone.replace('/','-')+'.html'))
        for zone in previous['zones']]
    for zone,file in lists:
        if not file.exists():raise ValueError('Missing captured category list: '+str(file))
        try:rows=list_rows(file.read_text())
        except ValueError:continue
        if zone and len(rows)>=1000:raise ValueError('Truncated category list: '+zone)
        for row in rows:
            record=records.setdefault(row['id'],{})
            record.update(base_facts(row))
            if zone:record['categoryPath']=zone
    # Join exact normalized zone names to the already attributed Forever travel
    # map identifiers. Ambiguous names cannot assign a UI map to source areas.
    travel=own_lua(ROOT/'WowTogether/TravelData.lua','travelData')
    names=collections.defaultdict(set)
    norm=lambda s:re.sub('[^a-z0-9]','',s.lower())
    for node in travel['nodes'].values():
        container=node.get('container','').split('.')[-1]
        if container:names[norm(container)].add(node['mapID'])
    pages={int(p.stem.split('-')[1]):p.read_text() for p in args.quest_cache.glob('quest-*.html')}
    joins=previous.get('additional_map_joins',[])
    for ident,page in pages.items():
        mapper=json_after(page,'new Mapper(')
        for area,group in (mapper.get('objectives',{}) if isinstance(mapper,dict) else {}).items():
            maps=names.get(norm(group.get('zone','')),set())
            if len(maps)==1 and int(area) not in area_maps:
                area_maps[int(area)]=next(iter(maps));joins.append({'areaID':int(area),'mapID':next(iter(maps)),
                    'zone':group.get('zone'),'source':'Exact Forever travel container / published quest mapper zone name'})
    entities={kind:{} for kind in ('npc','object','item')}
    for file in sorted(args.entity_cache.glob('*.html')):
        kind,ident=file.stem.split('-');ident=int(ident)
        facts=entity_facts(file.read_text(),kind,ident);merge_entity(entities,kind,ident,facts)
        for loc in facts['locations']:
            if loc.get('sourceAreaID') and loc['sourceAreaID'] not in area_maps:
                area_maps[loc['sourceAreaID']]=loc['mapID']
    refs={ident:{'starts':[],'ends':[],'requirements':values} for ident,values in source_requirements.items()}
    for ident in source_requirements:records[ident]['requirementSource']='Warcraft DB Forever structured objectives'
    valid_pages=0
    for ident,page in sorted(pages.items()):
        row={'id':ident,'name':records.get(ident,{}).get('title','')}
        try:facts=detail_facts(page,row,area_maps,records)
        except ValueError:continue
        valid_pages+=1
        records.setdefault(ident,{}).update(facts)
        relation=quest_relations(page)
        if relation['requirements']:records[ident]['requirementSource']='Wowhead Forever objective table'
        if not relation['requirements']:
            relation['requirements']=source_requirements.get(ident,[])
        supplied={r['entityID'] for r in relation.get('provided',[])}
        relation['requirements']=[r for r in relation['requirements'] if not (r['entityType']=='item' and r['entityID'] in supplied)]
        refs[ident]=relation
        for kind,entity_id,value in mapper_entities(page,area_maps):merge_entity(entities,kind,entity_id,value)
    poi_source=forever_pois(args.forever_pois,entities) if args.forever_pois else {}
    # Attach canonical map/zone to sparse list records too, using this proven join.
    for record in records.values():
        if record.get('areaID') in area_maps and not record.get('mapID'):
            record['mapID']=area_maps[record['areaID']]
    for exclusion in json.loads((ROOT/'tools/quest_exclusions.json').read_text()):
        for ident in exclusion['questIDs']:
            if ident in records:records[ident]['levelingExcluded']=exclusion['reason']
    legacy_quests=[];transforms={};legacy_stats={}
    if args.legacy_snapshot:
        print('Reading pinned older-world facts (no SQL execution)...',flush=True)
        legacy=indexed(read_snapshot(args.legacy_snapshot))
        for ident,entity in entities['npc'].items():
            if not entity['name'] and ident in legacy['npc']:entity['name']=legacy['npc'][ident]['name']
        transforms=calibrate(entities,legacy)
        eligible={ident for ident,quest in records.items() if ident in legacy['quests'] and matches(quest,legacy['quests'][ident])}
        print(f'Identity-matched unchanged quests: {len(eligible)}; calibrated maps: {len(transforms)}',flush=True)
        referenced={kind:set() for kind in ('npc','object','item')}
        for ident in sorted(eligible):
            quest,source=records[ident],legacy['quests'][ident]
            relation=refs.setdefault(ident,{'starts':[],'ends':[],'requirements':[]})
            for role in ('starts','ends'):
                if not relation[role]:relation[role]=legacy[role].get(ident,[])
            if not relation['requirements']:
                relation['requirements']=requirements(source,legacy)
                quest['requirementSource']='Identity-matched unchanged quest: '+SOURCE
            if not relation['requirements'] and source['SpecialFlags'] & 2 and not quest.get('objectives'):
                # Event/escort credit has no numeric target. An end NPC is
                # not evidence of where the event must actually take place.
                quest['objectiveLocationsIncomplete']=True;quest['otherLocationsIncomplete']=True
            for requirement in relation['requirements']:
                old_req=next((r for r in requirements(source,legacy) if r['entityType']==requirement['entityType']
                    and r['entityID']==requirement['entityID'] and r['quantity']==requirement['quantity']),None)
                if old_req and old_req.get('action')=='use':
                    requirement.update({k:old_req[k] for k in ('action','useItemName','spellID') if k in old_req})
            for role in relation.values():
                for ref in role:referenced[ref['entityType']].add(ref['entityID'])
            # Explicit positive predecessor only; keep published/tester branches.
            parent=source['PrevQuestId']
            if parent>0 and parent in eligible and not any(quest.get(k) for k in
                    ('previousQuest','prerequisiteAny','prerequisiteCandidates','prerequisitesUnverified')):
                quest['previousQuest']=parent;quest['prerequisiteSource']='Identity-matched unchanged quest: '+SOURCE
            if source['SpecialFlags'] & 1:quest['repeatable']=True
            for old_key,key in (('RequiredClasses','classMask'),('RequiredRaces','raceMask')):
                if key not in quest:quest[key]=source[old_key]
            if not quest.get('prerequisitesRead'):
                quest['prerequisitesRead']=True
                if source['RequiredCondition'] or source['RequiredMinRepFaction'] or source['RequiredMaxRepFaction']:
                    quest['prerequisitesUnverified']=True
            quest['legacyFactsSource']=SOURCE;legacy_quests.append(ident)
            quest['worldReferences']=relation
        for ident in referenced['item']:
            item=legacy['item'].get(ident)
            if item:
                sources=legacy['drops'].get(ident,[])
                for ref in sources:referenced[ref['entityType']].add(ref['entityID'])
                if ident not in entities['item']:
                    entities['item'][ident]={'name':item['name'],'locations':[], 'sources':sources,
                        'source':'Older-world factual fallback: '+SOURCE}
        for kind in ('npc','object'):
            for ident in sorted(referenced[kind]):
                entity=legacy[kind].get(ident)
                if not entity:continue
                target=entities[kind].setdefault(ident,{'name':entity['name'],'locations':[]})
                target['worldLocations']=world_locations(entity)
                # Never replace published Forever positions with legacy spawns.
                if any(p.get('mapID') for p in target['locations']):continue
                points=mapped_locations(entity,transforms,transforms)
                value={'name':entity['name'],'locations':points,'source':'Older-world factual fallback: '+SOURCE}
                if kind=='npc':value.update(minlevel=entity['raw']['MinLevel'],maxlevel=entity['raw']['MaxLevel'])
                merge_entity(entities,kind,ident,value)
        legacy_stats={'source':SOURCE,'commit':COMMIT,'snapshot_sha256':hashlib.sha256(args.legacy_snapshot.read_bytes()).hexdigest(),
            'license':'GPL-3.0','identity_matched_unchanged_quests':len(eligible),
            'maps_calibrated_against_forever_npcs':transforms,'limitations':['Older-world fallbacks need current-beta testing',
            'No server/addon logic or quest prose included','World points are not terrain-safe road paths']}
        checks=[]
        for ident,entity in sorted(entities['npc'].items()):
            raw=legacy['npc'].get(ident,{})
            worlds=raw.get('worldLocations',[])
            if len(worlds)==1:
                continent,x,y=worlds[0]
                for point in entity.get('locations',[]):
                    if point.get('mapID') and not point.get('locationSource'):
                        checks.append(dict(point,continent=continent,worldX=x,worldY=y));break
        world_checks={continent: [p for p in checks if p['continent']==continent][:16] for continent in (0,1)}
    for ident,relation in refs.items():
        quest=records[ident]
        quest['startRefs'],quest['endRefs']=relation['starts'],relation['ends']
        # Clear stale generated enrichment on reproducible rebuilds.
        quest.pop('missingRequirements',None)
        for ref in relation['requirements']:
            if ref['entityType']=='item':
                items=quest.setdefault('requiredItems',[])
                if not any(i['itemID']==ref['entityID'] for i in items):
                    items.append({'itemID':ref['entityID'],'name':ref['name'],'quantity':ref['quantity']})
        enrich(quest,relation,entities)
    corrections=apply_corrections(records)
    code=generate(records,datetime.date.today().isoformat())
    code=code.replace('-- Generated by tools/import_warcraftdb.py;','-- Generated by tools/build_quest_dataset.py;')
    code=code.replace('    count =','    detailSource = "https://www.wowhead.com/forever/quests",\n    count =',1)
    runtime_entities={kind:{ident:{key:value for key,value in entity.items() if key not in ('locations','source')}
        for ident,entity in values.items()} for kind,values in entities.items()}
    for values in runtime_entities.values():
        for entity in values.values():
            if 'worldLocations' in entity:
                entity['worldLocations']=[[p['continent'],p['worldX'],p['worldY']] for p in entity['worldLocations']]
    code+='\n-- Named entity/drop facts; compact world points are decoded only when a guide needs them.\nns.questEntities = '+encode(runtime_entities)+'\n'
    if args.legacy_snapshot:
        code+='ns.worldQuestChecks = '+encode(world_checks)+'\n'
        literal=json.dumps(SOURCE)
        code=code.replace(literal,'legacyFactsSource')
        code=code.replace('local addonName, ns = ...\n','local addonName, ns = ...\nlocal legacyFactsSource = '+literal+'\n',1)
        code=code.replace('-- Generated by tools/build_quest_dataset.py;',
            '-- Factual dataset includes GPL-3.0 older-world adaptations; see THIRD_PARTY_NOTICES.md.\n-- Generated by tools/build_quest_dataset.py;',1)
    (ROOT/'WowTogether/QuestCatalogue.lua').write_text(code)
    summary=dict(previous,captured=datetime.date.today().isoformat(),count=len(records),detailed_quests=valid_pages,
        with_starters=sum(bool(q.get('starts')) for q in records.values()),with_objectives=sum(bool(q.get('objectives')) for q in records.values()),
        with_turnins=sum(bool(q.get('ends')) for q in records.values()),with_series=sum(bool(q.get('series')) for q in records.values()),
        with_prerequisites=sum(bool(q.get('previousQuest') or q.get('prerequisiteAny')) for q in records.values()),
        incomplete_objective_locations=sum(bool(q.get('objectiveLocationsIncomplete')) for q in records.values()),
        repeatable_quests=sum(q.get('repeatable') is True for q in records.values()),area_ui_maps=area_maps,
        entities={k:len(v) for k,v in entities.items()},additional_map_joins=joins,legacy_fallback=legacy_stats,
        forever_npc_geography=poi_source,tester_corrections=corrections)
    (ROOT/'WowTogether/QuestCatalogue.json').write_text(json.dumps(summary,indent=2)+'\n')
    coverage=collections.defaultdict(lambda: {'quests':0,'pickups':0,'objectives':0,'turnins':0,'complete_locations':0,'missing_quest_ids':[]})
    for ident,quest in sorted(records.items()):
        zone=quest.get('categoryPath') or quest.get('zone') or 'Unknown category'
        if zone=='uncategorized' and quest.get('mapID'):
            zone='map:'+str(quest['mapID'])+' / '+(quest.get('zone') or 'Published zone '+str(quest['areaID']))
        row=coverage[zone];row['quests']+=1
        for field,target in (('starts','pickups'),('objectives','objectives'),('ends','turnins')):
            if quest.get(field):row[target]+=1
        complete=bool(quest.get('starts') and quest.get('ends') and quest.get('prerequisitesRead')
            and not quest.get('objectiveLocationsIncomplete') and (quest.get('objectives') or not quest.get('requirements')))
        if complete:row['complete_locations']+=1
        else:row['missing_quest_ids'].append(ident)
    report={'captured':summary['captured'],'sources':['https://forever.warcraftdb.com','https://www.wowhead.com/forever',SOURCE],
        'summary':{k:summary[k] for k in ('count','detailed_quests','with_starters','with_objectives','with_turnins','with_prerequisites','entities')},
        'zones':dict(sorted(coverage.items())),'unavailable_details':previous.get('unavailable_details',[]),
        'entity_capture':json.loads((args.entity_cache/'capture.json').read_text()) if (args.entity_cache/'capture.json').exists() else {},
        'legacy_fallback':legacy_stats}
    (ROOT/'WowTogether/QuestCoverage.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['summary'],indent=2),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--quest-cache',type=Path,default=Path('/tmp/wow-together-wowhead'))
    parser.add_argument('--warcraftdb-cache',type=Path,default=Path('/tmp/wow-together-warcraftdb'))
    parser.add_argument('--entity-cache',type=Path,default=Path('/tmp/wow-together-wowhead-entities'))
    parser.add_argument('--legacy-snapshot',type=Path)
    parser.add_argument('--forever-pois',type=Path,help='Reviewed MIT Forever NPC data rows, used only as geographic facts.')
    build(parser.parse_args())


if __name__=='__main__':main()
