"""Public Forever entity/requirement facts; never evaluate downloaded scripts.

Quest prose and community comments are deliberately not copied. Short objective
names, quantities, explicit relations and published coordinates are game facts.
"""
import collections
import html
import json
import math
import re

from import_warcraftdb import clean, number
from import_wowhead import json_after


TYPES = {'npc': 1, 'object': 2, 'item': 3}


def text(value):
    return clean(html.unescape(re.sub('<[^>]+>', '', value or '')))


def listviews(page):
    """Read literal Listview JSON only, excluding variables/functions/comments."""
    result = {}
    for match in re.finditer(r'new Listview\((.*?)\);', page, re.S):
        spec = match.group(1)
        ident = re.search(r"\bid:\s*['\"]([a-z0-9-]+)['\"]", spec)
        template = re.search(r"\btemplate:\s*['\"]([a-z]+)['\"]", spec)
        data = json_after(spec, 'data:')
        if ident and template and isinstance(data, list):
            result[ident[1]] = (template[1], data)
    return result


def quest_relations(page):
    refs = {'starts': [], 'ends': [], 'requirements': [], 'provided': []}
    for match in re.finditer(r'WH\.markup\.printHtml\(\s*("(?:[^"\\]|\\.)*")\s*,\s*"infobox-contents-\d+"', page):
        box = json.loads(match.group(1))
        for role, label in (('starts', 'Start'), ('ends', 'End')):
            row = re.search(r'\b' + label + r':(.*?)(?:\[/li\]|$)', box)
            if row:
                for kind, entity, name in re.findall(r'\[url=/forever/(npc|object|item)=(\d+)[^\]]*\](.*?)\[/url\]', row[1]):
                    refs[role].append({'entityType': kind, 'entityID': int(entity), 'name': text(name)})
    boundary = page.find('new Mapper(')
    if boundary < 0:
        heading = re.search(r'<h2[^>]*>(?:Description|Completion|Rewards)', page)
        boundary = heading.start() if heading else len(page)
    tables = re.findall(r'<table[^>]*class=["\'][^"\']*\bicon-list\b[^"\']*["\'][^>]*>(.*?)</table>', page[:boundary], re.S)
    for body in tables[:1]:
        for count, row in re.findall(r'<tr[^>]*data-icon-list-quantity=["\'](\d+)["\'][^>]*>(.*?)</tr>', body, re.S):
            link = re.search(r'<a[^>]*href=["\']/forever/(npc|object|item)=(\d+)[^"\']*["\'][^>]*>(.*?)</a>', row, re.S)
            if link and 0 < int(count) <= 10000:
                role = 'provided' if re.search(r'\(Provided\)', text(row), re.I) else 'requirements'
                refs[role].append({'entityType': link[1], 'entityID': int(link[2]),
                    'name': text(link[3]), 'quantity': int(count)})
    # A factual item-use relation requires the published goal to name both
    # the provided item and the mapped target. No source prose is retained.
    description = re.search(r'<meta name="description" content="(.*?)"', page, re.S)
    goal = html.unescape(description[1]) if description else ''
    for item in refs['provided']:
        use = re.search(r'\bUse (?:the )?' + re.escape(item['name']) + r' on (.*?)(?:[.,]| when | to |$)', goal, re.I)
        if not use:continue
        names={ident:text(value['name']) for kind,ident,value in mapper_entities(page,{}) if kind=='npc'}
        for ref in refs['requirements']:
            name=names.get(ref['entityID'],ref['name']).lower()
            if ref['entityType']=='npc' and use[1].strip().lower() in (name,name+'s'):
                ref.update(action='use',useItemName=item['name'])
    return refs


def warcraftdb_objective_facts(raw):
    """Structured IDs/counts and the explicitly provided item, without prose."""
    data=raw.get('data',{});provided=[];requirements=[]
    item=data.get('provided_item')
    if isinstance(item,dict) and type(item.get('id')) is int and item['id']>0:
        provided.append({'entityType':'item','entityID':item['id'],'name':text(item.get('name',''))})
    for objective in data.get('objectives',[]):
        kind=objective.get('link_node');ident=objective.get('link_id');quantity=objective.get('amount')
        if kind not in ('npc','object','item') or type(ident) is not int or ident<=0 or type(quantity) is not int or quantity<=0:continue
        if kind=='item' and any(p['entityID']==ident for p in provided):continue
        ref={'entityType':kind,'entityID':ident,'name':text(objective.get('description','')),'quantity':quantity}
        action={0:'kill',3:'talk',2:'interact',1:'collect'}.get(objective.get('type'))
        if action:ref['action']=action
        if action=='talk':ref['name']=re.sub(r'^Speak (?:with|to)\s+','',ref['name'])
        requirements.append(ref)
    return requirements,provided


def warcraftdb_map_facts(raw, quest, refs, entities, known_maps):
    """Fill missing stages from native map points, not tiles or quest prose.

    Objective indexes refer to the original, unfiltered objective array. An
    explicit target/count must match our requirement before an area is used.
    A polygon contributes a listed area point, never an invented centroid or
    an inferred NPC spawn. Existing detailed destinations always win.
    """
    data=raw.get('data',{});map_data=raw.get('extra',{}).get('quest_map',{})
    if not isinstance(map_data,dict) or text(data.get('name',''))!=quest.get('title'):return 0
    floors={f['id'] for f in map_data.get('floors',[]) if isinstance(f,dict)
        and type(f.get('id')) is int and f['id'] in known_maps}
    source='Warcraft DB Forever native quest map'
    def point(row, map_id=None):
        if not isinstance(row,dict):return None
        map_id=row.get('ui_map_id') if map_id is None else map_id
        x,y=row.get('u'),row.get('v')
        if type(map_id) is not int or map_id not in floors or not all(type(v) in (int,float)
            and math.isfinite(v) and 0<=v<=1 for v in (x,y)):return None
        return {'mapID':map_id,'x':x,'y':y,'locationSource':source}
    added=0
    for key,role in (('starts','starts'),('turn_ins','ends')):
        if quest.get(role):continue
        points=[p for row in map_data.get(key,[]) if (p:=point(row))]
        if not points:continue
        references=refs.get(role,[])
        ref=references[0] if len(references)==1 else None
        for p in points:
            # A sole published relation can name this destination. Without
            # that relation, keep the quest label; do not invent a giver ID.
            p.update(name=ref['name'] if ref else quest['title'],entityID=ref['entityID'] if ref else 0)
            if ref:
                p['entityType']=ref['entityType']
                if ref['entityType']=='npc':p['npc']=True
        quest[role]=[choose_location(points,quest)];added+=1
    objectives=data.get('objectives',[])
    candidates=collections.defaultdict(list)
    for area in map_data.get('objectives',[]):
        if not isinstance(area,dict):continue
        index=area.get('objective_index')
        if type(index) is not int or not 0<=index<len(objectives):continue
        objective=objectives[index]
        if not isinstance(objective,dict):continue
        req=next((r for r in refs['requirements'] if r['entityType']==objective.get('link_node')
            and r['entityID']==objective.get('link_id') and r.get('quantity')==objective.get('amount')),None)
        if not req:continue
        existing=quest.get('objectives',[])
        if any((req['entityType']=='item' and (p.get('itemID')==req['entityID'] or p.get('itemName')==req['name']))
            or (req['entityType']!='item' and p.get('entityID')==req['entityID']) for p in existing):continue
        for row in area.get('points',[]):
            p=point(row,area.get('ui_map_id'))
            if p:
                p.update(name=req['name'],entityID=req['entityID'],entityType=req['entityType'])
                if req['entityType']=='npc':p['npc']=True
                candidates[(req['entityType'],req['entityID'])].append(point_for(p,'q',req))
    for values in candidates.values():
        quest.setdefault('objectives',[]).append(choose_location(values,quest));added+=1
    if candidates:
        quest.pop('missingRequirements',None)
        enrich(quest,refs,entities)
    if added:quest['nativeMapSource']=source
    return added


def valid_coord(value):
    return isinstance(value, list) and len(value) == 2 and all(type(v) in (int, float)
        and math.isfinite(v) and 0 <= v <= 100 for v in value)


def representative_coords(coords, maximum=16):
    """Keep actual published spawns, never a centroid in impassable terrain."""
    groups = collections.defaultdict(list)
    for coord in coords:
        if valid_coord(coord):
            key = (int(coord[0] // 10), int(coord[1] // 10))
            if coord not in groups[key]:
                groups[key].append(coord)
    result = []
    for _, values in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))[:maximum]:
        mean = [sum(p[i] for p in values) / len(values) for i in (0, 1)]
        result.append(min(values, key=lambda p: ((p[0]-mean[0])**2+(p[1]-mean[1])**2, p)))
    return result


def entity_facts(page, kind, entity_id):
    canonical=re.search(r'<link rel="canonical" href="https://www\.wowhead\.com/forever/'
        + re.escape(kind) + r'=(\d+)(?:/[^\"]*)?"',page)
    if not canonical or int(canonical[1]) != entity_id:
        raise ValueError('Entity page identity does not match requested type/ID')
    title = re.search(r'<h1[^>]*>(.*?)</h1>', page, re.S)
    result = {'name': text(title[1]) if title else '', 'locations': [], 'source': 'Wowhead Forever'}
    mapper = json_after(page, 'var g_mapperData = ')
    for area, floors in (mapper.items() if isinstance(mapper, dict) else []):
        for floor in floors if isinstance(floors, list) else []:
            map_id = number(floor.get('uiMapId'), 1000000)
            if not map_id or not isinstance(floor.get('coords'), list):
                continue
            for coord in representative_coords(floor['coords']):
                result['locations'].append({'mapID': map_id, 'x': coord[0]/100, 'y': coord[1]/100,
                    'sourceAreaID': int(area), 'sourceZone': text(floor.get('uiMapName', ''))})
    plural = 'npcs' if kind == 'npc' else 'objects' if kind == 'object' else 'items'
    metadata = json_after(page, f'$.extend(g_{plural}[{entity_id}], ')
    if isinstance(metadata, dict) and metadata.get('id') == entity_id:
        for key in ('minlevel', 'maxlevel', 'classification'):
            value = number(metadata.get(key), 255)
            if value is not None:
                result[key] = value
    if kind == 'item':
        sources = []
        for role, (template, rows) in listviews(page).items():
            source_kind = {'npc': 'npc', 'object': 'object'}.get(template)
            if not source_kind or role not in ('dropped-by', 'contained-in', 'contained-in-object', 'sold-by'):
                continue
            for row in rows:
                ident = number(row.get('id'))
                if ident and ident > 0:
                    source = {'entityType': source_kind, 'entityID': ident, 'name': text(row.get('name')),
                        'action': 'buy' if role == 'sold-by' else 'loot' if source_kind == 'npc' else 'gather'}
                    for key in ('minlevel', 'maxlevel'):
                        value = number(row.get(key), 255)
                        if value is not None:
                            source[key] = value
                    if isinstance(row.get('location'), list):
                        source['areas'] = [a for a in row['location'] if number(a,1000000)]
                    sources.append(source)
        if sources:
            result['sources'] = sources[:128]
    return result


def mapper_entities(page, area_maps):
    mapper = json_after(page, 'new Mapper(')
    result = []
    for area, group in (mapper.get('objectives', {}) if isinstance(mapper, dict) else {}).items():
        for floor in group.get('levels', []):
            if not isinstance(floor, list):
                continue
            for point in floor:
                kind = {1:'npc', 2:'object', 3:'item'}.get(point.get('type'))
                ident = number(point.get('id'))
                if not kind or not ident:
                    continue
                coords = point.get('coords')
                if not isinstance(coords, list):
                    coords = [point.get('coord')]
                locations = []
                for coord in representative_coords(coords):
                    location = {'x': coord[0]/100, 'y':coord[1]/100,
                        'sourceAreaID': int(area), 'sourceZone': text(group.get('zone'))}
                    if int(area) in area_maps:
                        location['mapID'] = area_maps[int(area)]
                    locations.append(location)
                result.append((kind, ident, {'name': text(point.get('name')), 'locations': locations,
                    'source': 'Wowhead Forever quest mapper'}))
    return result


def point_for(entity, role, requirement=None):
    result = dict(entity)
    result['name'] = entity.get('name', '')
    if entity.get('entityType') == 'npc':
        result['npc'] = True
    if requirement:
        if requirement.get('quantity'):
            result['quantity'] = requirement['quantity']
        elif requirement.get('quantityUnknown'):
            result.pop('quantity', None)
            result['quantityUnknown'] = True
        result['objectiveKey'] = requirement['entityType'] + ':' + str(requirement['entityID'])
        if requirement['entityType'] == 'item':
            result['itemID'], result['itemName'] = requirement['entityID'], requirement['name']
        result['action'] = entity.get('action') or ('collect' if requirement['entityType'] == 'item' else None)
        if result['action'] is None:
            result.pop('action', None)
        for key in ('useItemName','spellID','alternativeEntityIDs','progressName','objectiveLabel'):
            if key in requirement:
                result[key] = requirement[key]
        if requirement.get('action') and (requirement['action'] != 'collect' or not entity.get('action')):
            result['action'] = requirement['action']
    return result


def choose_location(candidates, quest):
    anchor = next(iter(quest.get('starts') or quest.get('ends') or []), None)
    def rank(point):
        same = anchor and point['mapID'] == anchor.get('mapID')
        own = point['mapID'] == quest.get('mapID')
        dist = (point['x']-anchor['x'])**2+(point['y']-anchor['y'])**2 if same else 0
        return (0 if same else 1 if own else 2, dist, point['mapID'], point['entityID'], point['x'], point['y'])
    return min(candidates, key=rank) if candidates else None


def named_item_source(item_name, source_name):
    """A source named by the item is preferable to an unrelated alternate.

    This does not invent a loot relation or estimate drop rates. The caller
    must already have an explicit source relation for this exact item goal.
    """
    normalize=lambda s:re.sub(r'[^a-z0-9]','',s.lower())
    item,source=normalize(item_name),normalize(source_name)
    return len(source) if len(source)>=5 and source in item else 0


def enrich(quest, refs, entities):
    """Fill real source gaps. Existing mapped instructions take precedence."""
    quest['requirements'] = refs['requirements']
    if refs.get('provided'):quest['providedItems'] = refs['provided']
    def locations(ref):
        if ref.get('alternativeEntityIDs'):
            result = []
            for ident in ref['alternativeEntityIDs']:
                alternate = dict(ref,entityID=ident,name='')
                alternate.pop('alternativeEntityIDs')
                result.extend(locations(alternate))
            return result
        entity = entities.get(ref['entityType'], {}).get(ref['entityID'], {})
        return [dict(p, name=ref['name'] or entity.get('name',''), entityID=ref['entityID'],
                     entityType=ref['entityType']) for p in entity.get('locations',[]) if p.get('mapID')
            and (quest.get('legacyFactsSource') or not p.get('locationSource','').startswith('Older-world'))]
    for role in ('starts','ends'):
        if not quest.get(role):
            points = [point_for(p, role) for ref in refs[role] for p in locations(ref)]
            if role=='starts':
                for ref in refs[role]:
                    if ref['entityType']=='item':
                        item=entities['item'].get(ref['entityID'],{})
                        if item.get('source','').startswith('Older-world') and not quest.get('legacyFactsSource'):continue
                        for source in item.get('sources',[]):
                            for p in locations(source):
                                p.update(action='start-item',sourceAction=source.get('action'),itemID=ref['entityID'],itemName=ref['name'])
                                points.append(point_for(p,role))
            chosen = choose_location(points,quest)
            if chosen:
                quest[role] = [chosen]
    objectives = quest.setdefault('objectives',[])
    unresolved = []
    for req in refs['requirements']:
        matches = [p for p in objectives if (req['entityType'] == 'item' and p.get('itemName') == req['name'])
            or (req['entityType'] == 'item' and p.get('itemID') == req['entityID'])
            or (req['entityType'] != 'item' and p.get('entityID') == req['entityID'])]
        for point in matches:
            if req['entityType']=='item' and point.get('entityID') and point.get('mapID'):
                point['legacyStepKey']='q:'+str(point['mapID'])+':npc:'+str(point['entityID'])
                alternatives=[p for group in quest.get('objectiveAlternatives',[]) if group.get('itemName')==req['name']
                    and group.get('sourceObjective')==point.get('sourceObjective') for p in group.get('locations',[])
                    if p.get('npc') and p.get('mapID')==point.get('mapID') and named_item_source(req['name'],p.get('name',''))]
                if alternatives and not named_item_source(req['name'],point.get('name','')):
                    chosen=choose_location(alternatives,quest)
                    point.update({key:chosen[key] for key in ('mapID','x','y','name','entityID','npc','action') if key in chosen})
            point.update({k:v for k,v in point_for(point,'q',req).items() if k in
                ('quantity','objectiveKey','itemID','itemName','action','useItemName','spellID','alternativeEntityIDs','progressName','objectiveLabel')})
        if matches:
            continue
        candidates = []
        if req['entityType'] == 'item':
            item = entities.get('item',{}).get(req['entityID'],{})
            if item.get('source','').startswith('Older-world') and not quest.get('legacyFactsSource'):
                item = {}
            sources = item.get('sources',[])
            # An explicitly located ground item can be collected directly.
            # Never substitute a drop source's position for the item itself.
            for point in locations(req):
                point['action']='collect'
                candidates.append(point_for(point,'q',req))
            # Prefer sources the quest already explicitly names; a generic
            # common-item source in another continent cannot outrank them.
            targets = {p.get('entityID') for p in quest.get('npcTargets',[])}
            for source in sources:
                if source.get('action')=='loot' and source.get('minlevel',0)>quest.get('level',255)+5:continue
                if targets and source['entityType'] == 'npc' and source['entityID'] not in targets:
                    continue
                for point in locations(source):
                    point['action'] = source['action']
                    candidates.append(point_for(point,'q',req))
            if not candidates and targets:
                for source in sources:
                    if source.get('action')=='loot' and source.get('minlevel',0)>quest.get('level',255)+5:continue
                    for point in locations(source):
                        if point['mapID'] == quest.get('mapID'):
                            point['action'] = source['action']; candidates.append(point_for(point,'q',req))
        else:
            candidates = [point_for(p,'q',req) for p in locations(req)]
            for p in candidates:
                if req['entityType'] == 'npc':
                    old = next((t for t in quest.get('npcTargets',[]) if t.get('entityID') == req['entityID']),{})
                    if old.get('action') and not req.get('action'):
                        p['action'] = old['action']
                else:
                    p['action'] = 'interact'
        chosen = choose_location(candidates,quest)
        named=[p for p in candidates if p.get('npc') and req['entityType']=='item' and chosen
            and p['mapID']==chosen['mapID'] and named_item_source(req['name'],p.get('name',''))]
        if named:chosen=choose_location(named,quest)
        # Two item goals from the same proven drop source can share the
        # already-published farming area; a second trip adds no useful work.
        if chosen and req['entityType']=='item':
            sources=entities.get('item',{}).get(req['entityID'],{}).get('sources',[])
            same=next((p for p in objectives if p.get('itemName') and any(
                source['entityID']==p.get('entityID') and source['entityType']==('npc' if p.get('npc') else 'object')
                for source in sources)),None)
            if same:
                chosen.update({key:same[key] for key in ('mapID','x','y','name','entityID','npc') if key in same})
        if chosen:
            if chosen.get('action')=='event' and re.search(r'\b(?:DNT|DND|KILL CREDIT|QUEST CREDIT)\b',chosen.get('name',''),re.I):
                # An invisible credit marker has a real event area, but its
                # developer name isn't an NPC the player should talk to.
                chosen['name']=quest['title']; chosen.pop('npc',None)
            objectives.append(chosen)
            if chosen.get('action') == 'buy':
                for item in quest.get('requiredItems',[]):
                    if item['itemID'] == req['entityID']:item['buyable'] = True
            if chosen.get('npc'):
                target = {k:chosen[k] for k in ('entityID','name','action','itemName','npc','alternativeEntityIDs','progressName','objectiveLabel') if k in chosen}
                if target not in quest.setdefault('npcTargets',[]):
                    quest['npcTargets'].append(target)
        else:
            unresolved.append(req)
    if unresolved:
        quest['missingRequirements'] = unresolved
        quest['objectiveLocationsIncomplete'] = True
    elif refs['requirements'] and quest.get('prerequisitesRead'):
        # Only repair missing sources when every explicit objective is covered.
        # Unmapped quest objectives not represented in the table still count.
        other = [p for p in quest.get('unmappedLocations',[]) if p.get('kind') == 'q'
            and not any(r['entityID'] == p.get('entityID') or r['name'] == p.get('itemName') for r in refs['requirements'])]
        if not other and not quest.get('unmodeledObjectiveKinds'):
            quest.pop('objectiveLocationsIncomplete',None)
            quest['otherLocationsIncomplete'] = False
    quest['objectiveFactsSource'] = quest.get('requirementSource', 'Published Forever quest/entity relations')
    return quest
