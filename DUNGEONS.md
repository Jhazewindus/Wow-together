# Combined dungeon data — updated for 0.8.33

All **19 Classic dungeon complexes** have published entrance areas. The supplied
Wowhead overview contains **25 Classic range/wing rows**; Scarlet Monastery,
Maraudon and Blackrock Spire are kept as families with their wing ranges. All
nine new Forever dungeons are listed; four have published entrance areas and
five have broad location descriptions without usable coordinates or quest sets.

The 23 bounded Forever dungeon category pages supply 339 quest memberships.
Every captured member already exists in the 5,230-quest catalogue. Runtime also
recognizes explicit matching dungeon area/name facts, folding the formerly
separate Lordaeron label together. A generic Dungeon tag alone does not create
Mage, Orgrimmar or raid cards. Unassigned tagged quests remain in All quests;
no membership is guessed from mob/item names or an NPC's pickup zone.

## Sources and reconciliation

- [Wowhead Forever overview](https://www.wowhead.com/forever/guide/dungeons-overview-locations-details),
  captured October 6, 2026. Only short dungeon names and numeric ranges are used.
- All 23 published `https://www.wowhead.com/forever/quests/dungeons/<category>`
  lists, captured on the same date. IDs are merged without changing quest facts.
- [Mapzeroth Forever geographic facts](https://github.com/tr0tsky0/Mapzeroth/blob/fd68cfe2153379898680c66a01833846f9933587/Data/Forever/Pois.lua),
  pinned revision `fd68cfe2153379898680c66a01833846f9933587` (MIT).
  Only the 23 non-raid `instance` point records are selected. No upstream
  engine, route logic, UI, guide prose, screenshots or artwork are included.

`WowTogether/DungeonData.json` keeps all source URLs, SHA256 hashes, fields,
quest memberships and remaining gaps. Its overview SHA256 is
`47ccd5577125fbe48321d7ba87da10baa72c2e3b27d89466499881528c79a744`;
its entrance-source SHA256 is
`3dfa6f85e6fbe1c5a01389d4bcf445f4fa63391484647cdec663a849111e977d`.
The source's MIT notice is retained in THIRD_PARTY_NOTICES.md.

The overview's chart/table disagrees with its paragraphs for City of Dalaran
(28–33 versus 20–35) and Krol'dok Stronghold (40–45 versus 40–55). Use the
consistent chart/table ranges as run recommendations, with the conflict retained
in the metadata. These ranges are neither minimum entry levels nor quest pickup
requirements. Collection popups still use the highest relevant known quest
minimum for this character; faction, race, class, repeatable/profession filters,
prerequisites, actual offers and saved skips remain independent.

## Entrance behavior

Use a valid personal recording first, a matching public client map link second,
and the published entrance area third. Native matching includes canonical name
aliases and checks the published destination map even while the player is away.
Private/unavailable/invalid native points cannot overwrite published facts.
Recordings are per character; shipped facts are never mutated by recording.

Start route collects suitable dungeon quests across zones and any required
prerequisite chains, then visits the entrance. Accepted quests count as collected;
unknown offers/locations remain pending. Dijkstra travel costs help order the
preparation; normal updates preserve that itinerary. No quest credit is inferred
from arrival. Individual Route to pickup still ends on accepting that quest.

From 0.8.33, entering the matching dungeon retains the guide in its run phase.
Wait for the quests' real objective progress. Once all remaining goals are ready,
or when leaving with some ready, switch to hand-in visits for those quests only,
using their published or native return destinations. A later ready quest joins
the remaining hand-ins; unfinished or unmapped returns stay pending. Turn-ins
are ordered by known travel costs without claiming a global optimum. The guide
finishes after confirmed turn-ins. It does not supply an interior dungeon route.
Run/return phase and original goal set persist through Scan and reload; new
pickups cannot silently expand that run. Manual skips and identity gates remain.

Points identify **entrance areas**, not guaranteed exact portal coordinates.
Cave passages and mountain interior paths still need current beta observations.
There is no terrain mesh, new road data or guessed portal location in this merge.
Saved recordings and public native links can refine these published areas.

## Coverage

Map IDs below are Forever UI map IDs, not area IDs. Coordinates are percentages.

| Dungeon complex | Run levels | Published entrance area |
| --- | --- | --- |
| Ragefire Chasm | 13–18 | Map 1454 — 52.8, 48.9 |
| Hall of Thanes | 13–18 | Map 1455 — 15.2, 85.7 |
| Ruins of Lordaeron | 15–20 | Map 1458 — 64.8, 35.7 |
| Wailing Caverns | 15–25 | Map 1413 — 47.7, 35.0 |
| The Deadmines | 18–23 | Map 1436 — 38.2, 77.5 |
| Shadowfang Keep | 22–30 | Map 1421 — 44.7, 67.8 |
| The Stockade | 22–30 | Map 1453 — 58.7, 75.8 |
| Blackfathom Deeps | 24–32 | Map 1439 — 33.5, 93.5 |
| Excavation Site: Wetlands | 24–29 | Map 1437 — 38.5, 60.6 |
| City of Dalaran | 28–33 | Map 1416 — 16.6, 68.8 |
| Scarlet Monastery | 28–45 | Map 1420 — 85.0, 31.4 |
| Gnomeregan | 29–38 | Map 1426 — 17.7, 39.2 |
| Razorfen Kraul | 30–40 | Map 1413 — 42.3, 89.9 |
| The Drowned City | 35–40 | Unknown — Stranglethorn coast |
| Krol'dok Stronghold | 40–45 | Unknown — Riverglades |
| Razorfen Downs | 40–50 | Map 1413 — 50.9, 92.9 |
| Uldaman | 42–52 | Map 1432 — 34.8, 85.5 |
| Zul'Farrak | 44–54 | Map 1446 — 38.7, 19.9 |
| Maraudon | 45–57 | Map 1443 — 29.1, 62.9 |
| Alcaz Prison | 48–53 | Unknown — Alcaz Island, Dustwallow Marsh |
| Sunken Temple | 50–60 | Map 1435 — 77.3, 35.9 |
| Blackrock Depths | 52–60 | Map 1427 — 27.1, 72.5 |
| Blackmaw Hold | 55–60 | Unknown — Northern Azshara |
| Blackrock Spire | 55–60 | Map 1428 — 33.0, 25.2 |
| Dire Maul | 58–60 | Map 1444 — 62.0, 33.3 |
| Scholomance | 58–60 | Map 1422 — 69.0, 73.0 |
| Shaper's Terrace | 58–60 | Unknown — Un'Goro Crater |
| Stratholme | 58–60 | Map 1423 — 26.0, 10.5 |

## Reproduce the offline merge

Use captured inputs; the importer does not fetch pages or evaluate source scripts:

```sh
/workspace/.wow-together-tests/bin/python tools/import_dungeons.py \
  --overview /tmp/wow-together-dungeons-overview.html \
  --pois /tmp/forever-pois.lua \
  --quest-cache /tmp/wow-together-dungeon-quests
```

The importer rejects incomplete range coverage, truncated lists, invalid points,
unreviewed dungeon names and a mismatched pinned geography hash. Runtime data
is editable Lua with the standard addon namespace; load order stays in the TOC.
