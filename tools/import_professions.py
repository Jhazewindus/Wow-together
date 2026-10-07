"""Import public recipe/rank/trainer facts, never another site's guide sequence.

Inputs are saved pages. No scripts execute and no images or editorial passages
are bundled. Live client facts take precedence over this beta reference.
"""
import argparse
import hashlib
import json
import re
from html import unescape
from pathlib import Path

from pack_data import Packer
from import_travel_network import encode

ROOT = Path(__file__).resolve().parents[1]
PROFESSIONS = {'alchemy': (171, 'Alchemy'), 'blacksmithing': (164, 'Blacksmithing'),
    'enchanting': (333, 'Enchanting'), 'engineering': (202, 'Engineering'),
    'leatherworking': (165, 'Leatherworking'), 'tailoring': (197, 'Tailoring')}


def plain(text):
    return ' '.join(unescape(re.sub('<[^>]+>', ' ', text)).split())


def recipe_table(html):
    chunks = ''.join(json.loads(m.group(1)) for m in re.finditer(
        r'\.rsc\.push\(("(?:\\.|[^"\\])*")\)', html))
    found = []
    def visit(value):
        if isinstance(value, dict):
            if isinstance(value.get('rows'), list) and value['rows'] and 'spell' in value['rows'][0]:
                found.append(value)
            for child in value.values(): visit(child)
        elif isinstance(value, list):
            for child in value: visit(child)
    for line in chunks.splitlines():
        try: value = json.loads(line.partition(':')[2])
        except ValueError: continue
        visit(value)
    if len(found) != 1: raise ValueError('Expected one complete recipe fact table')
    return found[0]


def trainers(html):
    headings = [(m.start(), plain(m.group())) for m in re.finditer(r'<h[234][^>]*>.*?</h[234]>', html, re.S)]
    places = {}
    ranks = []
    for row in re.finditer(r'<tr[^>]*>.*?</tr>', html, re.S):
        cells = [plain(c) for c in re.findall(r'<td[^>]*>(.*?)</td>', row.group(), re.S)]
        if len(cells) == 4 and cells[0] in ('Apprentice', 'Journeyman', 'Expert', 'Artisan'):
            numbers = [int(c) if c.isdigit() else 0 for c in cells[1:]]
            ranks.append(dict(name=cells[0], maximum=numbers[0], skill=numbers[1], level=numbers[2]))
        match = re.search(r'/mappin\s+(\d+)\s+([\d.]+)\s+([\d.]+)', row.group())
        if not match or len(cells) < 3: continue
        heading = next((h for pos, h in reversed(headings) if pos < row.start()), '')
        band = re.fullmatch(r'(\d+)-(\d+): (Alliance|Horde)', heading)
        if not band: raise ValueError('Trainer rank/faction heading missing')
        map_id, x, y = int(match[1]), float(match[2])/100, float(match[3])/100
        key = (cells[0], map_id, x, y, int(band[2]))
        if key in places: places[key]['faction'] = 'Both'
        else: places[key] = dict(name=cells[0], hub=cells[1], mapID=map_id, x=x, y=y,
            maximum=int(band[2]), faction=band[3], dungeon='Inside ' in cells[1])
    if len(ranks) != 4 or not places: raise ValueError('Incomplete trainer/rank facts')
    return ranks, list(places.values())


def generate(cache):
    professions, sources = {}, []
    for slug, (ident, name) in PROFESSIONS.items():
        paths = [cache / ('facts-'+slug+'.html'), cache / ('icy-'+slug+'.html')]
        urls = ['https://classicwowforever.com/professions/'+slug+'/recipes/', 'https://www.icy-veins.com/wow-forever/'+slug]
        for path, url in zip(paths, urls):
            sources.append(dict(url=url, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        table = recipe_table(paths[0].read_text())
        ranks, places = trainers(paths[1].read_text())
        recipes, item_ids = [], set()
        for row in table['rows']:
            recipe = dict(id=row['spell'], name=row['name'], materials=row['mats'], source=row['source'])
            for key in ('learn', 'yellow', 'green', 'grey'):
                if isinstance(row.get(key), int): recipe[key] = row[key]
            if isinstance(row.get('itemId'), int): recipe['outputID'] = row['itemId']
            makes = re.search(r'makes (\d+)', row.get('item', ''))
            recipe['outputQuantity'] = int(makes[1]) if makes else 1
            if str(row.get('faction', '')).lower() in ('horde', 'alliance'):
                recipe['faction'] = row['faction'].capitalize()
            recipe['icon'] = 'Interface\\Icons\\'+row['icon']
            fee = re.match(r'Trainer, ((?:\d+[gsc]\s*)+)', row.get('how', ''))
            if fee: recipe['trainingCost'] = sum(int(n)*{'g':10000,'s':100,'c':1}[u] for n,u in re.findall(r'(\d+)([gsc])', fee[1]))
            recipes.append(recipe)
            item_ids.update(item[0] for item in row['mats'])
        items = {int(k): {'name':v['n'], 'icon':'Interface\\Icons\\'+v['i']} for k,v in table['items'].items() if int(k) in item_ids}
        professions[ident] = dict(id=ident, name=name, slug=slug, recipes=recipes, items=items, ranks=ranks, trainers=places,
            icon='Interface\\Icons\\Trade_'+{'alchemy':'Alchemy','blacksmithing':'BlackSmithing','enchanting':'Engraving',
                'engineering':'Engineering','leatherworking':'LeatherWorking','tailoring':'Tailoring'}[slug])
    data = dict(schema=1, captured='2026-10-07', professions=professions, sources=sources)
    packer = Packer()
    body = 'ns.professionGuideData = {schema=1,captured="2026-10-07"}\n'
    body += packer.records('crafting-professions', 'ns.professionGuideData.professions', professions)
    (ROOT/'WowTogether/ProfessionData.lua').write_text(packer.code(body, 'Public Forever recipe/trainer facts; see PROFESSIONS.md. No source guide ordering or prose.'))
    (ROOT/'WowTogether/ProfessionData.json').write_text(json.dumps(data, indent=2)+'\n')
    print(f'{sum(len(p["recipes"]) for p in professions.values())} recipes; {sum(len(p["trainers"]) for p in professions.values())} trainer locations; {len(professions)} crafting professions')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=Path('/tmp/wow-together-professions'))
    generate(parser.parse_args().cache)
