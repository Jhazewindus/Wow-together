"""Select public Forever quest/entity facts without evaluating source providers.

Source UI, routing/availability algorithms, code and quest prose are excluded.
Only whitelisted literal fields and integer sums of named mask constants are
accepted. Dynamic providers and unknown expressions are left unresolved.
"""
import collections
import hashlib
import json
import math
from pathlib import Path
import re

from lua_data_literal import LiteralParser
from quest_enrichment import representative_coords, choose_location
from import_warcraftdb import clean


MANIFEST = Path(__file__).with_name('forever_source_manifest.json')
KIND_NAMES = {'quest':'Quest', 'npc':'Npc', 'object':'Object', 'item':'Item'}
FIELDS = {
    'quest': {'name','startedBy','finishedBy','requiredLevel','questLevel','requiredRaces','requiredClasses',
        'objectives','objectivesText','sourceItemId','preQuestGroup','preQuestSingle','zoneOrSort','requiredSkill',
        'triggerEnd','requiredSourceItems','questFlags','specialFlags','requiredMaxLevel','exclusiveTo',
        'availableUntilCompleted','availableStartingWith','parentQuest','requiredMinRep','requiredMaxRep'},
    'npc': {'name','minLevel','maxLevel','rank','spawns','waypoints','zoneID','questStarts','questEnds'},
    'object': {'name','spawns','zoneID','questStarts','questEnds'},
    'item': {'name','npcDrops','objectDrops','itemDrops','vendors','startQuest'},
}


def numeric_symbols(text, prefix):
    return {prefix+'.'+name:int(value) for name,value in re.findall(r'^\s+([A-Z][A-Z_0-9]*)\s*=\s*(-?\d+)\s*,', text, re.M)}


def symbols_from(texts):
    result = numeric_symbols(texts['src/corrections/enum/zones.lua'], 'zoneIDs')
    sorts = texts['src/corrections/enum/quests.lua'].split('sortKeys =', 1)[1].split('\n}', 1)[0]
    result.update(numeric_symbols(sorts, 'sortKeys'))
    for prefix in ('specialFlags','questFlags'):
        block = texts['src/corrections/enum/quests.lua'].split(prefix+' =',1)[1].split('\n}',1)[0]
        result.update(numeric_symbols(block,prefix))
    # These are mask encodings documented in the pinned Forever enum file;
    # neither game type nor race ID alone selects an API compatibility path.
    races = {'HUMAN':1, 'ORC':2, 'DWARF':4, 'NIGHT_ELF':8, 'UNDEAD':16,
        'TAUREN':32, 'GNOME':64, 'TROLL':128, 'GOBLIN':256,
        'SKYBORNE_ALLIANCE':4294967296, 'SKYBORNE_HORDE':8589934592,
        'ALL_ALLIANCE':4294967373, 'ALL_HORDE':8589934770, 'NONE':0}
    result.update({'raceIDs.'+name:value for name,value in races.items()})
    classes = {'WARRIOR':1,'PALADIN':2,'HUNTER':4,'ROGUE':8,'PRIEST':16,'SHAMAN':64,
        'MAGE':128,'WARLOCK':256,'DRUID':1024,'ALL_CLASSES':1503,'NONE':0}
    result.update({'classIDs.'+name:value for name,value in classes.items()})
    for name in ('EVENT','INTERACT','TALK','SLAY','LOOT'):
        result['Questie.ICON_TYPE_'+name] = 'action:'+name.lower()
    return result


def read_value(text, start, symbols):
    parser = LiteralParser(text, symbols); parser.pos = start
    value = parser.value(); parser.space()
    while parser.pos < len(text) and text[parser.pos] == '+':
        if type(value) is not int: raise ValueError('Only integer mask sums are supported')
        parser.pos += 1; other = parser.value()
        if type(other) is not int: raise ValueError('Only integer mask sums are supported')
        value += other; parser.space()
    if parser.pos < len(text) and text[parser.pos] not in ',}':
        raise ValueError('Nonliteral field expression')
    return value


def static_fields(text, kind, symbols):
    # Only the static Load body is examined. Never invoke it or interpret a
    # LoadDynamic body whose values depend on class/faction/phase at runtime.
    match = re.search(r'^function [^\n]+:Load\(\)\s*$', text, re.M)
    if not match: raise ValueError('Unrecognized factual provider boundary')
    body = text[match.end():]
    end = re.search(r'^end\s*$', body, re.M)
    if not end: raise ValueError('Missing factual provider boundary')
    body = body[:end.start()]
    rows, skipped, assumptions = {}, [], []
    entries = list(re.finditer(r'^        \[(\d+)\]\s*=\s*\{([^\n]*)', body, re.M))
    for i, entry in enumerate(entries):
        ident = int(entry[1])
        if not 0 < ident < 2147483647: raise ValueError('Invalid factual entity ID')
        chunk = body[entry.end():entries[i+1].start() if i+1<len(entries) else len(body)]
        row = rows.setdefault(ident, {})
        # An entry heading may carry a short entity identity, never quest prose.
        heading = entry[2].strip()
        name = re.match(r'--\s*(.*?)\s*(?::\s*https://|$)', heading)
        if name and name[1]: row['_identityName'] = name[1].strip()
        for field in re.finditer(r'^            \['+kind+r'Keys\.([A-Za-z_0-9]+)\]\s*=\s*', chunk, re.M):
            key = field[1]; base = re.sub(r'_(?:add|remove)$','',key)
            if base not in FIELDS[kind]: continue
            line = chunk[field.end():].split('\n',1)[0]
            if 'Assumption:' in line:
                assumptions.append([kind,ident,key]); continue
            try: row[key] = read_value(chunk, field.end(), symbols)
            except ValueError: skipped.append([kind,ident,key])
    return rows, skipped, assumptions


def base_fields(text, kind):
    """Read numeric rows from the published converted baseline as literals."""
    key_block = text.split('QuestieDB.'+kind+'Keys =', 1)[1].split('\n}', 1)[0]
    keys = {int(index):name for name,index in re.findall(r"^    \['([A-Za-z0-9_]+)'\]\s*=\s*(\d+)",key_block,re.M)
        if name in FIELDS[kind]}
    body = text.split('[[return {', 1)[1].rsplit('}]]', 1)[0]
    rows = {}
    for match in re.finditer(r'^\[(\d+)\]\s*=\s*',body,re.M):
        values = read_value(body,match.end(),{})
        rows[int(match[1])] = {keys[index]:value for index,value in values.items()
            if index in keys and value is not None}
    return rows


def sequence(value):
    return [v for _,v in sorted(value.items()) if v is not None] if isinstance(value,dict) else []


def union(old, values, remove=False):
    current=sequence(old); incoming=sequence(values)
    if remove: current=[v for v in current if v not in incoming]
    else:
        for v in incoming:
            if v not in current: current.append(v)
    return {i+1:v for i,v in enumerate(current)}


def apply_fields(target, incoming):
    for key, value in incoming.items():
        mode='add' if key.endswith('_add') else 'remove' if key.endswith('_remove') else 'set'
        base=re.sub(r'_(?:add|remove)$','',key)
        if mode=='set': target[base]=value
        elif base in ('spawns','waypoints','startedBy','finishedBy','objectives'):
            groups=target.setdefault(base,{})
            if not isinstance(groups,dict) or not isinstance(value,dict): continue
            for group, entries in value.items():
                if entries is not None: groups[group]=union(groups.get(group),entries,mode=='remove')
        else: target[base]=union(target.get(base),value,mode=='remove')


def read_beta_facts(root):
    manifest=json.loads(MANIFEST.read_text()); texts={}
    for name,checksum in manifest['files_sha256'].items():
        file=root/name
        if hashlib.sha256(file.read_bytes()).hexdigest()!=checksum: raise ValueError('Forever source needs review: '+name)
        texts[name]=file.read_text()
    symbols=symbols_from(texts)
    data={kind:{} for kind in KIND_NAMES}; origins={kind:{} for kind in KIND_NAMES}; skipped=[]; assumptions=[]
    for kind,cap in KIND_NAMES.items():
        base = 'data/Forever/forever'+cap+'DB.lua'
        data[kind] = base_fields(texts[base],kind)
        for ident,row in data[kind].items(): origins[kind][ident]={key:'converted-baseline' for key in row}
        files=['src/corrections/Forever/legacy/classic'+('NPC' if kind=='npc' else cap)+'Fixes.lua',
            'src/corrections/Forever/generated/foreverBase'+cap+'.lua',
            'src/corrections/Forever/traces/forever'+cap+'Traces.lua',
            'src/corrections/Forever/forever'+('NPC' if kind=='npc' else cap)+'Fixes.lua']
        for name in files:
            rows, missing, guessed=static_fields(texts[name],kind,symbols)
            skipped.extend(missing); assumptions.extend(guessed)
            for ident, row in rows.items():
                apply_fields(data[kind].setdefault(ident,{}),row)
                source = 'converted-baseline' if '/legacy/' in name else 'beta-delta' if '/generated/' in name else 'beta-observation' if '/traces/' in name else 'beta-reviewed'
                origin = origins[kind].setdefault(ident,{})
                for key in row: origin[re.sub(r'_(?:add|remove)$','',key)] = source
    mapping_text=texts['support/Forever/Zones/areaIdToUiMapId.lua']
    # The default native mappings follow the separately documented legacy
    # overrides. Dungeon aliases and synthetic views are not copied.
    mapping_text=mapping_text.split('ZoneDB.private.areaIdToUiMapId =',1)[1]
    maps={int(area):int(map_id) for area,map_id in re.findall(r'^\s+\[(\d+)\]\s*=\s*(\d+)\s*,',mapping_text,re.M)
        if int(map_id)>0 and (int(area)<10000 or int(area)>=16000)}
    provenance={'source':manifest['source'],'commit':manifest['commit'],'files_sha256':manifest['files_sha256'],
        'parsed_records':{kind:len(rows) for kind,rows in data.items()},'skipped_nonliteral_fields':skipped,
        'withheld_assumption_fields':assumptions,'limitations':['Static factual fields only; dynamic provider code is never executed',
            'Observations and published data still require current-beta verification','No quest prose or source engine/UI is bundled']}
    return data,maps,provenance,origins


RACE_BITS = {1:1, 2:2, 3:4, 4:8, 5:16, 6:32, 7:64, 8:128, 9:256, 95:4294967296, 96:8589934592}
ALLIANCE = 4294967373
HORDE = 8589934770


def ids(value):
    return [i for i in sequence(value) if type(i) is int and 0 < i < 2147483647]


def patrol_paths(value):
    """Only explicit ordered waypoint lists; spawns never imply movement."""
    values = sequence(value)
    if not values: return []
    def pair(item):
        return isinstance(item, dict) and set(item) == {1, 2} and all(
            type(item[i]) in (int, float) and math.isfinite(item[i]) and 0 <= item[i] <= 100 for i in (1, 2))
    if all(pair(item) for item in values):
        return [[sequence(item) for item in values]] if 2 <= len(values) <= 2048 else []
    result = []
    for route in values[:16]:
        points = sequence(route)
        if 2 <= len(points) <= 2048 and all(pair(item) for item in points):
            result.append([sequence(item) for item in points])
    return result


def entity_name(kind, ident, data):
    row = data.get(kind, {}).get(ident, {})
    return clean(row.get('name') or row.get('_identityName') or '')


def relations(value, data):
    result = []
    for slot,kind in ((1,'npc'), (2,'object'), (3,'item')):
        for ident in ids((value or {}).get(slot)):
            result.append({'entityType':kind, 'entityID':ident, 'name':entity_name(kind,ident,data)})
    return result


def objective_facts(row, data):
    """Typed IDs and explicit counts only; the source's prose stays transient."""
    result = []
    for slot,kind,default in ((1,'npc','kill'), (2,'object','interact'), (3,'item','collect')):
        for value in sequence((row.get('objectives') or {}).get(slot)):
            if not isinstance(value,dict) or type(value.get(1)) is not int: continue
            ident = value[1]; name = entity_name(kind,ident,data)
            if kind=='item' and ident==row.get('sourceItemId'): continue
            action = value.get(3, '').replace('action:', '') if isinstance(value.get(3),str) else default
            label = value.get(2)
            if action==default and isinstance(label,str) and kind=='npc':
                if re.search(r'\b(?:spoken to|speak|talk|listen)\b',label,re.I): action='talk'
                elif not re.search(r'\b(?:slain|killed)\b',label,re.I): action='event'
            action = {'slay':'kill', 'loot':'collect'}.get(action,action)
            if action not in ('kill','interact','talk','collect','event'): action = default
            ref = {'entityType':kind, 'entityID':ident, 'name':name, 'action':action, 'quantityUnknown':True}
            # Match only exact named targets with an explicit numeric amount.
            # A vague "bring me supplies" sentence cannot invent a count.
            counts = set()
            for goal in sequence(row.get('objectivesText')):
                if not isinstance(goal,str) or not name: continue
                target = re.escape(name)+r'(?:s|es)?\b'
                for count in re.findall(r'\b(\d+)\s+(?:\w+\s+)?'+target,goal,re.I):
                    if 0 < int(count) <= 10000: counts.add(int(count))
            if len(counts)==1:
                ref['quantity'] = counts.pop(); ref.pop('quantityUnknown')
            result.append(ref)
    credits = sequence((row.get('objectives') or {}).get(5))
    for value in credits:
        if not isinstance(value,dict): continue
        alternatives = ids(value.get(1)); ident = value.get(2)
        if type(ident) is not int or ident<=0 or not alternatives: continue
        icon = value.get(4)
        action = icon.replace('action:','') if isinstance(icon,str) else 'kill'
        action = {'slay':'kill','loot':'collect'}.get(action,action)
        if action not in ('kill','talk','interact','event'): action='event'
        ref = {'entityType':'npc','entityID':ident,'name':entity_name('npc',ident,data),
            'action':action,'alternativeEntityIDs':alternatives,'quantityUnknown':True}
        goals = ' '.join(g for g in sequence(row.get('objectivesText')) if isinstance(g,str))
        amounts = {int(n) for n in re.findall(r'\b(\d+)\b',goals) if 0<int(n)<=10000}
        if len(credits)==1 and len(amounts)==1:
            ref['quantity']=amounts.pop(); ref.pop('quantityUnknown')
        result.append(ref)
    return result


def event_point(row, quest, data, area_maps, basis):
    trigger = row.get('triggerEnd')
    if not isinstance(trigger,dict) or not isinstance(trigger.get(2),dict): return
    points = []
    for area,coords in trigger[2].items():
        if area not in area_maps: continue
        for pair in representative_coords([sequence(p) for p in sequence(coords)]):
            points.append({'mapID':area_maps[area],'x':pair[0]/100,'y':pair[1]/100,'entityID':0,
                'name':quest['title'],'action':'event','locationSource':'Published Forever '+basis+' event area'})
    chosen = choose_location(points,quest)
    if not chosen: return
    chosen.pop('entityID')
    goal = ' '.join(v for v in sequence(row.get('objectivesText')) if isinstance(v,str))
    item = entity_name('item',row.get('sourceItemId'),data)
    if item and re.search(r'\bUse\s+(?:the\s+)?'+re.escape(item)+r'\b',goal,re.I):
        chosen.update(action='use',sourceAction='use-at',useItemName=item)
    elif re.search(r'\bEscort\b',goal,re.I):
        chosen['action']='escort'
        starts = relations(row.get('startedBy'),data)
        if starts and starts[0]['entityType']=='npc': chosen['name']=starts[0]['name']
    return chosen


def merge_beta_facts(records, refs, entities, area_maps, root):
    data, native_maps, provenance, origins = read_beta_facts(root)
    for area,map_id in native_maps.items():
        if area in area_maps and area_maps[area] != map_id:
            raise ValueError('Native area/map identity conflicts with captured data: '+str(area))
        area_maps[area] = map_id
    provenance.update(quests_used=[], identity_conflicts=[], withheld_fields=[], location_points=0,corrected_objective_quest_ids=[], patrol_routes=0)
    # Entity records are facts, not quest eligibility. Converted baseline
    # positions remain explicitly distinguishable from new beta observations.
    for kind in ('npc','object','item'):
        for ident,row in data[kind].items():
            value = entities[kind].setdefault(ident,{'name':'','locations':[]})
            if not value['name']: value['name'] = entity_name(kind,ident,data)
            source = origins[kind].get(ident,{})
            if kind != 'item':
                for area,coords in (row.get('spawns') or {}).items():
                    if area not in area_maps or not isinstance(coords,dict): continue
                    basis = source.get('spawns','converted-baseline')
                    for pair in representative_coords([sequence(p) for p in sequence(coords)]):
                        point = {'mapID':area_maps[area], 'x':pair[0]/100, 'y':pair[1]/100,
                            'sourceAreaID':area, 'locationSource':'Published Forever '+basis+' entity position'}
                        if point not in value['locations']: value['locations'].append(point); provenance['location_points']+=1
                for key,output in (('minLevel','minlevel'),('maxLevel','maxlevel'),('rank','classification')):
                    if type(row.get(key)) is int: value.setdefault(output,row[key])
                if kind == 'npc':
                    basis = source.get('waypoints', 'converted-baseline')
                    for area, routes in (row.get('waypoints') or {}).items():
                        if area not in area_maps or basis == 'converted-baseline' and area in (44, 139, 215, 1519): continue
                        for points in patrol_paths(routes):
                            patrol = {'mapID':area_maps[area], 'points':[[x/100,y/100] for x,y in points],
                                'source':'Published Forever '+basis+' patrol waypoints'}
                            value.setdefault('patrols', []).append(patrol)
                            provenance['patrol_routes'] += 1
                            if not any(p.get('mapID') == patrol['mapID'] for p in value['locations']):
                                x,y = patrol['points'][0]
                                value['locations'].append({'mapID':patrol['mapID'],'x':x,'y':y,
                                    'sourceAreaID':area,'patrol':True,'locationSource':patrol['source']})
            else:
                sources = value.setdefault('sources',[])
                for field,source_kind,action in (('npcDrops','npc','loot'),('objectDrops','object','gather'),('vendors','npc','buy')):
                    for target in ids(row.get(field)):
                        point = {'entityType':source_kind, 'entityID':target, 'name':entity_name(source_kind,target,data),'action':action}
                        if not any(p['entityID']==target and p['entityType']==source_kind and p.get('action')==action for p in sources): sources.append(point)
                if sources: value['source'] = 'Published Forever item-source facts'
    categories = {q.get('areaID'):q.get('categoryPath') for q in records.values() if q.get('areaID') and q.get('categoryPath') not in (None,'uncategorized')}
    inverse = collections.defaultdict(lambda:{'starts':[], 'ends':[]})
    for kind in ('npc','object'):
        for ident,row in data[kind].items():
            for field,role in (('questStarts','starts'),('questEnds','ends')):
                for quest_id in ids(row.get(field)):
                    ref = {'entityType':kind,'entityID':ident,'name':entity_name(kind,ident,data),
                        '_basis':origins[kind].get(ident,{}).get(field,'converted-baseline')}
                    inverse[quest_id][role].append(ref)
    for ident,row in data['item'].items():
        quest_id=row.get('startQuest')
        if type(quest_id) is int and quest_id>0:
            inverse[quest_id]['starts'].append({'entityType':'item','entityID':ident,'name':entity_name('item',ident,data),
                '_basis':origins['item'].get(ident,{}).get('startQuest','converted-baseline')})
    for ident,row in sorted(data['quest'].items()):
        source = origins['quest'].get(ident,{})
        title = clean(row.get('name') or row.get('_identityName') or '')
        quest = records.get(ident)
        # Never select deleted/unknown baseline quests just because their IDs
        # are in another database. New selections require explicit beta cores.
        if quest is None:
            if source.get('name','converted-baseline')=='converted-baseline' or not title \
                or type(row.get('requiredLevel')) is not int or type(row.get('questLevel')) is not int: continue
            quest = records[ident] = {'title':title,'level':row['questLevel'],'minLevel':row['requiredLevel'],'foreverStatus':'new'}
        if title and title != quest['title']:
            provenance['identity_conflicts'].append(ident); continue
        exact = bool(title and row.get('requiredLevel')==quest.get('minLevel') and row.get('questLevel')==quest.get('level'))
        relation = refs.setdefault(ident,{'starts':[],'ends':[],'requirements':[]})
        used = False
        for field,role in (('startedBy','starts'),('finishedBy','ends')):
            if exact or source.get(field,'converted-baseline')!='converted-baseline':
                values = relations(row.get(field),data) or inverse[ident][role]
                if not relation[role] and values:
                    relation[role]=[{k:v for k,v in r.items() if k!='_basis'} for r in values]; used=True
        explicit_objectives = source.get('objectives','converted-baseline')!='converted-baseline'
        if explicit_objectives or not relation['requirements'] and exact:
            values = objective_facts(row,data)
            old = {(p['entityType'],p['entityID']):p for p in relation['requirements']}
            for ref in values:
                primary = old.get((ref['entityType'],ref['entityID']),{})
                if primary.get('quantity') and not ref.get('alternativeEntityIDs'):
                    ref['quantity']=primary['quantity']; ref.pop('quantityUnknown',None)
                if ref.get('alternativeEntityIDs'):
                    goal=' '.join(g for g in sequence(row.get('objectivesText')) if isinstance(g,str))
                    healing=re.search(r'\bheal\s+(\d+)\s+([a-z ]+?)(?:\s+and\b|[.,]|$)',goal,re.I)
                    if ref['action']=='interact' and healing and int(healing[1])==ref.get('quantity'):
                        label=clean(healing[2]).capitalize()
                        ref.update(action='heal',objectiveLabel=label)
                        credit=next((p for p in old.values() if p.get('quantity')==ref['quantity']
                            and re.search(r'\bhealed\b',p.get('name',''),re.I)),None)
                        if credit:ref['progressName']=credit['name']
            if values or explicit_objectives:
                relation['requirements']=values; used=True; quest['requirementSource']='Published Forever typed objectives'
                if explicit_objectives:
                    quest['objectives']=[]; quest.pop('missingRequirements',None)
                    quest.pop('objectiveLocationsIncomplete',None)
                    provenance['corrected_objective_quest_ids'].append(ident)
            if (row.get('objectives') or {}).get(6) or (row.get('objectives') or {}).get(4):
                # Reputation/spell credit is not a physical NPC requirement.
                quest['objectiveLocationsIncomplete']=True
                quest['unmodeledObjectiveKinds']=True
        provided = row.get('sourceItemId')
        if provided and (exact or source.get('sourceItemId','converted-baseline')!='converted-baseline'):
            original=relation['requirements']
            relation['requirements']=[r for r in relation['requirements'] if not (r['entityType']=='item' and r['entityID']==provided)]
            if original and not relation['requirements'] and not quest.get('unmodeledObjectiveKinds'):
                quest.pop('objectiveLocationsIncomplete',None)
                quest['otherLocationsIncomplete']=False
        if not relation['requirements'] and not quest.get('objectives') and (exact or source.get('triggerEnd','converted-baseline')!='converted-baseline'):
            point = event_point(row,quest,data,area_maps,source.get('triggerEnd','converted-baseline'))
            if point:
                quest['objectives']=[point]; used=True
                quest.pop('objectiveLocationsIncomplete',None)
        if exact or source.get('zoneOrSort','converted-baseline')!='converted-baseline':
            area = row.get('zoneOrSort')
            if type(area) is int and area>0:
                quest.setdefault('areaID',area)
                if area in area_maps: quest.setdefault('mapID',area_maps[area])
                if not quest.get('categoryPath') or quest['categoryPath']=='uncategorized':
                    quest['categoryPath']=categories.get(area,'uncategorized')
        for field,key in (('requiredRaces','raceMask'),('requiredClasses','classMask')):
            mask = row.get(field)
            if type(mask) is int and mask>=0 and (exact or source.get(field,'converted-baseline')!='converted-baseline'):
                # Current published masks, including an explicit zero, take
                # precedence over the converted old baseline. Do not attach
                # a second race gate from a mask that we declined to import.
                if key in quest and source.get(field,'converted-baseline')=='converted-baseline': continue
                if field=='requiredRaces':
                    if mask & ~sum(RACE_BITS.values()):
                        provenance['withheld_fields'].append([ident,field]); continue
                    quest['allowedRaceIDs']=[race for race,bit in RACE_BITS.items() if mask & bit] if mask else []
                    if mask & ALLIANCE and not mask & HORDE: quest.setdefault('side','Alliance')
                    elif mask & HORDE and not mask & ALLIANCE: quest.setdefault('side','Horde')
                    elif mask==0 or mask & ALLIANCE and mask & HORDE: quest.setdefault('side','Both')
                if key not in quest or source.get(field,'converted-baseline')!='converted-baseline': quest[key]=mask
        for field,key in (('preQuestGroup','prerequisiteAll'),('preQuestSingle','prerequisiteAny')):
            parents = ids(row.get(field))
            if parents and (exact or source.get(field,'converted-baseline')!='converted-baseline'):
                if any(p==ident or p not in records for p in parents): provenance['withheld_fields'].append([ident,field]); continue
                current = [quest['previousQuest']] if quest.get('previousQuest') else quest.get(key,[])
                if field=='preQuestGroup' and source.get(field,'converted-baseline')!='converted-baseline' \
                    and (not current or set(current).issubset(parents)):
                    quest[key]=parents; used=True
                    quest['prerequisiteSource']='Published Forever beta prerequisites'
                    continue
                if current and set(current)!=set(parents): provenance['withheld_fields'].append([ident,field]); continue
                if not current:
                    quest[key]=parents; used=True
                    quest['prerequisiteSource']='Published Forever beta prerequisites' if source.get(field,'converted-baseline')!='converted-baseline' else 'Published converted-baseline prerequisites'
        if exact:
            quest.setdefault('prerequisitesRead',True)
            for field in ('requiredSkill','requiredMinRep','requiredMaxRep','parentQuest','availableStartingWith','availableUntilCompleted','exclusiveTo'):
                if row.get(field): quest['prerequisitesUnverified']=True
            if any(k=='quest' and i==ident and field in ('requiredSkill','requiredMinRep','requiredMaxRep','requiredClasses','requiredRaces')
                for k,i,field in provenance['skipped_nonliteral_fields']): quest['prerequisitesUnverified']=True
        if type(row.get('specialFlags')) is int and row['specialFlags'] & 1: quest['repeatable']=True
        if type(row.get('questFlags')) is int and row['questFlags'] & (4096|32768|65536): quest['repeatable']=True
        if used: quest['betaFactsSource']=provenance['source']; provenance['quests_used'].append(ident)
    provenance['inverse_beta_relations_used']=[]
    for ident,quest in records.items():
        relation=refs.setdefault(ident,{'starts':[],'ends':[],'requirements':[]})
        for role in ('starts','ends'):
            values=[{k:v for k,v in r.items() if k!='_basis'} for r in inverse[ident][role] if r['_basis']!='converted-baseline']
            if values and not relation[role]:
                relation[role]=values
                provenance['inverse_beta_relations_used'].append([ident,role])
    return provenance
