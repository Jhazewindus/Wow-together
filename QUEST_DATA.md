# Quest data and guide audit

This is an expanded **partial** Forever dataset. A quest ID/name is not a
mapped quest, an NPC offer, or proof that a guide is optimal. The playing UI
uses simple instructions; source and coverage details belong here.

## Sources and precedence

1. Published Forever quest/entity records and reviewed tester corrections.
2. Licensed Forever NPC/travel geographic facts, at the reviewed MIT revision.
3. Older-world numeric/name fallbacks only for identity-matched unchanged quests.

The public category union contains 5,230 records from 123 leaf lists. The root
Wowhead list is truncated at 1,000 and is never treated as a complete index.
There are 1,885 captured Forever detail pages and 1,143 Warcraft DB detail records.
The latter add structured named objectives; they do not supply complete spawn maps.

Source access uses the environment proxy and verified TLS. Quest/entity capture
stops after access denials, keeps successful caches and records failed IDs. Raw
downloaded JavaScript and SQL are never executed. Quest prose/artwork and other
addon engines/UI are not bundled.

Static pickup / objective-area / hand-in coverage: **2,877 / 1,218 / 3,044** quests.
Named entity facts: **6,580 NPCs / 785 objects / 2,301 items**.

## Older-world fallback provenance

- Source: https://github.com/cmangos/classic-db/tree/ec4f596146be6467ea93c57397858e329e2db852
- File: `Full_DB/ClassicDB_1_12_1_z2815.sql.gz`.
- SHA256: `4f92db520868ab4e566726f68b5b2e380ae781209beaf22237b4f7f04600d0c0`.
- License: GPL-3.0; upstream license/copyright notice included. See THIRD_PARTY_NOTICES.md.
- Changes: select factual IDs, names, quantities, explicit relations and actual spawns;
  verify unchanged quest identity; annotate provenance; retain actual representative points.

A Forever `unchanged` label and identical ID, title, level and minimum level are
required: 3,544 quest identities match. Updated, new, unconfirmed and excluded
quests cannot borrow these quest fallback facts. Missing conditions/reputation
requirements remain uncertain. Positive explicit predecessors are used; arbitrary
neighboring IDs and negative/ambiguous relations never establish a chain.
Published beta/tester gates win. An actual beta NPC offer may contradict a
marked older-world prerequisite without weakening published beta/tester gates.

Static map transforms are fitted only with at least five broadly distributed
single-spawn published Forever NPC anchors, at least 80% inliers and <=0.8%
normalized residuals. Eleven maps pass; all other maps keep world coordinates.
A native C_Map conversion may fill those only after three published Forever
anchors confirm its world-axis convention. Missing/private/contradictory native
data leaves the gap visible. A valid transform proves the map convention, not
that an old NPC spawn, cave floor or quest mechanism survived beta changes.

Actual representative spawn points are selected; a centroid inside mountains
is never introduced. Drop/vendor joins require an explicit item-source relation.
Common-item sources above the quest level allowance are not selected as farming
targets; high-level friendly vendors can still sell a required item. Item goals
from a proven common mob may share its already-published farming area.
A proven drop source whose creature name matches the requested item is preferred
within the same farming zone. A name match never creates an unproven drop relation
or justifies travel to a remote zone. Published alternatives remain available.
Provided items are distinguished from farming goals. Item-use facts require
a matching explicit source mechanism, rather than assuming every NPC goal is a kill.

## Forever NPC geography

Read-only geographic rows from Mapzeroth Forever 0.6.0 (MIT), revision
`fd68cfe2153379898680c66a01833846f9933587`, file `Data/Forever/Pois.lua`.
SHA256: `3dfa6f85e6fbe1c5a01389d4bcf445f4fa63391484647cdec663a849111e977d`.
Only NPC IDs and normalized coordinates are read: 674 positions. The source
addon engine, UI and service logic are not copied. Full MIT notice is included.

## What the route audit establishes

The host audit checked **77 faction-specific zone guides** and **7,802 stored map points**.
It uses the actual Lua 5.1 compiler with native world conversion unavailable.
Checks cover finite map coordinates, excluded/repeatable quests, pickup/objective/
hand-in order, explicit prerequisites and non-increasing estimated route distance.
GuideAudit.json contains each guide, step count, remaining unknown steps and
distance before/after the bounded local search. Search preserves NPC hand-off
bundles and fixed order during play; it is not a globally optimal XP solution.

The checks do not certify actual beta APIs, NPC offers, secret-value behavior,
protected actions, map rendering, walkable terrain, cave entrances or travel times.
Lines show visiting order. A shortest line is not a safe road path; the travel
graph has transport/crossing facts and estimated walks, not a terrain navmesh.
Read TESTING.md for current beta validation and export labeled /wt findings.

## Remaining source work

Source denials still block many detailed quest and entity pages. The environment
draft already allows the required source domains; the running policy has not
activated those rules. Save/publish the draft in environment settings, then
recheck source access. A successful capture is required before marking gaps filled.
QuestCoverage.json includes denied IDs, per-zone missing quest IDs and entity
capture results. New/changed beta zones, including Zephras Isle, still need
additional NPC/mob/item positions and live prerequisite evidence.

Coordinate completeness below counts all source-category quests, before the
leveling guide filters. Capitals, classes, dungeons, professions and seasonal
quests may remain in the catalogue while excluded from normal zone leveling.
A complete-location row does not establish current pickup availability.

| Source zone/category | Quests | Pickups | Objective areas | Hand-ins | Complete locations |
| --- | ---: | ---: | ---: | ---: | ---: |
| eastern-kingdoms/alterac-mountains | 21 | 16 | 8 | 18 | 7 |
| eastern-kingdoms/alterac-valley | 3 | 3 | 0 | 3 | 0 |
| eastern-kingdoms/anvilmar | 1 | 1 | 1 | 1 | 0 |
| eastern-kingdoms/arathi-highlands | 54 | 50 | 28 | 50 | 32 |
| eastern-kingdoms/badlands | 44 | 42 | 25 | 43 | 29 |
| eastern-kingdoms/blackrock-mountain | 15 | 4 | 4 | 2 | 0 |
| eastern-kingdoms/blasted-lands | 26 | 26 | 17 | 25 | 22 |
| eastern-kingdoms/burning-steppes | 24 | 24 | 13 | 24 | 9 |
| eastern-kingdoms/deeprun-tram | 2 | 0 | 0 | 0 | 0 |
| eastern-kingdoms/dun-morogh | 60 | 56 | 29 | 60 | 39 |
| eastern-kingdoms/duskwood | 100 | 98 | 42 | 99 | 59 |
| eastern-kingdoms/eastern-plaguelands | 109 | 80 | 42 | 104 | 39 |
| eastern-kingdoms/elwynn-forest | 76 | 69 | 33 | 73 | 51 |
| eastern-kingdoms/hillsbrad-foothills | 56 | 56 | 32 | 56 | 32 |
| eastern-kingdoms/ironforge | 82 | 71 | 21 | 80 | 34 |
| eastern-kingdoms/kharanos | 1 | 1 | 0 | 1 | 1 |
| eastern-kingdoms/loch-modan | 47 | 38 | 18 | 38 | 18 |
| eastern-kingdoms/redridge-mountains | 43 | 31 | 14 | 32 | 13 |
| eastern-kingdoms/riverglades | 1 | 1 | 0 | 1 | 1 |
| eastern-kingdoms/searing-gorge | 31 | 28 | 19 | 30 | 19 |
| eastern-kingdoms/shadowfang-keep | 2 | 0 | 0 | 0 | 0 |
| eastern-kingdoms/silverpine-forest | 50 | 36 | 9 | 36 | 16 |
| eastern-kingdoms/stonewrought-dam | 1 | 1 | 0 | 1 | 1 |
| eastern-kingdoms/stormwind-city | 88 | 78 | 12 | 79 | 49 |
| eastern-kingdoms/stranglethorn-vale | 125 | 58 | 23 | 63 | 25 |
| eastern-kingdoms/swamp-of-sorrows | 28 | 23 | 14 | 21 | 16 |
| eastern-kingdoms/the-hinterlands | 45 | 44 | 24 | 44 | 27 |
| eastern-kingdoms/thoradins-wall | 1 | 1 | 0 | 1 | 1 |
| eastern-kingdoms/tirisfal-glades | 66 | 36 | 25 | 37 | 22 |
| eastern-kingdoms/undercity | 32 | 26 | 12 | 26 | 11 |
| eastern-kingdoms/western-plaguelands | 92 | 63 | 30 | 62 | 32 |
| eastern-kingdoms/westfall | 54 | 32 | 19 | 32 | 15 |
| eastern-kingdoms/wetlands | 66 | 43 | 20 | 43 | 34 |
| kalimdor/abyssal-sands | 1 | 0 | 0 | 0 | 0 |
| kalimdor/ashenvale | 82 | 69 | 34 | 70 | 52 |
| kalimdor/azshara | 45 | 5 | 1 | 6 | 1 |
| kalimdor/blackmaw-hold | 7 | 7 | 4 | 7 | 4 |
| kalimdor/darkshore | 80 | 60 | 31 | 62 | 34 |
| kalimdor/darnassus | 27 | 26 | 8 | 26 | 19 |
| kalimdor/desolace | 76 | 41 | 22 | 41 | 24 |
| kalimdor/durotar | 65 | 55 | 32 | 60 | 37 |
| kalimdor/dustwallow-marsh | 69 | 50 | 20 | 49 | 33 |
| kalimdor/felwood | 87 | 82 | 31 | 83 | 34 |
| kalimdor/feralas | 78 | 47 | 19 | 48 | 25 |
| kalimdor/field-of-giants | 1 | 1 | 0 | 1 | 1 |
| kalimdor/moonglade | 8 | 8 | 1 | 8 | 3 |
| kalimdor/mulgore | 61 | 27 | 14 | 29 | 16 |
| kalimdor/orgrimmar | 92 | 68 | 22 | 81 | 31 |
| kalimdor/ruttheran-village | 4 | 4 | 2 | 4 | 4 |
| kalimdor/shendralas | 3 | 0 | 1 | 0 | 0 |
| kalimdor/silithus | 126 | 32 | 34 | 64 | 24 |
| kalimdor/stonetalon-mountains | 52 | 42 | 27 | 42 | 33 |
| kalimdor/tanaris | 94 | 67 | 24 | 66 | 21 |
| kalimdor/teldrassil | 62 | 44 | 22 | 47 | 29 |
| kalimdor/the-barrens | 116 | 114 | 73 | 114 | 84 |
| kalimdor/thousand-needles | 71 | 35 | 18 | 40 | 17 |
| kalimdor/thunder-bluff | 36 | 29 | 14 | 26 | 13 |
| kalimdor/ungoro-crater | 53 | 34 | 20 | 35 | 15 |
| kalimdor/winterspring | 57 | 34 | 19 | 36 | 18 |
| map:2521 / Published zone 16593 | 9 | 0 | 0 | 0 | 0 |
| map:2521 / Zephras Isle | 107 | 0 | 0 | 0 | 0 |

## Reproduce capture, build and audit

Use `/workspace/.wow-together-tests/bin/python` (Python with pinned Lupa 2.8).
Run these from the development repository, not the installed AddOns folder.
Source caches are development inputs outside the addon. Keep the reviewed
older-world snapshot and Mapzeroth data checkout at their pinned revisions.
The archive includes editable catalogue Lua, import/build scripts and notices.

```sh
python3 tools/import_warcraftdb.py
python3 tools/import_wowhead.py --all-categories --spread-details
/workspace/.wow-together-tests/bin/python tools/collect_quest_entities.py \
  --from-catalogue WowTogether/QuestCatalogue.lua
/workspace/.wow-together-tests/bin/python tools/build_quest_dataset.py \
  --legacy-snapshot /tmp/wow-together-classic-facts/source/Full_DB/ClassicDB_1_12_1_z2815.sql.gz \
  --forever-pois /tmp/wow-together-mapzeroth-source/Data/Forever/Pois.lua
/workspace/.wow-together-tests/bin/python tools/audit_quest_guides.py
/workspace/.wow-together-tests/bin/python -m unittest discover -s tests -q
```

Capture commands may need configured source access; do not loop unchanged
denials. After a meaningful access change, the entity capture tool supports
`--access-changed` to recheck stored 403s and still stops on renewed denials.
The dataset builder performs no network requests. It regenerates from source
caches instead of accumulating stale fallback facts from yesterday's output.
Run it twice with unchanged inputs and compare output checksums.
