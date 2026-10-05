"""Extract narrowly attributed coordinate observations from captured pages.

Community coordinates are a fallback, never verified beta facts. Require an
explicit entity ID, an explicit single zone, numeric coordinates and agreement
between all observations. No comment prose, addon code or UI is bundled.
"""
import collections
import re

from import_wowhead import json_after


def coordinate_observations(page, quest_id, area_maps):
    candidates=collections.defaultdict(list)
    comments=json_after(page,'var lv_comments0 = ')
    for row in comments if isinstance(comments,list) else []:
        if row.get('deleted') or row.get('outofdate') or row.get('dataTree')!=16:continue
        if type(row.get('id')) is not int:continue
        body=row.get('body','')
        if not isinstance(body,str):continue
        areas={int(a) for a in re.findall(r'\[zone=(\d+)\]',body)}
        if len(areas)!=1:continue
        area=areas.pop();map_id=area_maps.get(area)
        if not map_id:continue
        for kind,ident,segment in re.findall(r'\[(item|npc|object)=(\d+)\]([^\[\]\r\n]{0,100})',body):
            position=re.search(r'\bat\s+(\d{1,3}(?:\.\d+)?)\s*,\s*(\d{1,3}(?:\.\d+)?)\b',segment,re.I)
            if not position:continue
            x,y=map(float,position.groups())
            if not 0<=x<=100 or not 0<=y<=100:continue
            candidates[(kind,int(ident))].append({'mapID':map_id,'x':x/100,'y':y/100,
                'sourceAreaID':area,'locationSource':'Community Forever coordinate observation; beta verification needed',
                'observationQuestID':quest_id,'observationCommentID':row['id']})
    result=[]
    for (kind,ident),points in sorted(candidates.items()):
        first=points[0]
        if any(p['mapID']!=first['mapID'] or abs(p['x']-first['x'])>.01 or abs(p['y']-first['y'])>.01 for p in points[1:]):continue
        result.append((kind,ident,first))
    return result


def apply_observations(pages,records,refs,entities,area_maps):
    used=[]
    for quest_id,page in sorted(pages.items()):
        if quest_id not in records:continue
        relation=refs.get(quest_id,{})
        referenced={(r['entityType'],r['entityID']) for field in ('starts','ends','requirements','provided')
            for r in relation.get(field,[])}
        for kind,ident,point in coordinate_observations(page,quest_id,area_maps):
            if (kind,ident) not in referenced:continue
            entity=entities[kind].setdefault(ident,{'name':'','locations':[]})
            if any(p.get('mapID') for p in entity.get('locations',[])):continue
            entity['locations'].append(point)
            used.append({'questID':quest_id,'entityType':kind,'entityID':ident,
                'commentID':point['observationCommentID'],'mapID':point['mapID']})
    return {'source':'Captured Wowhead Forever comments; explicit ID/zone/coordinate facts only',
        'coordinate_observations_used':used,'limitations':['Community observations are not live-beta verification',
            'Conflicting observations are withheld; published entity positions take precedence','No comment prose included']}
