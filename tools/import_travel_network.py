"""Adapt public Forever travel facts; no upstream addon logic is included."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
COMMIT = 'fd68cfe2153379898680c66a01833846f9933587'
FILES = ['Nodes_Kalimdor.lua', 'Nodes_EasternKingdoms.lua', 'Nodes_ZephrasIsle.lua',
         'Borders.lua', 'Pois.lua', 'Edges.lua', 'Geometry.lua', 'PathFactors.lua', 'NodeNames_enUS.lua']
POIS_SHA256 = '3dfa6f85e6fbe1c5a01389d4bcf445f4fa63391484647cdec663a849111e977d'


def plain(value):
    if hasattr(value, 'items'):
        result = {key: plain(item) for key, item in value.items()}
        if result and set(result) == set(range(1, len(result) + 1)):
            return [result[i] for i in range(1, len(result) + 1)]
        return result
    return value


def encode(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return '{' + ','.join(encode(item) for item in value) + '}'
    if isinstance(value, dict):
        return '{' + ','.join('[' + encode(key) + ']=' + encode(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))) + '}'
    return json.dumps(value, ensure_ascii=False)


def settlement_facts(path, nodes):
    """Published occupied locations, not guard boundaries or invented roads."""
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != POIS_SHA256:
        raise ValueError('Expected the pinned Forever settlement facts')
    lua = LuaRuntime(unpack_returned_tuples=True)
    ns = lua.table_from({'RULESET': 'forever'})
    lua.eval('function(text,ns) local f=assert(loadstring(text));setfenv(f,{});f("Source",ns)end')(data.decode(), ns)
    places = dict(plain(ns.Cities), **plain(ns.Towns))
    pois = plain(ns.Nodes.Pois)
    footprints = []
    for key, place in sorted(places.items()):
        taxi = nodes.get(place.get('taxi'))
        # Neutral settlements may contain separate faction flight masters.
        if taxi is not None and place['faction'] != 'Both':
            taxi['faction'] = place['faction']
        points = [(place['x'], place['y'])]
        if taxi is not None and taxi['mapID'] == place['mapID']:
            points.append((taxi['x'], taxi['y']))
        for node in pois:
            if (node.get('town') or node.get('city')) == key and node['mapID'] == place['mapID']:
                points.append((node['x'], node['y']))
        footprints.append({'name': key.replace('_', ' ').title(), 'faction': place['faction'],
            'mapID': place['mapID'], 'minX': min(x for x,y in points), 'maxX': max(x for x,y in points),
            'minY': min(y for x,y in points), 'maxY': max(y for x,y in points)})
    return footprints


def collect(source):
    lua = LuaRuntime(unpack_returned_tuples=True)
    # Data files run in a namespace-only sandbox, without IO, network or game APIs.
    ns = lua.table_from({'RULESET': 'forever'})
    lua.execute('function register(_, _, values) names=values end')
    ns.RegisterLocale = lua.globals().register
    loader = lua.eval('function(text, ns) local env={ipairs=ipairs,pairs=pairs,table={insert=table.insert}}; local f=assert(loadstring(text)); setfenv(f,env); f("Mapzeroth",ns) end')
    names, hashes = {}, {}
    for name in FILES:
        path = source / 'Data/Forever' / name
        data = path.read_bytes()
        hashes[name] = hashlib.sha256(data).hexdigest()
        loader(data.decode(), ns)
        if name.startswith('Nodes_'):
            for line in data.decode().splitlines():
                match = re.search(r'id = "([^"]+)".*?},\s*--\s*([^\(]+)', line)
                if match:
                    names[match[1]] = match[2].strip()
    names.update({key[5:]: value for key, value in plain(lua.globals().names).items()})
    cities = plain(ns.Cities)
    city_maps = {city['mapID']: city['faction'] for city in cities.values() if city['mapID'] >= 1453 and city['mapID'] <= 1458}
    nodes = {}
    for group, values in plain(ns.Nodes).items():
        for node in values:
            if group == 'Pois' and node.get('kind') not in ('entrance', 'convergence'):
                continue
            if node['id'].startswith('TELEPORT_'):
                continue
            fields = {key: node[key] for key in ('mapID', 'x', 'y', 'container')}
            fields['name'] = names.get(node['id']) or (node.get('city', '').replace('_', ' ').title() + ' gate' if node.get('city') else node['id'].replace('_', ' ').title())
            faction = cities.get(node.get('city'), {}).get('faction') or city_maps.get(node['mapID'])
            if faction:
                fields['faction'] = faction
            if node.get('kind') == 'entrance':
                fields['name'] = node.get('city', 'City').replace('_', ' ').title() + ' gate'
            nodes[node['id']] = fields
    edges = []
    for origin, values in plain(ns.Geometry).items():
        if origin not in nodes:
            continue
        for target, cost, method in values:
            if target in nodes and method in ('walk', 'gate'):
                edges.append({'from': origin, 'to': target, 'method': 'walk', 'distance': cost})
    for edge in plain(ns.Edges):
        if edge['from'] not in nodes or edge['to'] not in nodes or edge['method'] not in ('walk', 'ship', 'zeppelin', 'tram', 'transition'):
            continue
        requirements = edge.get('requirements', {})
        if set(requirements) - {'faction'}:
            continue  # Restricted spells/race portals need separate tested capability gates.
        item = {key: edge[key] for key in ('from', 'to', 'method')}
        if 'cost' in edge:
            item['seconds'] = edge['cost'] + edge.get('loadingScreens', 0) * 10
        if requirements.get('faction'):
            item['faction'] = requirements['faction']
        edges.append(item)
        if not edge.get('oneway'):
            edges.append(dict(item, **{'from': item['to'], 'to': item['from']}))
    edges.sort(key=lambda edge: (edge['from'], edge['to'], edge['method'], edge.get('seconds', -1)))
    return nodes, edges, plain(ns.PathFactors), hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Local Mapzeroth checkout at the pinned Forever 0.6.0 commit.')
    parser.add_argument('--license-file', type=Path, required=True, help='MIT LICENSE published by the source repository.')
    args = parser.parse_args()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=args.source, text=True).strip()
    if commit != COMMIT:
        raise ValueError('Expected the reviewed Forever data revision ' + COMMIT)
    license_text = args.license_file.read_text()
    if not license_text.startswith('MIT License') or 'Copyright (c) 2026 tr0tsky0' not in license_text:
        raise ValueError('Expected the source project MIT notice')
    nodes, edges, factors, hashes = collect(args.source)
    settlements = settlement_facts(args.source / 'Data/Forever/Pois.lua', nodes)
    lines = ['local addonName, ns = ...', '', '-- Adapted geographic facts from Mapzeroth Forever 0.6.0 (MIT).',
             '-- See TRAVEL_DATA.md and THIRD_PARTY_NOTICES.md. Costs/coordinates need beta retesting.',
             '-- Geometry describes estimated walks between points, not collision-safe road polylines.',
             'ns.travelData = {', '    nodes = {']
    lines += ['        [' + encode(key) + '] = ' + encode(value) + ',' for key, value in sorted(nodes.items())]
    lines += ['    },', '    edges = {']
    lines += ['        ' + encode(edge) + ',' for edge in edges]
    lines += ['    },', '    factors = ' + encode(factors) + ',',
              '    settlements = ' + encode(settlements) + ',', '}','']
    (ROOT / 'WowTogether/TravelData.lua').write_text('\n'.join(lines))
    metadata = {'source': 'https://github.com/tr0tsky0/Mapzeroth', 'commit': commit, 'tag': '0.6.0',
                'files_sha256': hashes, 'nodes': len(nodes), 'directed_edges': len(edges),
                'license': 'MIT', 'license_revision': '676241e234cbeab5e2066b869b52c235d675a9e0',
                'settlement_footprints': len(settlements), 'settlement_margin_yards': 100,
                'exclusions': ['Retail data', 'service/action graph nodes', 'spells/items', 'race/class portals', 'unconfirmed flights'],
                'limitations': ['Community data, not tested here in the beta client', 'Walk geometry uses estimated point-to-point distances, not terrain navigation', 'Boat waits and loading time are estimates', 'Settlement footprints bound published occupied locations with an estimated margin, not actual guards or road bypasses']}
    (ROOT / 'WowTogether/TravelData.json').write_text(json.dumps(metadata, indent=2) + '\n')
    (ROOT / 'THIRD_PARTY_NOTICES.md').write_text('# Third-party notices\n\nGeographic travel facts adapted from [Mapzeroth](https://github.com/tr0tsky0/Mapzeroth),\nForever 0.6.0 (`' + commit + '`). Its addon engine/UI is not included.\nThe project publishes this license:\n\n```text\n' + license_text.rstrip() + '\n```\n')
    print(f'Generated {len(nodes)} travel points and {len(edges)} directed links.')


if __name__ == '__main__':
    main()
