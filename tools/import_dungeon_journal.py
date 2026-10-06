"""Import audited Vanilla and Forever dungeon facts; never execute scripts.

Artwork is referenced by verified client filenames, never copied into the addon.
Classic dungeons use reviewed original Vanilla encounter identities. The audit
requires complete captured Vanilla loot tables and separates encounter ownership
from shared/world drops. Explicit Forever additions retain their provenance.
"""
import json
import re

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
    # The legacy boss-flag-only path mixed SoD identities and random drops.
    # Rebuilding now requires the complete audited Vanilla capture instead.
    from audit_dungeon_loot import main as audited_main
    audited_main()

if __name__ == '__main__':
    main()
