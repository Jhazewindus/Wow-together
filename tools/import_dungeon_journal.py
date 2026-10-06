"""Extract offline dungeon facts from captured Forever pages; never execute scripts.

Artwork is referenced by verified client filenames, never copied into the addon.
NPC boss flags are supplemented by a reviewed Classic encounter list whose IDs
must also exist on the corresponding Forever zone page. No loot is inferred.
"""
import argparse, csv, hashlib, json, re
from pathlib import Path
from import_travel_network import encode

ROOT = Path(__file__).resolve().parents[1]
MAPS = {
 'ragefire-chasm': 'Ragefire', 'wailing-caverns': 'WailingCaverns', 'the-deadmines': 'TheDeadmines',
 'shadowfang-keep': 'ShadowfangKeep', 'the-stockade': 'TheStockade', 'blackfathom-deeps': 'BlackFathomDeeps',
 'gnomeregan': 'Gnomeregan', 'scarlet-monastery': 'ScarletMonasteryOld', 'razorfen-kraul': 'RazorfenKraul',
 'razorfen-downs': 'RazorfenDowns', 'uldaman': 'Uldaman', 'zulfarrak': 'ZulFarrak', 'maraudon': 'Maraudon',
 'the-temple-of-atalhakkar': 'TheTempleofAtalhakkar', 'blackrock-depths': 'BlackrockDepths',
 'blackrock-spire': 'BlackrockSpire', 'dire-maul': 'DireMaul', 'scholomance': 'ScholomanceOLD', 'stratholme': 'Stratholme',
}

def rows(page, template, name):
    marker = "new Listview({template: '%s', id: '%s'" % (template, name)
    start = page.find(marker)
    if start < 0: return []
    try:
        data = json.JSONDecoder().raw_decode(page[page.index('data:', start)+5:].lstrip())[0]
    except (ValueError, json.JSONDecodeError): return []
    return data if isinstance(data, list) else []

def icons(page):
    result = {}
    for match in re.finditer(r'WH.Gatherer.addData\(3,\s*\d+,\s*', page):
        try: data = json.JSONDecoder().raw_decode(page[match.end():])[0]
        except json.JSONDecodeError: continue
        for key, value in data.items():
            icon = value.get('icon', '')
            if re.fullmatch(r'[a-zA-Z0-9_]+', icon): result[int(key)] = icon
    return result

def clean(value):
    if not isinstance(value,str): return None
    return re.sub(r'[\x00-\x1f|]', '', value)[:180]

def normalize(name): return re.sub(r'[^a-z0-9]', '', name.lower())

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zones',type=Path,required=True)
    parser.add_argument('--bosses',type=Path,required=True)
    parser.add_argument('--listfile',type=Path,required=True)
    args=parser.parse_args()
    definitions=json.loads((ROOT/'WowTogether/DungeonData.json').read_text())['dungeons']
    selected=json.loads((args.zones/'selected-bosses.json').read_text())
    zone_sources=json.loads((args.zones/'capture.json').read_text())
    npc_sources=json.loads((args.bosses/'capture.json').read_text())
    files=list(csv.reader(args.listfile.open(),delimiter=';'))
    heads={normalize(Path(path).stem.removeprefix('UI-EJ-BOSS-')):path[:-4].replace('/','\\') for _,path in files if '/ui-ej-boss-' in path.lower() and path.endswith('.blp')}
    data={}
    for key,definition in definitions.items():
        entry={'name':definition['name'],'bosses':[],'maps':[]}
        if key in zone_sources: entry['zoneID']=zone_sources[key]['id']
        for boss in selected.get(key,[]):
            boss_id=boss['id']; p=args.bosses/(str(boss_id)+'.html')
            if not p.exists():continue
            page=p.read_text(); icon_names=icons(page)
            record={'id':boss_id,'name':clean(boss['name']),'level':boss.get('maxlevel'),'rare':boss.get('classification') in (2,4),'status':boss.get('envChange',{}).get('status','unconfirmed'),'loot':[]}
            head=heads.get(normalize(boss['name']))
            if head:record['portrait']=head
            seen=set()
            for item in rows(page,'item','drops'):
                iid=item.get('id'); kind=item.get('classs'); quality=item.get('quality',0)
                if not isinstance(iid,int) or iid<=0 or iid in seen:continue
                if item.get('commondrop') and kind not in (12,13):continue
                if quality<2 and kind not in (12,13):continue
                seen.add(iid)
                loot={'id':iid,'name':clean(item.get('displayName') or item.get('name')),'quality':quality,'classID':kind,'subclass':item.get('subclass'),'slot':item.get('slot'),'level':item.get('level'),'requiredLevel':item.get('reqlevel'),'status':item.get('envChange',{}).get('status','unconfirmed')}
                if iid in icon_names:loot['icon']='Interface\\Icons\\'+icon_names[iid]
                record['loot'].append({k:v for k,v in loot.items() if v is not None})
            record['loot'].sort(key=lambda v:(-v['quality'],v['name'],v['id']))
            entry['bosses'].append({k:v for k,v in record.items() if v is not None})
        entry['bosses'].sort(key=lambda v:(v.get('level',0),v['name'],v['id']))
        folder=MAPS.get(key)
        if folder:
            floors={}
            for fid,path in files:
                parts=path.split('/')
                if len(parts)!=4 or parts[2]!=folder or not path.endswith('.blp'):continue
                match=re.search(r'(\d+)_(\d+)\.blp$',path)
                if match:floor,tile=map(int,match.groups())
                else:
                    match=re.search(r'(\d+)\.blp$',path)
                    if not match:continue
                    floor,tile=1,int(match.group(1))
                if tile<=12: floors.setdefault(floor,{})[tile]=path[:-4].replace('/','\\')
            for floor,tiles in sorted(floors.items()):
                if set(tiles)==set(range(1,13)):
                    entry['maps'].append({'name':'Floor '+str(floor),'width':1002,'height':668,'tileWidth':256,'tileHeight':256,'tiles':[tiles[i]for i in range(1,13)],'reference':True})
        data[key]=entry
    counts={'dungeons':len(data),'dungeonsWithBosses':sum(bool(e['bosses'])for e in data.values()),'bosses':sum(len(e['bosses'])for e in data.values()),'lootEntries':sum(len(b['loot'])for e in data.values()for b in e['bosses']),'portraits':sum('portrait'in b for e in data.values()for b in e['bosses']),'mapReferences':sum(bool(e['maps'])for e in data.values())}
    result={'schema':1,'captured':'2026-10-06','counts':counts,'dungeons':data}
    (ROOT/'WowTogether/DungeonJournalData.lua').write_text('local addonName, ns = ...\n\n-- Offline Forever facts; no web scripts or images. See DUNGEON_VIEWER.md.\nns.dungeonJournalData = '+encode(result)+'\n')
    manifest={'schema':1,'captured':result['captured'],'counts':counts,'zoneSources':zone_sources,'bossSources':npc_sources,'clientFilenameSource':{'repository':'wowdev/wow-listfile','commit':'2ee24a9d0ff98f614997587e32ee6a0074d0de65','sha256':hashlib.sha256(args.listfile.read_bytes()).hexdigest()},'limitations':['Boss display order is alphabetical within level, not a walkthrough.','Notable boss drops only; common junk/consumables and generic world drops omitted.','Published database facts are a beta snapshot, not proof of current availability.','Classic client floor images are layout references; current client map data takes precedence.','No external images, copied guide text or source scripts are bundled.']}
    (ROOT/'WowTogether/DungeonJournalData.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(counts))
if __name__=='__main__':main()
