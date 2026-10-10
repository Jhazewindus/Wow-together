# Dungeon viewer — 0.8.66 — NATIVE FINDER FILTERS

**See dungeon** opens the full journal from the main addon's Dungeon quests cards
from anywhere. Cards place **Quest list** beside **Start route**; clicking the
card opens the viewer. Inspecting a dungeon never starts or alters a quest guide.

**Quest list** opens compact, scrollable quest cards showing pickup giver/zone,
quest level and current status. Filter All, To collect, In your log or Completed.
A card or Route to pickup starts a personal preparation guide for that quest and
its required prerequisites, ending on acceptance. Start route builds a collection
guide for all matching quests at the player's pickup level, across every needed
zone, then directs to the entrance. Both use the same small guide window as
leveling; opening the list alone does not change a guide.

Required known chains are deduplicated, preserving their accept/objective/return
order before child pickups. Alternative prerequisites choose one compatible
branch; uncertain candidates are not treated as proven requirements. Missing
locations, actual absent offers and incompatible/too-high prerequisites prevent
a false completed collection. Accepted goal quests count as already collected. Entering the matching dungeon
after collection completes the preparation guide without awarding quest credit.
Planning is scheduled; directed Dijkstra travel/known flight costs order visits,
with bounded dependency-safe relocation improvements. Progress removes finished
steps from the prepared itinerary; an explicit Scan can replan. Geography gaps
use distance estimates only for ordering. This is not a global-optimum promise
or road/terrain coverage for all walks. No NPC offer is inferred from sharing.

Record entrance here is removed from the list. Existing saved entrance corrections
remain readable, followed by native map links and published entrance areas.

Choose floors when multiple maps exist; the selector is hidden otherwise.
Select an encounter from the paged boss list or its portrait map marker, and
browse its encounter drops. Trash mobs and treasure containers are listed beneath
bosses; selecting one opens its own loot without moving the map or creating markers. Portrait clicks in Map only open Full view and select
the boss and its loot; selecting a mapped boss changes to its floor. A missing
named portrait uses the client default. Loot has literal name search,
equipment/other filters, a class dropdown, paging, native item icons, cached client tooltips and
standard modified-item clicks. Client item requests are bounded to once per
visible item per viewer session. Shared/world drops, including junk and recipes, are separate from encounter loot.
Choose Shared / world drops for a boss's other sourced drops. Trash and treasure
tables include every captured drop row, including common items; equipment/other
and class filters narrow browsing. Boss list order is alphabetical within level, not a walkthrough.

The class dropdown defaults to your character and retains your choice when you
switch dungeons. **All classes** shows every listed drop. Known weapon/armor types
filter by supported class proficiencies, including armor available through later
training. Shared accessories, quest items and unclassified types stay visible.
This is a type-usability filter, not a spec/stat ranking or a check of trained
skills, talents or item-specific class restrictions. Retest Forever's class
proficiencies as the beta changes; All classes remains available for comparison.
Boss clicks follow the floor containing their mapped point, preferring native
positions over reference positions. Unknown floor assignments are not guessed.

Quest icons open a separate small, movable action card with the NPC/object,
quest names and pickup/objective/turn-in instructions. Actual quest relationships
place these markers; a city pickup is never substituted with the dungeon entrance
or an interior boss. Several quests at one NPC share an icon. Objective markers
may preview unaccepted work: a marker does not certify pickup availability.
Completed quests, accepted pickup steps and known incompatible faction/class/race
quests are hidden. Quest events refresh visible markers/cards in a short batch.
The saved **Quests** toggle hides/shows quest markers across dungeons. Boss levels
outside 1–255, including Wowhead's 9999 placeholders, are omitted.

Player windows keep labels concise and show brief unavailable states for missing
maps or loot. Source coverage, native API details and layout limitations belong
in diagnostics and the source notes below.

The 0.8.28 hotfix keeps transport and ordinary zone/objective updates out of the
closed dashboard's catalogue scan. Visible background dashboard work is batched
for 0.1 seconds with a new query; guide progression still updates separately.
Viewer listeners reuse the dispatch frame's existing event subscriptions while
preserving previous handlers. Genuine registration failures remain diagnostic.

**Map only** collapses the journal into a small gameplay window; **Full view**
restores bosses and loot. Both views move and resize using native frame sizing,
with aspect-correct map tiles and letterboxing. Their sizes and positions are
saved independently in `WowTogetherDB.dungeonViewerUI` and shared across all
dungeons. BG toggles the background; artwork and text stay visible. These are
owned, unprotected frames at DIALOG strata, above the HIGH main window; opening
raises the journal among its peers. Combat does not close the viewer.

Entering a recognized five-player dungeon asks **Open map?** once per entry,
outside combat. Accepting opens the compact view; declining leaves gameplay and
quest directions unchanged. **Offer the map when entering a dungeon** in Leveling
guides settings disables the prompt without disabling manual browsing. Raid and
unrecognized/private instance data do not trigger it. Exact English instance
names/aliases match the bundled definitions; localized matching needs further
beta work. No network downloads or addon-message transfers occur in game.

## Source snapshot and actual limits

Captured and audited 6 October 2026:

- Original Vanilla encounter identities are reviewed in `tools/dungeon_encounters.json`.
  The old zone boss flags selected BFD's Season of Discovery raid NPCs, while
  omitting some Vanilla encounters. Those flags no longer select the journal.
- **933 Vanilla NPC tables and 95 treasure-container tables captured without
  failures**, covering every listed Vanilla NPC/container across all 19 classic
  dungeon complexes. **415,670 source rows audited**, **5,557 distinct item facts**,
  **1,214 encounter-drop relationships**, **16,228 other/shared boss relationships**,
  **532 trash listings with 313,233 relationships**, and **103 container listings
  with 6,087 relationships**. A source appearing in more than one dungeon has
  more than one listing; large world-drop pools contain many repeated relationships.
  Coverage means every row in these source tables is represented, not proof of
  every item currently obtainable in the Forever beta. Quest rewards, vendor stock,
  skinning and gathering tables are outside the journal drop tables.
- Every boss/ordinary-mob/container relationship retains its actual source.
  Vanilla loot groups alone are not proof of boss-specific loot. Shared ordinary-mob
  drops, junk and new items without an explicit boss owner stay outside encounter
  loot. Captured Forever item metadata and explicit specific/new relationships
  supplement the baseline; **13,127 season-only rows** are excluded. NPC pages can
  contain historic Classic, Hardcore, Anniversary and SoD samples even under a
  Forever URL. No historical sample rate is presented as a Forever drop chance.
- **263 encounter listings across 22 dungeon definitions**. Hall of Thanes has
  four reported encounters and twelve reported drops; Ruins of Lordaeron and
  Excavation Site: Wetlands also have explicit community encounter/drop tables.
  Their matching public NPC/item IDs, names and icons were verified against the
  page's literal metadata. Comment IDs/authors/dates and page hashes are in
  `communityReports`; these are reported beta observations, not official or
  exhaustive loot tables. Missing beta trash tables remain unknown.
- The remaining **six new dungeon definitions** have no captured encounter/loot
  tables. Wowhead began returning CloudFront 403s during the NPC audit; bulk
  captures were stopped. Warcraft DB's public NPC endpoint was checked but has no
  loot tabs for the tested NPCs; the tested new item endpoint was unavailable.
  These external gaps prevent a truthful 100% current-Forever claim. No NPC is
  called a boss just because it is elite and no absent relationship is guessed.
- Items are shared by ID and decoded only when inspected. Startup host Lua memory
  is approximately 28.4 MiB after host collection; no forced collection runs in
  the client. All other quest/guide data compartments and decisions are preserved.
- **171 client portrait references and 19 Classic reference floor-map sets**.
  Texture filenames use `wowdev/wow-listfile` commit
  `2ee24a9d0ff98f614997587e32ee6a0074d0de65`, `parts/interface.csv`, SHA-256
  `f41981d597d1826d836909ca270ff699cb0cf169243eab9e959907370e1133f4`.
  Blizzard files are referenced, not redistributed. BFD reference markers now
  select original encounter IDs; their existing reference positions are retained.

`DungeonJournalData.json` contains source URLs, SHA-256s, per-dungeon coverage and
known missing beta sources. Captures stay outside the release. Only facts are
included; no website scripts, guide prose, community images or addon code are copied.

The reproducible importer uses literal-only parsers (never JavaScript evaluation):

```sh
/workspace/.wow-together-tests/bin/python tools/audit_dungeon_loot.py \
  --zones /tmp/wt-0831-loot/zones --npcs /tmp/wt-0831-loot/npcs \
  --bosses /tmp/wt-0824-bosses --vanilla /tmp/wt-0831-loot/vanilla \
  --containers /tmp/wt-0831-loot/containers --listfile /tmp/wt-0822-interface.csv
```

`tools/import_dungeon_journal.py` delegates to this audit and requires the complete
Vanilla input; the old boss-flag-only importer is removed. `capture_dungeon_loot.py`
uses bounded workers, proxy/TLS defaults and resumable hashed captures; source
access denial pauses bulk capture. The capture function can also target the
public `https://classicdb.ch/?npc=<ID>` and `?object=<ID>` Vanilla tables.

## Native beta adapter

API signatures were checked against Gethe's Forever UI snapshot,
`a84e2b1b41d3d4137127c07e4da448aa3251d6f1`:

- `Blizzard_APIDocumentationGenerated/MapDocumentation.lua`: map groups and
  `C_Map.GetMapArtLayers` / `GetMapArtLayerTextures`, including layer/tile sizes.
- `Blizzard_MapCanvas/Blizzard_MapCanvasDetailLayer.lua`: row-major native tiles.
- `Blizzard_APIDocumentationGenerated/EncounterJournalDocumentation.lua`:
  `C_EncounterJournal.GetEncountersOnMap`, encounterID/mapX/mapY fields.
- `Blizzard_EncounterJournal/Mainline/Blizzard_EncounterJournal.lua`: explicit
  instance/encounter reads and creature portrait return positions.

Current client floors take precedence over the older reference layouts. No EJ
instance, encounter, tier, difficulty or loot filter is selected or changed.
Discovery is bounded and uses the current journal tier; unavailable tiers are
not silently assumed to contain Forever data. Native boss markers only match
published/native encounter names and public coordinates on that exact floor.
Reference maps get only sourced floor positions, never guessed points. Embedded skulls in
Blizzard's older map illustration are part of the image, not addon buttons.

Native EJ/maps, textures, tooltips and instance-entry behavior **still need beta
retesting**. `/wt probe` lists capabilities and viewer snapshot counts; presence
alone does not establish successful behavior. Host UI pictures render actual
addon frame definitions with database data, preview-only Blizzard map/art assets,
and substituted fonts; they are not WoW beta screenshots. Preview image files
stay outside the addon and source repository.

## Static floor positions

`DungeonMapData.lua/json` adds **158 boss positions** and **414 interior quest
target positions for 139 quests**, with records for all 28 dungeon definitions.
All 19 Classic complexes have some reference positions. This is **partial
coordinate coverage**, not all 263 encounter listings: `coverage` lists every unresolved
boss, including missing event spawns and ambiguous multi-floor locations. The
nine new Forever dungeons have no verified offline interior coordinates in this
capture; matching public native encounters/maps can supply live positions.

Sources are factual CSV tables from `eXPeRi91/ClientDB-Diff` revision
`ac1d02cba59374c5d599f78ede0cd3984f4312a1` (`JournalEncounter`, `DungeonMap`,
`WorldMapArea`), the already attributed/licensed CMaNGOS snapshot, the verified
client filename list, and this project's compiled Forever quest/entity relations.
URLs, SHA-256s and per-dungeon counts are in `DungeonMapData.json`. No downloaded
implementation, SQL, web scripts, guide text or image files are included.

Journal coordinates must match the same old world-map area and game instance,
and identify an available floor. Unambiguous world spawns are projected onto
explicit client floor rectangles. Several possible floors are **not** resolved
by guessing elevation or drawing the target on every floor. A representative
point is an actual spawn, never an average through walls. Broad trash-mob
objectives use one representative per target/floor to avoid covering the map.

The reference coordinates are older Classic facts, not measurements in Forever.
They apply to the corresponding bundled map illustration. Native floors inherit
them only when **all tile file IDs and dimensions match** that illustration;
same dungeon/floor names do not suffice. Exact native boss coordinates override
the old boss point and corresponding quest-target point. A redesigned/native
map with different art uses only its available native boss/related quest points.
Outside pickups/turn-ins are deliberately absent from interior coverage counts.
Retest positions, changed encounters and portrait availability in the beta.

## Live player on Classic reference maps

The runtime now retains **51 published world rectangles** for the reference
floors, with their game instance map ID and source row. `UnitPosition("player")`
can be projected with exactly the same world-X/world-Y reversal as static
spawns. This does not require `C_Map.GetPlayerMapPosition` or native dungeon
artwork. Ragefire uses `DungeonMap` row 136, game map 389. The current dungeon
name, instance ID and public position must agree. The marker uses the rendered
image's scaled/letterboxed rectangle, updating at 10 Hz without redrawing loot.

Only a unique matching floor is accepted. Overlapping world rectangles cannot
establish height/floor; no floor is chosen from proximity to a boss or entrance.
Nil, restricted, failed, nonfinite, out-of-bounds or mismatched positions hide
the marker. Native floor tracking remains available on exact native art.
These are attributed older-world rectangles, so runtime coordinate availability
and Forever alignment still require an in-instance retest. `/wt probe` reports
the actual public coordinate/instance state while the addon map is open.

Reproduce geometry augmentation while retaining reviewed boss/quest positions:

```sh
/workspace/.wow-together-tests/bin/python tools/import_dungeon_positions.py \
  --client-db /tmp/wt-0827-positions --geometry-only
```

This mode verifies both CSV SHA-256s against `DungeonMapData.json` before writing.

## Forever finder filters

Forever's Classic `LFGBrowseFrame` now owns a compact header bar with combined
role/class choices. It filters the native ScrollBox tree while preserving
original result IDs/order and retaining Groups/self-listings. Original results
are restored for All/All, disabling the option or leaving Browse. Native search,
activity controls, handlers and invite/message actions are not replaced.
Changes wait during combat; protected/unsupported providers remain untouched.
The legacy retail search/applicant companion remains a fallback for those UIs.
Roles come from public assigned roles / `lfgRoles` flags, never from class.

RFC's submitted 0.8.65 probe has instance 389 but no public X/Y, so its map
stays static and the button says **Static map** (click to recheck). This is not
an inferred position at the entrance or a fabricated native floor. A matching
usable position restores Locate me and the marker automatically. HiddenMaps'
public description also limits live tracking to supported pre-instance areas.

Reference facts and host checks are recorded in
`research/release-0.8.66-2026-10-10/README.md`. Actual beta UI integration,
selection/invite behavior and position availability still need live checks.

Reproduce the separate factual compilation:

```sh
/workspace/.wow-together-tests/bin/python tools/import_dungeon_positions.py \
  --client-db /tmp/wt-0827-positions \
  --snapshot /tmp/wt-0827-positions/cmangos-full.gz \
  --listfile /tmp/wt-0822-interface.csv
```
