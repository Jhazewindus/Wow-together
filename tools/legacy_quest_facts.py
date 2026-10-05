"""Read numeric/name facts from a pinned, licensed older-world SQL snapshot.

No SQL is executed and no server/addon logic, quest prose or scripts are copied.
Callers must gate reuse on matching Forever identities/change metadata. World
coordinates stay world coordinates until a validated map transform exists.
"""
import collections
import gzip
import math
import re


COMMIT = 'ec4f596146be6467ea93c57397858e329e2db852'
SNAPSHOT_SHA256 = '4f92db520868ab4e566726f68b5b2e380ae781209beaf22237b4f7f04600d0c0'
SOURCE = 'https://github.com/cmangos/classic-db/tree/' + COMMIT
SELECTION = {
    'quest_template': {'entry','Title','MinLevel','QuestLevel','RequiredClasses','RequiredRaces','RequiredCondition',
        'RequiredMinRepFaction','RequiredMaxRepFaction','PrevQuestId','SpecialFlags','SrcItemId',
        *('ReqItemId'+str(i) for i in range(1,5)), *('ReqItemCount'+str(i) for i in range(1,5)),
        *('ReqCreatureOrGOId'+str(i) for i in range(1,5)), *('ReqCreatureOrGOCount'+str(i) for i in range(1,5)),
        *('ReqSpellCast'+str(i) for i in range(1,5))},
    'creature_template': {'Entry','Name','MinLevel','MaxLevel','Rank','LootId','VendorTemplateId'},
    'gameobject_template': {'entry','name','type','data1'},
    'item_template': {'entry','name','startquest','BuyPrice'},
    'creature': {'id','map','position_x','position_y'},
    'gameobject': {'id','map','position_x','position_y'},
    'creature_questrelation': {'id','quest'}, 'creature_involvedrelation': {'id','quest'},
    'gameobject_questrelation': {'id','quest'}, 'gameobject_involvedrelation': {'id','quest'},
    'creature_loot_template': {'entry','item','ChanceOrQuestChance','mincountOrRef'},
    'gameobject_loot_template': {'entry','item','ChanceOrQuestChance','mincountOrRef'},
    'npc_vendor': {'entry','item','condition_id'},
    'npc_vendor_template': {'entry','item','condition_id'},
}


def sql_rows(body):
    """A data lexer, including escaped quotes and parentheses inside strings."""
    row, value, quoted, escaped, in_row = [], [], False, False, False
    for char in body:
        if quoted:
            if escaped:
                value.append({'n':'\n','r':'\r','t':'\t','0':'\x00'}.get(char,char)); escaped=False
            elif char == '\\': escaped=True
            elif char == "'": quoted=False
            else: value.append(char)
        elif char == "'": quoted=True
        elif char == '(' and not in_row: in_row=True; row=[]; value=[]
        elif in_row and char in ',)':
            field=''.join(value).strip(); row.append(field); value=[]
            if char == ')': yield row; in_row=False
        elif in_row: value.append(char)
    if quoted or in_row:
        raise ValueError('Incomplete SQL data row')


def read_snapshot(path):
    import hashlib
    if hashlib.sha256(path.read_bytes()).hexdigest() != SNAPSHOT_SHA256:
        raise ValueError('Older-world snapshot differs from the reviewed, pinned source')
    facts = {key:[] for key in SELECTION}
    columns, active = {}, None
    with gzip.open(path,'rt',encoding='utf-8',errors='replace') as stream:
        for line in stream:
            create=re.match(r'CREATE TABLE `([^`]+)`',line)
            if create:
                active=create[1];columns[active]=[];continue
            if active:
                column=re.match(r'\s+`([^`]+)`',line)
                if column:columns[active].append(column[1])
                if line.startswith(')'):active=None
                continue
            insert=re.match(r'INSERT INTO `([^`]+)` VALUES (.*);\s*$',line)
            if not insert or insert[1] not in SELECTION: continue
            table=insert[1]
            selected=[(i,name) for i,name in enumerate(columns[table]) if name in SELECTION[table]]
            for values in sql_rows(insert[2]):
                if len(values)!=len(columns[table]):raise ValueError('SQL column count changed: '+table)
                row={}
                for i,name in selected:
                    value=values[i]
                    if name not in ('Title','Name','name'):
                        value=float(value) if '.' in value or 'e' in value.lower() else int(value)
                        if not math.isfinite(value):raise ValueError('Nonfinite source number')
                    row[name]=value
                facts[table].append(row)
    return facts


def indexed(facts):
    result={'quests':{},'npc':{},'object':{},'item':{},'starts':collections.defaultdict(list),
        'ends':collections.defaultdict(list),'drops':collections.defaultdict(list)}
    for row in facts['quest_template']:result['quests'][row['entry']]=row
    for kind,table,id_field,name_field in (('npc','creature_template','Entry','Name'),
            ('object','gameobject_template','entry','name'),('item','item_template','entry','name')):
        for row in facts[table]:result[kind][row[id_field]]={'name':row[name_field],'raw':row,'worldLocations':[]}
    for ident,item in result['item'].items():
        if item['raw']['startquest']>0:
            result['starts'][item['raw']['startquest']].append({'entityType':'item','entityID':ident,'name':item['name']})
    for kind,table in (('npc','creature'),('object','gameobject')):
        for row in facts[table]:
            if row['id'] in result[kind] and row['map'] in (0,1):
                result[kind][row['id']]['worldLocations'].append((row['map'],row['position_x'],row['position_y']))
    for kind,prefix in (('npc','creature'),('object','gameobject')):
        for role,suffix in (('starts','questrelation'),('ends','involvedrelation')):
            for row in facts[prefix+'_'+suffix]:
                entity=result[kind].get(row['id'])
                if entity:result[role][row['quest']].append({'entityType':kind,'entityID':row['id'],'name':entity['name']})
    loot_owners=collections.defaultdict(list)
    for ident,entity in result['npc'].items():
        loot_owners['npc',entity['raw']['LootId']].append(ident)
    for ident,entity in result['object'].items():
        if entity['raw']['type']==3:loot_owners['object',entity['raw']['data1']].append(ident)
    for kind,table in (('npc','creature_loot_template'),('object','gameobject_loot_template')):
        for row in facts[table]:
            if row['mincountOrRef']<=0 or row['ChanceOrQuestChance']==0:continue
            for ident in loot_owners[kind,row['entry']]:
                entity=result[kind][ident]
                ref={'entityType':kind,'entityID':ident,'name':entity['name'],
                    'action':'loot' if kind=='npc' else 'gather'}
                if kind=='npc':ref.update(minlevel=entity['raw']['MinLevel'],maxlevel=entity['raw']['MaxLevel'])
                if ref not in result['drops'][row['item']]:result['drops'][row['item']].append(ref)
    vendors=collections.defaultdict(list)
    for ident,entity in result['npc'].items():
        if entity['raw'].get('VendorTemplateId'):
            vendors[entity['raw']['VendorTemplateId']].append(ident)
    for table in ('npc_vendor','npc_vendor_template'):
        for row in facts.get(table,[]):
            if row['condition_id'] or row['item'] not in result['item']:continue
            for ident in ([row['entry']] if table=='npc_vendor' else vendors[row['entry']]):
                entity=result['npc'].get(ident)
                if entity:
                    ref={'entityType':'npc','entityID':ident,'name':entity['name'],'action':'buy'}
                    if ref not in result['drops'][row['item']]:result['drops'][row['item']].append(ref)
    return result


def matches(quest, old):
    return quest.get('foreverStatus')=='unchanged' and quest.get('title')==old['Title'] \
        and quest.get('level')==old['QuestLevel'] and quest.get('minLevel')==old['MinLevel'] \
        and not quest.get('levelingExcluded')


def requirements(old, data):
    result=[]
    for i in range(1,5):
        ident=old['ReqItemId'+str(i)];count=old['ReqItemCount'+str(i)]
        if ident>0 and count>0 and ident in data['item']:
            result.append({'entityType':'item','entityID':ident,'name':data['item'][ident]['name'],'quantity':count})
        ident=old['ReqCreatureOrGOId'+str(i)];count=old['ReqCreatureOrGOCount'+str(i)]
        kind='npc' if ident>0 else 'object';ident=abs(ident)
        if ident and count>0 and ident in data[kind]:
            ref={'entityType':kind,'entityID':ident,'name':data[kind][ident]['name'],'quantity':count}
            if old['ReqSpellCast'+str(i)]>0:
                ref['action']='use';ref['spellID']=old['ReqSpellCast'+str(i)]
                item=data['item'].get(old['SrcItemId'])
                if item:ref['useItemName']=item['name']
            else:ref['action']='kill' if kind=='npc' else 'interact'
            result.append(ref)
    return result


def calibrate(entities, legacy):
    """Fit aligned map axes with robust medians and independent residual checks.

    At least five single-spawn NPCs, broad axis coverage and <=0.8% residuals
    are required. Reject inconsistent/changed maps rather than invent bounds.
    """
    anchors=collections.defaultdict(list)
    for ident,entity in entities.get('npc',{}).items():
        positions=legacy['npc'].get(ident,{}).get('worldLocations',[])
        if len(positions)!=1:continue
        continent,wx,wy=positions[0]
        for point in entity.get('locations',[]):
            source=point.get('locationSource','')
            if point.get('mapID') and not source.startswith('Older-world') and 'converted-baseline' not in source:
                anchors[point['mapID'],continent].append((wx,wy,point['x'],point['y']))
    import statistics
    transforms={}
    for (map_id,continent),points in anchors.items():
        if len(points)<5:continue
        coefficients=[]
        for axis,world_axis in ((2,1),(3,0)):
            pairs=[(a[axis]-b[axis])/(a[world_axis]-b[world_axis]) for i,a in enumerate(points) for b in points[i+1:]
                if abs(a[axis]-b[axis])>.15 and abs(a[world_axis]-b[world_axis])>100]
            if len(pairs)<3:break
            slope=statistics.median(pairs);offset=statistics.median(p[axis]-slope*p[world_axis] for p in points)
            coefficients.append((slope,offset))
        if len(coefficients)!=2:continue
        sx,ox=coefficients[0];sy,oy=coefficients[1]
        good=[p for p in points if abs(sx*p[1]+ox-p[2])<=.008 and abs(sy*p[0]+oy-p[3])<=.008]
        if len(good)<5 or len(good)<len(points)*.8:continue
        if max(p[2] for p in good)-min(p[2] for p in good)<.25 or max(p[3] for p in good)-min(p[3] for p in good)<.25:continue
        transforms[map_id]={'continent':continent,'sx':sx,'ox':ox,'sy':sy,'oy':oy,'anchors':len(good)}
    return transforms


def mapped_locations(entity, transforms, map_ids):
    result=[]
    groups=collections.defaultdict(list)
    for continent,wx,wy in entity.get('worldLocations',[]):
        for map_id in map_ids:
            transform=transforms.get(map_id)
            if not transform or continent!=transform['continent']:continue
            x=transform['sx']*wy+transform['ox'];y=transform['sy']*wx+transform['oy']
            if 0<=x<=1 and 0<=y<=1:groups[map_id].append([x*100,y*100])
    from quest_enrichment import representative_coords
    for map_id,coords in groups.items():
        for x,y in representative_coords(coords):result.append({'mapID':map_id,'x':round(x/100,5),'y':round(y/100,5),
            'locationSource':transforms[map_id].get('locationSource',
                'Older-world fallback; calibrated against Forever published NPCs')})
    return result


def world_locations(entity):
    groups=collections.defaultdict(list)
    for continent,x,y in entity.get('worldLocations',[]):
        groups[continent,int(x//500),int(y//500)].append((x,y))
    result=[]
    for key,points in sorted(groups.items(),key=lambda item:(-len(item[1]),item[0]))[:24]:
        mean=(sum(p[0] for p in points)/len(points),sum(p[1] for p in points)/len(points))
        x,y=min(points,key=lambda p:((p[0]-mean[0])**2+(p[1]-mean[1])**2,p))
        result.append({'continent':key[0],'worldX':x,'worldY':y})
    return result
