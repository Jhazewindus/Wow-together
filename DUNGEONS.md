# Combined dungeon data — updated for 0.8.96

All **19 Classic dungeon complexes** have published entrance areas. The supplied
Wowhead overview contains **25 Classic range/wing rows**; Scarlet Monastery,
Maraudon and Blackrock Spire are kept as families with their wing ranges. All
nine new Forever dungeons are listed; four have published entrance areas and
five have broad location descriptions without usable coordinates. Two of those
five now have named quest lists; the other three remain unknown.

Current Wowhead Forever lists provide 26 named dungeon categories, captured
November 8, 2026. The Drowned City (8 quests), Krol'dok Stronghold (13), and
now Alcaz Prison (4) have dedicated lists. Two category URLs still return a
generic global quest page, so Blackmaw Hold and Shaper's Terrace retain unknown
quest sets. Current Method.gg tables supplement the named lists with seven
City of Dalaran quests and The Treaty of Understanding (98423) for Hall of
Thanes. After excluding two category rows explicitly marked `<UNUSED>`, the
finder has 380 static memberships, all present in the 5,337-quest catalogue.
Runtime also recognizes two verified matching-area quests, for 382 audited
memberships. These lists do not establish that every live quest is categorized.

Research now follows the user's requested level progression: City of Dalaran
(28–33), Razorfen Kraul (30–40), Scarlet Monastery (28–45), then The Drowned
City (35–40). This is the order for coverage work, not a mandatory player
route. Alcaz Prison (48–53) is treated as a later-game follow-up. The level
bands overlap, so they describe relative audit priority rather than a strict
unlock sequence. The live data already links Horde Hearts of Zeal (1113) to
Going, Going, Guano! (1109): its generated prep route picks up the prerequisite,
travels to Razorfen Kraul, returns to turn it in, then resumes at the Scarlet
quest giver. A regression test protects that cross-dungeon chain.
The Method tables for Ruins of Lordaeron and Excavation Site: Wetlands add no
new IDs beyond Wowhead's lists. The overview's 28 ranges and the other quest
facts are unchanged. Runtime also
recognizes explicit matching dungeon area/name facts, folding the formerly
separate Lordaeron label together. A generic Dungeon tag alone does not create
Mage, Orgrimmar or raid cards. Unassigned tagged quests remain in All quests;
no membership is guessed from mob/item names or an NPC's pickup zone.

## Sources and reconciliation

- [Wowhead Forever overview](https://www.wowhead.com/forever/guide/dungeons-overview-locations-details),
  captured November 5, 2026. Only short dungeon names and numeric ranges are used.
- All 28 current `https://www.wowhead.com/forever/quests/dungeons/<category>`
  URLs, captured November 8, 2026. Twenty-six return named categories; two
  return the generic global quest list and are not used to infer memberships.
  Two rows explicitly marked `<UNUSED>` are excluded. Current detail pages,
  series tables and relevant comments were checked for the dungeon quests; the
  capture hashes, reviewed links and inaccessible pages are in
  `research/dungeon-prerequisite-audit-2026-11-07/audit.json`; the refreshed
  Alcaz list and four detail-page hashes are in `tools/dungeon_quest_additions.json`.
- [Mapzeroth Forever geographic facts](https://github.com/tr0tsky0/Mapzeroth/blob/fd68cfe2153379898680c66a01833846f9933587/Data/Forever/Pois.lua),
  pinned revision `fd68cfe2153379898680c66a01833846f9933587` (MIT).
  Only the 23 non-raid `instance` point records are selected. No upstream
  engine, route logic, UI, guide prose, screenshots or artwork are included.
- [Method.gg dungeon guides](https://www.method.gg/wow-forever/dungeons),
  checked November 6, 2026. The index lists all nine newer Forever dungeons,
  while only City of Dalaran, Excavation Site: Wetlands, Hall of Thanes and
  Ruins of Lordaeron have dedicated guide pages. Their explicit quest tables
  are merged as supplemental memberships; the seven City and one Hall IDs are
  absent from their Wowhead category captures. Guide range labels
  differ from the Wowhead chart for the four available pages; current finder
  recommendations retain the Wowhead chart ranges. No site code, guide prose,
  images or map artwork are included.

`WowTogether/DungeonData.json` keeps all source URLs, SHA256 hashes, fields,
quest memberships and remaining gaps. Its overview SHA256 is
`a5beae895fb35c88d3c854ff364f89c611879086b1c606a6c70797d83a5275f5`;
its entrance-source SHA256 is
`3dfa6f85e6fbe1c5a01389d4bcf445f4fa63391484647cdec663a849111e977d`.
The source's MIT notice is retained in THIRD_PARTY_NOTICES.md.

The overview's chart/table disagrees with its paragraphs for City of Dalaran
(28–33 versus 20–35) and Krol'dok Stronghold (40–45 versus 40–55). Method.gg's
guide ranges for Hall of Thanes, Ruins of Lordaeron, Wetlands and City of
Dalaran also differ from the Wowhead chart (13–20 vs 13–18, 15–22 vs 15–20,
26–33 vs 24–29, and 28–35 vs 28–33 respectively). Use Wowhead's consistent
chart/table ranges as run recommendations, with source conflicts documented. These ranges are neither minimum entry levels nor quest pickup
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

The all-dungeon prerequisite review uses current QuestieDB facts, Wowhead
series, and relevant player comments. It corrects the hidden Rig Wars offer
gate before Chief Engineer Scooty, and removes the false 6562 → 6563 edge:
current comments identify Trouble in the Deeps and The Essence of Aku'Mai as
breadcrumbs rather than required prerequisites. The Lordaeron Unending Torment
chain now includes its current QuestieDB links through 97292. Known limitations
remain explicit: 17 detail pages were denied, the prerequisite for quest 7507
could not be read, and comments conflict or omit the quest ID for gates on 2846
and 95682. Newly listed quests lack pickup/objective coordinates, and two
outdoor prerequisite records lack published pickup/turn-in map points. A
comment-supported pickup for 97130 is routed to Archmage Timear in Dalaran.

The current Forever pages still show no preceding quest for either faction's
The Heart of the Void quest. They do not identify its starter item or pickup
point, so dungeon preparation leaves collection deferred and directs the player
to the run.

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

## Progression-ordered refresh (November 8, 2026)

The current audit sequence follows the supplied level brackets and the
cross-dungeon quest dependency: Dalaran → Razorfen Kraul → Scarlet Monastery
Graveyard/Library → The Drowned City. Scarlet's published complex bracket is
28–45, but the relevant RFK-to-Scarlet chain starts at level 30. The Drowned
City's 35–40 bracket follows those checks in the requested review order. Alcaz
Prison at 48–53 is late-game coverage and is recorded separately.

The refreshed Alcaz category has four named quests: 96335, 96337, 96377 and
96772. Current individual pages disclose some item/object requirements but do
not establish pickup/turn-in map points or trustworthy prerequisite chains;
the catalogue therefore exposes the quests while keeping them out of a falsely
complete guided route. The category capture and each page hash are recorded in
`tools/dungeon_quest_additions.json`.

The November 8 refresh of the eight Drowned City pages improved seven existing
records (95775, 95776, 95787, 95788, 95789, 95791 and 97130): it adds or confirms
three pickup points, three turn-in points, NPC/item facts and the exact tablet
item IDs. No objective coordinates, Drowned City entrance point, or new chain
link was established. The current source captures and hashes are recorded in
`research/dungeon-progression-audit-2026-11-08.json`. QuestieDB at
`aa1d7e7294596cf50a6fd0946dfae0d969cb9623` added no new dungeon quest records
beyond this reviewed catalogue; its chain facts confirm the 1109 → 1113 link.

As of this refresh, 380 static quest memberships are in the finder and two
additional area-matched quests are included in the runtime prerequisite audit
(382 total). Five of 28 dungeon entrance areas remain unknown, Blackmaw Hold
and Shaper's Terrace still have no named quest list, and 27 listed quest
memberships have unverified prerequisite research. These are visible work items,
not gaps to fill with guessed paths. See
`research/dungeon-prerequisite-level-audit-2026-11-08.json`.

## Reproduce the offline merge

Use captured inputs; the importer does not fetch pages or evaluate source scripts:

```sh
/workspace/.wow-together-tests/bin/python tools/import_dungeons.py \
  --overview /tmp/wow-together-dungeons-overview.html \
  --pois /tmp/forever-pois.lua \
  --quest-cache /tmp/wow-together-dungeon-quests \
  --captured 2026-11-08
```

The importer rejects incomplete range coverage, truncated lists, invalid points,
unreviewed dungeon names and a mismatched pinned geography hash. Runtime data
is editable Lua with the standard addon namespace; load order stays in the TOC.
