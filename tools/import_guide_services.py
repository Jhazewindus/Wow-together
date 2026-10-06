"""Extract inn/taxi location facts from the already-attributed Forever snapshot."""
import argparse
import hashlib
import json
from pathlib import Path

from lupa.lua51 import LuaRuntime
from import_travel_network import COMMIT, encode, plain

ROOT = Path(__file__).resolve().parents[1]
POIS_SHA256 = '3dfa6f85e6fbe1c5a01389d4bcf445f4fa63391484647cdec663a849111e977d'


def collect(path):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != POIS_SHA256:
        raise ValueError('Expected the pinned, reviewed Forever Pois.lua snapshot')
    lua = LuaRuntime(unpack_returned_tuples=True)
    ns = lua.table_from({'RULESET': 'forever'})
    lua.eval('function(text, ns) local f=assert(loadstring(text)); setfenv(f, {}); f("Source",ns) end')(data.decode(), ns)
    settlements = dict(plain(ns.Cities), **plain(ns.Towns))
    inns, taxis = [], {}
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
        if node.get('kind') != 'inn' or not place:
            continue  # Never invent ownership or a settlement for an unscoped POI.
        item = {key: node[key] for key in ('id', 'mapID', 'x', 'y')}
        item.update(name=(node.get('town') or node.get('city')).replace('_', ' ').title(), faction=place['faction'])
        if node.get('npcs'):
            item['npcID'] = node['npcs'][0]['id']
        inns.append(item)
    return sorted(inns, key=lambda item: item['id']), taxis


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pois', type=Path)
    args = parser.parse_args()
    inns, taxis = collect(args.pois)
    target = ROOT / 'WowTogether/GuideServiceData.lua'
    target.write_text('local addonName, ns = ...\n\n'
        '-- Location facts only, from Mapzeroth Forever 0.6.0 (MIT).\n'
        '-- See TRAVEL_DATA.md / THIRD_PARTY_NOTICES.md; no upstream UI or logic.\n'
        'ns.guideServiceData = ' + encode({'inns': inns, 'taxis': taxis}) + '\n')
    metadata = {'source': 'https://github.com/tr0tsky0/Mapzeroth', 'commit': COMMIT,
                'file': 'Data/Forever/Pois.lua', 'sha256': POIS_SHA256, 'license': 'MIT',
                'inns': len(inns), 'taxi_settlement_labels': len(taxis),
                'taxi_faction_labels': sum('faction' in item for item in taxis.values()),
                'limitations': ['Published coordinates need beta verification',
                                'Unscoped inns excluded; new inns can be observed in game',
                                'Location data does not establish flight unlocks']}
    (ROOT / 'WowTogether/GuideServiceData.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(f'Extracted {len(inns)} inns and {len(taxis)} taxi settlement labels.')


if __name__ == '__main__':
    main()
