# Quest data and guide audit

This is an expanded **partial** Forever dataset. A quest name is not a mapped
quest, a confirmed NPC offer or proof of an optimal guide. The playing UI keeps
simple instructions; source evidence and remaining gaps are recorded here.

## Review one zone at a time

Run the same source-point, prerequisite ordering, objective-stage and route-flow
invariants for a single exact zone name, without replacing the full audit:

```sh
/workspace/.wow-together-tests/bin/python tools/audit_quest_guides.py --zone "Dun Morogh" --output /tmp/dun-morogh-audit.json
```

The scoped report counts only catalogue records whose `zone` matches. Every
discoverable faction/chapter of that zone is compiled normally, including its
cross-zone destinations and prerequisite dependencies. An unknown zone fails;
a scoped run requires a separate output path. Omit `--zone` for the existing
full-catalogue audit. Add `--require-complete` to return exit status 2 when source
gaps remain, even when every invariant passes; the report is still written.

The [8 October Dun Morogh review](research/2026-10-08-dun-morogh-review.json)
retains selected facts, immutable source URLs/hashes and the evidence still
needed for quests 282, 95217 and 98423. Both chapters pass their invariants:
151 actions at levels 1–10 and 30 at levels 11–20, with 164 static points checked.
Both chapters remain incomplete. Published facts confirm the existing Senir
chain, Quarry item quantities/boar point and Treaty item starter; they do not
establish the unresolved pickup conditions, a local Copper Bar objective point,
or the Treaty pickup location. This review makes no shipped-data or routing
change and does not certify live beta behavior.

The [8 October Durotar review](research/durotar-2026-10-08/README.md) covers
103 quest IDs across both chapters. Six supported stage corrections close five
objective-location gaps, retaining all 354 audited actions. Four objective gaps
and 16 unverified pickup requirements remain. The full-route comparison exposes
reward-timing and uncertain-travel tradeoffs in the unchanged shared compiler;
the changes remain a review draft pending main-developer coordination. Evidence,
exact comparison results and the native-beta player checklist accompany the review.

The [8 October Mulgore review](research/mulgore-2026-10-08/README.md) adds three
published prerequisite links and reconciles Baine/Mull pickup and hand-in
locations in eight quest records. It retains actual-offer confirmation and all
existing gap flags. Separate Tauren captures add the race-specific continuations
omitted by the first-discovered audit template: 74 distinct quests across three
chapters. The review records route tradeoffs and the shared builder's suppression
of The Broodmother's single-quest chapter, both requiring main-developer review.

## Captured facts and source precedence

The 0.8.59 correction adds **Treacherous Cold (99162) → Rime's Wrath (99161)**
from the supplied 0.8.42/build-70245 Dun Morogh tester report. The report identifies
the missing prerequisite; the uploaded probe supplies level-7 Alliance dwarf
context but is not a complete before/after NPC observation. Retain this as tester
provenance in `tools/quest_corrections.json`, not a verified web-source fact.
The same identity-checked correction is reapplied by future dataset builds.
Complete and hand in the prerequisite before the follow-up pickup; no location,
race/class mask or other quest fact changed. This adds one recorded prerequisite,
bringing the catalogue total to 2,466.
The corrected full Dun Morogh 1–10 compilation retains all 151 actions and places
the prerequisite's turn-in before the follow-up pickup. The source/invariant
audit checks all 152 sections; source mapping completeness does not change.

1. Current Forever quest/entity pages and reviewed tester corrections.
2. Explicit public Forever beta delta, observation and reviewed factual fields.
3. Identity-matched published converted-baseline facts; separately attributed
   older-world fallbacks only for strictly unchanged quest identities.
4. Explicit, consistent community ID/zone/coordinate observations for otherwise
   unmapped ground items. Published entity positions take precedence.

The category union contains **5,230 quests from 123 leaf lists**. The
Wowhead root list is truncated at 1,000 and is never treated as a complete index.
There are **2,232 captured Forever detail pages** and 1,143 Warcraft
DB detail records. Static pickup / objective-area / hand-in coverage is
**4,281 / 2,151 / 4,449 quests**.
Runtime named entities: **13,340 NPCs / 6,981 objects /
3,129 quest-used items**. Unrelated item loot tables are omitted.

Source capture uses normal proxy routing and verified TLS. Individual failed
IDs remain excluded; renewed denials stop a batch. Successful captures remain
cached. Downloaded JavaScript, Lua providers and SQL are never executed.
No source engine, UI, quest prose, artwork or comment prose is bundled.

## 7 October supplemental captures

A normal HTTPS batch captured **231 additional page snapshots** before later
requests were denied. The offline supplement fills **5 pickup points, 1 objective
area and 5 hand-in points**, plus missing item requirements and short NPC
references. These snapshots may overlap older captures, so they are not simply
added to the distinct detailed-page count. Each source URL/hash is retained in
QuestCoverage.json; existing mapped coordinates/actions, identity masks and
reviewed prerequisites take precedence. No downloaded script or quest prose is
executed/copied. The expanded chapter audit tracks 470 remaining records rather
than the former full-zone queue of 405; this is a wider audit scope.

Reproduce against the 0.8.41 source files and the captured HTML directory:

```text
/workspace/.wow-together-tests/bin/python tools/supplement_quest_data.py --directory <baseline-WowTogether> --cache <captured-pages> --output <candidate-directory>
```

Capture and full rebuilding remain separate from this additive tool. It cannot
fill facts a page does not publish or certify live NPC availability. Larger
same-hub pickup/turn-in bundles are allowed only in new fixed compilations when
all points are within 150 yards, levels are close and dependency/order checks
pass. Existing running guide order stays saved. Distance scores are estimates.

## Published Forever database facts

Source: https://github.com/Questie/QuestieDB/tree/e0a6eaa86f181ac99262e34126bcd2ed1a1712d6

`tools/forever_source_manifest.json` pins the selected factual files and hashes.
Our literal-only parser reads raw entity fields, inherited literal corrections,
beta deltas, trace observations and reviewed literal corrections in source
precedence order. It does not execute static/dynamic providers, function calls
or arbitrary expressions. Assumed fields and unsupported expressions remain
withheld. Short names, typed objective IDs, numeric counts, masks, explicit
relations and actual representative points are selected.

The importer also selects **484 explicit NPC patrol paths** as ordered points.
Multiple spawn positions never imply a patrol. Removed/unresolved patrol fields
remain absent; converted paths in known changed map frames are withheld. The map
shows a bounded thin amber search trace for upcoming givers, not a live location.

Converted baseline fields require agreeing quest title, level and minimum
level. Explicit beta field updates are distinguished from the baseline.
Current source masks, including an explicit unrestricted mask, take precedence
for unchanged inherited fields. High Skyborne race bits are represented as
explicit race IDs, without 32-bit truncation. AND and OR prerequisites retain
their distinct meanings. Conditions not modeled by the addon remain unknown
until the actual NPC offer confirms availability.

Typed beta facts correct **488 quest objective records**. Healing groups
produce one credit goal with alternate targets, rather than individual kills.
Provided items stay out of farming goals. Event areas and item-use instructions
require explicit locations/mechanisms. Unknown counts are never defaulted to one.
Escort work stays adjacent to acceptance, preserving its event sequence.

## Map geometry and older-world facts

Published geometry comes from the pinned Forever conversion report, targeting
DBC **1.60.1.69893**. Its SHA256 is
`0229566017126c2577e77d2bcc7c9f995648fb27ed32a7918fa44ace0664fb22`.
The parser verifies target snapshots, coverage, build, map IDs and finite bounds.
**46 outdoor/capital views** have supported rectangles; instance/battleground
and unsupported world views are not turned into outdoor quest positions.
Converted percentages preserve source world position, not proof of a current
spawn or a terrain-safe road. This geometry still needs current-beta validation.

Older-world source:
https://github.com/cmangos/classic-db/tree/ec4f596146be6467ea93c57397858e329e2db852

- File: `Full_DB/ClassicDB_1_12_1_z2815.sql.gz`.
- SHA256: `4f92db520868ab4e566726f68b5b2e380ae781209beaf22237b4f7f04600d0c0`.
- GPL-3.0 license/copyright notices are included; see THIRD_PARTY_NOTICES.md.
- **3,544** strictly unchanged ID/title/level/minimum-level quest identities match.
  New, updated and unconfirmed quests cannot borrow these old quest core facts.
  Published beta/tester gates win. Actual offers can contradict marked older gates.

Separate empirical fits require at least five broadly distributed single-spawn
published Forever anchors, at least 80% inliers and <=0.8% residuals.
**13 maps** pass. Converted/older anchors cannot validate themselves.
Remaining world positions can use guarded native conversion only after three
published Forever anchors agree. Missing or contradictory native data stays unknown.

Actual spawn representatives are retained; no centroid inside mountains is
invented. Drop/vendor joins require explicit relations. A matching item/mob name
does not create a loot relation or justify a remote farming detour. Two item
goals from a proven common source may share a farming area. No beta drop rate
is inferred from the old database.

## Additional geography and observed ground items

Warcraft DB's native quest-map fields fill **5 missing stages on 3 quests**:
two well-sampling areas in Westfall and three class-quest pickup/hand-in points.
Only known native map IDs, finite normalized coordinates and exact objective
IDs/counts are accepted. Original objective indexes survive filtering supplied
items. Existing destinations win; area polygons retain a published point,
not an inferred spawn or centroid. Source quest IDs and SHA256 hashes of
canonical JSON are retained in QuestCoverage.json. Tiles/artwork are excluded.

Mapzeroth Forever 0.6.0 factual NPC geography is pinned at
`fd68cfe2153379898680c66a01833846f9933587` (MIT), `Data/Forever/Pois.lua` SHA256
`3dfa6f85e6fbe1c5a01389d4bcf445f4fa63391484647cdec663a849111e977d`.
Only IDs and 674 normalized positions are selected; its engine/UI is excluded.

Community observations require an explicit entity ID, one explicit known zone,
numeric coordinates and agreement between observations. Deleted, outdated and
other-game comments are excluded. **3 ground-item points** are used, with
quest/comment IDs retained in QuestCoverage.json. These need beta verification;
community observations do not establish prerequisites or loot rates.

## Audit and the remaining completion gate

The Lua 5.1 host audit checked **152 faction/level-section guides** and
**11,822 stored map points**. It verifies finite coordinates, exclusions,
repeatable filtering, stage ordering, AND/OR hand-in prerequisites, escort
adjacency and non-increasing estimated distance. Movement, pickups, abandonment
and Scan do not reorder a selected fixed guide. This is bounded local search,
not globally optimal XP or terrain routing.

**32 of 152 guide sections currently have no audited source gaps.**
`--require-complete` exits with status 2 while any guide has missing locations,
pickup requirements, required quantities or prerequisite review steps. Passing
route invariants alone must never be presented as 100% guide completion.
`GuideSourceQueue.json` identifies **470 remaining quest records**, their exact
missing stages/facts and relevant source URLs. It is included in releases.

The environment rules have been applied and initial source reads succeeded.
Some individual source pages still return HTTP 403; known failures are recorded
and not retried unchanged. Other gaps contain no position/condition evidence in
the captured sources. An exact quest/NPC beta observation can fill such a gap;
a neighboring quest or guessed chain cannot.

Host checks do not certify beta APIs, secret values, NPC offers, protected actions,
map rendering, cave entrances, walkable terrain or travel times. Lines show visit
order; the travel graph has transport facts and estimated walks, not a navmesh.
Read TESTING.md and export labeled /wt findings for current-beta evidence.

## Per-source-category coordinate coverage

These counts include source-category quests before normal leveling filters.
A complete-location row does not prove pickup eligibility, objective quantities
or live beta behavior. Capitals, class/profession/dungeon/seasonal quests may
remain in the catalogue while excluded from normal leveling.

| Source zone/category | Quests | Pickups | Objective areas | Hand-ins | Complete locations |
| --- | ---: | ---: | ---: | ---: | ---: |
| battlegrounds/alterac-valley | 65 | 55 | 36 | 59 | 40 |
| battlegrounds/arathi-basin | 48 | 36 | 4 | 36 | 10 |
| battlegrounds/darkspear-islands | 9 | 3 | 0 | 3 | 0 |
| battlegrounds/reuse-old-scarlet-monastery | 1 | 1 | 0 | 1 | 0 |
| battlegrounds/warsong-gulch | 42 | 24 | 0 | 24 | 0 |
| classes/druid | 58 | 58 | 15 | 58 | 51 |
| classes/hunter | 52 | 51 | 19 | 52 | 46 |
| classes/mage | 51 | 51 | 22 | 51 | 45 |
| classes/paladin | 101 | 84 | 27 | 87 | 72 |
| classes/priest | 89 | 61 | 8 | 62 | 57 |
| classes/rogue | 66 | 54 | 23 | 54 | 42 |
| classes/shaman | 87 | 70 | 19 | 69 | 53 |
| classes/warlock | 102 | 95 | 38 | 91 | 68 |
| classes/warrior | 74 | 73 | 27 | 73 | 58 |
| dungeons/blackfathom-deeps | 13 | 9 | 2 | 10 | 4 |
| dungeons/blackrock-depths | 43 | 27 | 3 | 27 | 4 |
| dungeons/blackrock-spire | 37 | 27 | 3 | 28 | 5 |
| dungeons/city-of-dalaran | 8 | 0 | 0 | 0 | 0 |
| dungeons/dire-maul | 38 | 10 | 3 | 9 | 2 |
| dungeons/excavation-site-wetlands | 14 | 3 | 0 | 2 | 0 |
| dungeons/gnomeregan | 28 | 14 | 10 | 17 | 9 |
| dungeons/maraudon | 11 | 9 | 5 | 8 | 3 |
| dungeons/ragefire-chasm | 6 | 5 | 0 | 5 | 0 |
| dungeons/razorfen-downs | 7 | 4 | 3 | 5 | 2 |
| dungeons/razorfen-kraul | 6 | 4 | 1 | 5 | 0 |
| dungeons/ruins-of-lordaeron | 12 | 6 | 1 | 10 | 1 |
| dungeons/scarlet-monastery | 8 | 6 | 2 | 7 | 1 |
| dungeons/scholomance | 12 | 11 | 0 | 12 | 0 |
| dungeons/shadowfang-keep | 3 | 3 | 0 | 2 | 0 |
| dungeons/stratholme | 17 | 12 | 1 | 11 | 0 |
| dungeons/the-deadmines | 5 | 5 | 3 | 5 | 3 |
| dungeons/the-hall-of-thanes | 4 | 3 | 0 | 3 | 0 |
| dungeons/the-stockade | 6 | 6 | 0 | 6 | 0 |
| dungeons/the-temple-of-atalhakkar | 10 | 7 | 2 | 6 | 3 |
| dungeons/uldaman | 29 | 21 | 12 | 23 | 13 |
| dungeons/wailing-caverns | 12 | 8 | 5 | 9 | 6 |
| dungeons/zulfarrak | 10 | 10 | 1 | 10 | 3 |
| eastern-kingdoms/alterac-mountains | 21 | 18 | 10 | 19 | 16 |
| eastern-kingdoms/alterac-valley | 3 | 3 | 0 | 3 | 0 |
| eastern-kingdoms/anvilmar | 1 | 1 | 1 | 1 | 1 |
| eastern-kingdoms/arathi-highlands | 54 | 50 | 32 | 50 | 47 |
| eastern-kingdoms/badlands | 44 | 42 | 28 | 44 | 38 |
| eastern-kingdoms/blackrock-mountain | 15 | 14 | 12 | 15 | 11 |
| eastern-kingdoms/blasted-lands | 26 | 26 | 20 | 26 | 26 |
| eastern-kingdoms/burning-steppes | 24 | 24 | 18 | 24 | 19 |
| eastern-kingdoms/crafting | 150 | 0 | 9 | 36 | 0 |
| eastern-kingdoms/deeprun-tram | 2 | 2 | 0 | 2 | 1 |
| eastern-kingdoms/dun-morogh | 64 | 62 | 34 | 64 | 57 |
| eastern-kingdoms/duskwood | 100 | 99 | 43 | 99 | 90 |
| eastern-kingdoms/eastern-plaguelands | 109 | 82 | 53 | 108 | 58 |
| eastern-kingdoms/elwynn-forest | 78 | 74 | 40 | 75 | 70 |
| eastern-kingdoms/hillsbrad-foothills | 56 | 56 | 39 | 56 | 49 |
| eastern-kingdoms/ironforge | 82 | 82 | 23 | 82 | 42 |
| eastern-kingdoms/kharanos | 1 | 1 | 0 | 1 | 1 |
| eastern-kingdoms/loch-modan | 47 | 46 | 24 | 46 | 44 |
| eastern-kingdoms/redridge-mountains | 43 | 40 | 25 | 42 | 39 |
| eastern-kingdoms/riverglades | 1 | 1 | 0 | 1 | 1 |
| eastern-kingdoms/searing-gorge | 31 | 30 | 24 | 31 | 29 |
| eastern-kingdoms/shadowfang-keep | 2 | 0 | 0 | 0 | 0 |
| eastern-kingdoms/silverpine-forest | 50 | 50 | 26 | 50 | 50 |
| eastern-kingdoms/stonewrought-dam | 1 | 1 | 0 | 1 | 1 |
| eastern-kingdoms/stormwind-city | 88 | 84 | 23 | 87 | 81 |
| eastern-kingdoms/stranglethorn-vale | 125 | 106 | 79 | 106 | 98 |
| eastern-kingdoms/swamp-of-sorrows | 28 | 25 | 14 | 24 | 21 |
| eastern-kingdoms/the-hinterlands | 45 | 45 | 31 | 45 | 43 |
| eastern-kingdoms/thoradins-wall | 1 | 1 | 0 | 1 | 1 |
| eastern-kingdoms/tirisfal-glades | 66 | 65 | 44 | 66 | 64 |
| eastern-kingdoms/undercity | 32 | 31 | 16 | 31 | 27 |
| eastern-kingdoms/western-plaguelands | 92 | 91 | 48 | 91 | 68 |
| eastern-kingdoms/westfall | 54 | 54 | 29 | 54 | 52 |
| eastern-kingdoms/wetlands | 66 | 60 | 31 | 60 | 57 |
| kalimdor/abyssal-sands | 1 | 0 | 0 | 0 | 0 |
| kalimdor/ashenvale | 82 | 76 | 41 | 77 | 69 |
| kalimdor/azshara | 45 | 27 | 12 | 27 | 23 |
| kalimdor/blackmaw-hold | 7 | 7 | 4 | 7 | 4 |
| kalimdor/darkshore | 80 | 80 | 53 | 80 | 78 |
| kalimdor/darnassus | 29 | 28 | 7 | 28 | 20 |
| kalimdor/desolace | 76 | 62 | 43 | 60 | 54 |
| kalimdor/durotar | 67 | 61 | 39 | 62 | 56 |
| kalimdor/dustwallow-marsh | 69 | 55 | 25 | 55 | 53 |
| kalimdor/felwood | 87 | 83 | 39 | 83 | 43 |
| kalimdor/feralas | 78 | 78 | 43 | 78 | 66 |
| kalimdor/field-of-giants | 1 | 1 | 0 | 1 | 1 |
| kalimdor/moonglade | 8 | 8 | 3 | 8 | 7 |
| kalimdor/mulgore | 61 | 57 | 35 | 59 | 57 |
| kalimdor/orgrimmar | 94 | 90 | 30 | 92 | 45 |
| kalimdor/ruttheran-village | 4 | 4 | 2 | 4 | 4 |
| kalimdor/shendralas | 3 | 0 | 1 | 0 | 0 |
| kalimdor/silithus | 126 | 75 | 73 | 117 | 51 |
| kalimdor/stonetalon-mountains | 52 | 50 | 34 | 49 | 47 |
| kalimdor/tanaris | 95 | 87 | 43 | 90 | 58 |
| kalimdor/teldrassil | 62 | 60 | 35 | 61 | 59 |
| kalimdor/the-barrens | 116 | 114 | 75 | 114 | 111 |
| kalimdor/thousand-needles | 71 | 67 | 34 | 68 | 63 |
| kalimdor/thunder-bluff | 38 | 38 | 14 | 37 | 27 |
| kalimdor/ungoro-crater | 53 | 52 | 37 | 52 | 46 |
| kalimdor/winterspring | 57 | 57 | 33 | 57 | 49 |
| map:2521 / Published zone 16593 | 8 | 1 | 0 | 1 | 1 |
| map:2521 / Zephras Isle | 108 | 108 | 74 | 108 | 108 |
| miscellaneous/epic | 2 | 2 | 1 | 2 | 2 |
| miscellaneous/legendary | 9 | 8 | 0 | 9 | 2 |
| professions/alchemy | 1 | 1 | 0 | 1 | 0 |
| professions/blacksmithing | 41 | 36 | 6 | 37 | 5 |
| professions/cooking | 11 | 11 | 6 | 11 | 6 |
| professions/engineering | 20 | 20 | 1 | 20 | 7 |
| professions/first-aid | 4 | 4 | 2 | 4 | 4 |
| professions/fishing | 13 | 10 | 1 | 10 | 3 |
| professions/herbalism | 1 | 1 | 1 | 1 | 1 |
| professions/leatherworking | 21 | 20 | 15 | 20 | 2 |
| professions/tailoring | 3 | 2 | 2 | 2 | 2 |
| raids/ahnqiraj | 79 | 27 | 18 | 28 | 0 |
| raids/blackwing-lair | 2 | 1 | 0 | 2 | 0 |
| raids/molten-core | 8 | 2 | 2 | 2 | 0 |
| raids/naxxramas | 91 | 89 | 22 | 91 | 0 |
| raids/onyxias-lair | 1 | 0 | 0 | 0 | 0 |
| raids/ruins-of-ahnqiraj | 1 | 0 | 0 | 1 | 0 |
| raids/zulgurub | 86 | 10 | 9 | 12 | 5 |
| uncategorized | 259 | 129 | 107 | 144 | 122 |
| world-events/childrens-week | 14 | 14 | 10 | 14 | 12 |
| world-events/darkmoon-faire | 47 | 36 | 13 | 42 | 13 |
| world-events/hallows-end | 15 | 15 | 13 | 15 | 12 |
| world-events/love-is-in-the-air | 20 | 20 | 2 | 20 | 12 |
| world-events/lunar-festival | 72 | 64 | 2 | 64 | 53 |
| world-events/midsummer | 16 | 14 | 12 | 14 | 12 |
| world-events/winter-veil | 29 | 27 | 6 | 27 | 21 |

## XP estimate evidence

Quest reward XP comes from captured quest facts. UnitXP/UnitXPMax are probed and
only public numeric values are used. Observed thresholds are saved per client
build. The fallback is the literal `player_xp_for_level` table from the pinned
CMaNGOS snapshot above; no SQL is executed. It is labeled a Classic estimate,
not verified Forever thresholds. Reward scaling is also an older-world estimate.
Mob kills, exploration, rested XP and party effects are omitted. Missing rewards
and unavailable thresholds are reported. Route-start estimates persist without
changing fixed order; they are not an exact finish-level prediction.

The New Horde (787) is flagged for actual-offer confirmation from the main
developer's Orc/Troll report. Race eligibility remains unresolved; no guessed
race mask is bundled. This flagged requirement still counts as an audit gap.

## Current-step elite spawn overlay — 0.8.32

`EliteSpawnData.lua` stores possible locations separately from guide destinations.
The selected unfinished kill/drop objective determines the target NPC IDs; normal
NPCs, quest givers, future steps and non-mob objectives are excluded. Known elite,
rare-elite and world-boss classifications qualify. Unknown classification is used
only for an explicitly Elite quest. Source locations do not track living mobs,
patrol positions, spawn conditions, respawn times or walkable access.

The snapshot contains **343 target NPCs**, **261 published points** and **3,181
older-world reference points**, linked to **431 quests** before guide filters.
Published quest positions can be representative rather than exhaustive. All
selected numeric outdoor spawns from the pinned CMaNGOS snapshot above are retained,
projected through the reviewed Forever map bounds; duplicate coordinates are merged.
Those references require the exact objective NPC and an identity-matched unchanged
quest with an older-world factual fallback. New/changed quests use their published
points only. These counts are source coverage, not verified beta spawn coverage.

`EliteSpawnData.json` records source revisions/checksums, bounds provenance and
limits. The inert packed records load per NPC on demand. Route order, destinations,
guide prerequisites, manual skips and ordinary nameplate marker preferences are
unchanged. The current target's map skulls disappear on completion/skip/guide change;
synced members still needing that objective keep them visible.

Rebuild with the reviewed numeric snapshot and map-conversion file, using:

```sh
/workspace/.wow-together-tests/bin/python tools/build_elite_spawns.py \
  --snapshot /path/to/ClassicDB_1_12_1_z2815.sql.gz \
  --geometry /path/to/Forever/conversion.json
```

The compiler checks the pinned snapshot hash. It parses literal spawn facts without
running SQL, source addon code or server scripts, and does not modify the quest catalogue.

## Reproduce capture, build and audit

Use `/workspace/.wow-together-tests/bin/python` with pinned Lupa 2.8. Run from
this repository, not the installed AddOns folder. Caches stay outside releases.
Keep external factual checkouts at their documented revisions; source hashes
must agree. No source acquisition is hidden inside the offline builder.

```sh
python3 tools/import_warcraftdb.py
python3 tools/import_wowhead.py --all-categories --spread-details
/workspace/.wow-together-tests/bin/python tools/collect_quest_entities.py \
  --from-catalogue WowTogether/QuestCatalogue.lua
/workspace/.wow-together-tests/bin/python tools/build_quest_dataset.py \
  --legacy-snapshot /tmp/wow-together-classic-facts/source/Full_DB/ClassicDB_1_12_1_z2815.sql.gz \
  --forever-pois /tmp/wow-together-mapzeroth-source/Data/Forever/Pois.lua \
  --forever-geometry /tmp/wow-together-questiedb-facts/data/Forever/conversion.json \
  --forever-event-data /tmp/wow-together-questiedb-facts \
  --forever-beta-data /tmp/wow-together-questiedb-facts
/workspace/.wow-together-tests/bin/python tools/audit_quest_guides.py
/workspace/.wow-together-tests/bin/python tools/guide_source_queue.py
/workspace/.wow-together-tests/bin/python tools/capture_quest_pages.py \
  WowTogether/GuideSourceQueue.json --denials WowTogether/QuestCatalogue.json
/workspace/.wow-together-tests/bin/python tools/audit_quest_guides.py --require-complete
/workspace/.wow-together-tests/bin/python -m unittest discover -s tests -q
```

Capture commands need source access; do not loop unchanged denials. The targeted
quest capture excludes known failed IDs and does not overwrite generated addon
files. After capture, rebuild and regenerate both audit reports and the queue.
Run the offline builder twice with unchanged inputs and compare output checksums.
The complete editable catalogue, build tools and notices are included in releases.

## Reviewed Mulgore pickup availability — 0.8.19

The supplied report and overlapping partial NPC observations show missing offers
for Our Ancient Enemy (99101) and The High Chieftain (99082). Both now require an
actual NPC offer while their exact Forever unlocks are unresolved. The reviewed
flags live in `tools/quest_corrections.json` and the generated catalogue; their
published levels, identities, starters and map locations are unchanged. A missing
offer is not an inferred prerequisite. All guides retain complete NPC absence
evidence for the observing character/build until an actual offer rechecks it.
Fresh positive lists are still transient; manual skips and other players'
eligibility remain separate. Mapping coverage does not change in this release.
See `research/README.md` for the original truncated inputs and 94-event review.

### Report to Kadrak alternative quest IDs

6541 (Thork) and 6542 (Darn Talongrip) have reciprocal `exclusiveTo` lists in the
pinned Forever quest fact table. The identity, level and NPC data match our
unchanged records. Reviewed `exclusiveQuests` fields now prevent duplicate pickup
when the other version is active or completed. Fixed guides exclude the unchosen
alternative from that player's applicable scope; they do not grant completion
or create manual skips. The accepted version always keeps its actual work.
Only explicit reviewed relationships qualify; matching quest names alone do not.
Other baseline exclusivity data is not bulk imported by this release.
