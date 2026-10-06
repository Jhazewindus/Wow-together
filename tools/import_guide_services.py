"""Extract inn/taxi/class-trainer facts from the attributed Forever snapshot."""
import argparse
import hashlib
import json
from pathlib import Path

from lupa.lua51 import LuaRuntime
from import_travel_network import COMMIT, encode, plain

ROOT = Path(__file__).resolve().parents[1]
POIS_SHA256 = '3dfa6f85e6fbe1c5a01389d4bcf445f4fa63391484647cdec663a849111e977d'
CLASSES = {'WARRIOR': 1, 'PALADIN': 2, 'HUNTER': 3, 'ROGUE': 4, 'PRIEST': 5,
           'SHAMAN': 7, 'MAGE': 8, 'WARLOCK': 9, 'DRUID': 11}


def collect(path):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != POIS_SHA256:
        raise ValueError('Expected the pinned, reviewed Forever Pois.lua snapshot')
    lua = LuaRuntime(unpack_returned_tuples=True)
    ns = lua.table_from({'RULESET': 'forever'})
    lua.eval('function(text, ns) local f=assert(loadstring(text)); setfenv(f, {}); f("Source",ns) end')(data.decode(), ns)
    settlements = dict(plain(ns.Cities), **plain(ns.Towns))
    inns, taxis, trainers = [], {}, []
    for key, place in sorted(settlements.items()):
        if place.get('taxi'):
            item = {'name': key.replace('_', ' ').title()}
            # A neutral town can have separate Horde/Alliance flight masters.
            # Never transfer its Both ownership to the selected taxi node.
            if place['faction'] != 'Both':
                item['faction'] = place['faction']
            taxis[int(place['taxi'][5:])] = item
    for node in plain(ns.Nodes.Pois):
        place = settlements.get(node.get('town') or node.get('city'))
        class_id = CLASSES.get(node.get('trainer'))
        if node.get('kind') == 'trainer' and class_id:
            owners = {}
            for npc in node.get('npcs', []):
                owner = npc.get('faction') or (place and place['faction'])
                if owner in ('Horde', 'Alliance', 'Both'):
                    owners.setdefault(owner, []).append(npc['id'])
            if not node.get('npcs') and place:
                owners[place['faction']] = []
            for owner, npc_ids in sorted(owners.items()):
                item = {key: node[key] for key in ('mapID', 'x', 'y')}
                item.update(id=node['id'] + ':' + owner, classID=class_id,
                    name=node['trainer'].title() + ' trainer', faction=owner,
                    npcIDs=sorted(set(npc_ids)))
                if place:
                    item['hub'] = (node.get('town') or node.get('city')).replace('_', ' ').title()
                trainers.append(item)
        if node.get('kind') != 'inn' or not place:
            continue  # Never invent ownership or a settlement for an unscoped POI.
        item = {key: node[key] for key in ('id', 'mapID', 'x', 'y')}
        item.update(name=(node.get('town') or node.get('city')).replace('_', ' ').title(), faction=place['faction'])
        if node.get('npcs'):
            item['npcID'] = node['npcs'][0]['id']
        inns.append(item)
    return sorted(inns, key=lambda item: item['id']), taxis, sorted(trainers, key=lambda item: item['id'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pois', type=Path)
    args = parser.parse_args()
    inns, taxis, trainers = collect(args.pois)
    target = ROOT / 'WowTogether/GuideServiceData.lua'
    target.write_text('local addonName, ns = ...\n\n'
        '-- Location facts only, from Mapzeroth Forever 0.6.0 (MIT).\n'
        '-- See TRAVEL_DATA.md / THIRD_PARTY_NOTICES.md; no upstream UI or logic.\n'
        'ns.guideServiceData = ' + encode({'inns': inns, 'taxis': taxis, 'trainers': trainers}) + '\n')
    metadata = {'source': 'https://github.com/tr0tsky0/Mapzeroth', 'commit': COMMIT,
                'file': 'Data/Forever/Pois.lua', 'sha256': POIS_SHA256, 'license': 'MIT',
                'inns': len(inns), 'taxi_settlement_labels': len(taxis),
                'taxi_faction_labels': sum('faction' in item for item in taxis.values()),
                'class_trainer_locations': len(trainers),
                'class_trainer_classes': sorted({item['classID'] for item in trainers}),
                'limitations': ['Published coordinates need beta verification',
                                'Unscoped inns excluded; new inns can be observed in game',
                                'Location data does not establish flight unlocks',
                                'Trainer locations do not establish spell availability or training level caps',
                                'Unknown trainer ownership and non-class training are excluded']}
    (ROOT / 'WowTogether/GuideServiceData.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(f'Extracted {len(inns)} inns, {len(taxis)} taxi labels and {len(trainers)} class-trainer locations.')


if __name__ == '__main__':
    main()
