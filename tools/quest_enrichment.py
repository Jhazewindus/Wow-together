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
        result['quantity'] = requirement.get('quantity', 1)
        result['objectiveKey'] = requirement['entityType'] + ':' + str(requirement['entityID'])
        if requirement['entityType'] == 'item':
            result['itemID'], result['itemName'] = requirement['entityID'], requirement['name']
        result['action'] = entity.get('action') or ('collect' if requirement['entityType'] == 'item' else None)
        if result['action'] is None:
            result.pop('action', None)
        for key in ('useItemName','spellID'):
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
                ('quantity','objectiveKey','itemID','itemName','action','useItemName','spellID')})
        if matches:
            continue
        candidates = []
        if req['entityType'] == 'item':
            item = entities.get('item',{}).get(req['entityID'],{})
            if item.get('source','').startswith('Older-world') and not quest.get('legacyFactsSource'):
                item = {}
            sources = item.get('sources',[])
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
            objectives.append(chosen)
            if chosen.get('action') == 'buy':
                for item in quest.get('requiredItems',[]):
                    if item['itemID'] == req['entityID']:item['buyable'] = True
            if chosen.get('npc'):
                target = {k:chosen[k] for k in ('entityID','name','action','itemName','npc') if k in chosen}
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
        if not other:
            quest.pop('objectiveLocationsIncomplete',None)
            quest['otherLocationsIncomplete'] = False
    quest['objectiveFactsSource'] = quest.get('requirementSource', 'Published Forever quest/entity relations')
    return quest
