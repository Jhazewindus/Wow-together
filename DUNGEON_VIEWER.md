# Dungeon viewer — 0.8.29 — MEMORY COMPARTMENTS

**See dungeon** opens the full journal from the main addon's Dungeon quests cards
from anywhere. Cards place **Quest list** beside **Start route**; clicking the
card opens the viewer. Inspecting a dungeon never starts or alters a quest guide.

Choose floors when multiple maps exist; the selector is hidden otherwise.
Select an encounter from the paged boss list or its portrait map marker, and
browse its notable drops. Portrait clicks in Map only open Full view and select
the boss and its loot; selecting a mapped boss changes to its floor. A missing
named portrait uses the client default. Loot has literal name search,
equipment/other filters, a class dropdown, paging, native item icons, cached client tooltips and
standard modified-item clicks. Client item requests are bounded to once per
visible item per viewer session. Common junk/consumables and generic common drops
are omitted. Boss list order is alphabetical within level, not a walkthrough.

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

Captured 6 October 2026:

- 23 Wowhead **Forever** zone pages and 243 Forever NPC pages. Boss flags are
  supplemented with a reviewed Classic encounter list; an ID must also appear
  on the corresponding captured Forever zone page. Only factual names, levels,
  IDs and drop relationships are extracted. Source scripts, guide prose,
  screenshots and community maps are not bundled.
- **19 Classic dungeon complexes**, **243 encounters**, **2,766 notable boss-drop
  entries** (not distinct items). The same item can appear under several bosses.
  Loot and NPC entries can be unconfirmed on the database and remain a snapshot,
  not proof of current beta drops, encounter availability or kill order.
- **164 named client portrait references** and **19 Classic floor-map reference
  sets**. Filenames were checked against `wowdev/wow-listfile`, commit
  `2ee24a9d0ff98f614997587e32ee6a0074d0de65`, `parts/interface.csv`, SHA-256
  `f41981d597d1826d836909ca270ff699cb0cf169243eab9e959907370e1133f4`.
  Blizzard texture files are referenced, not redistributed. Missing textures
  fall back without crashing; a missing map tile hides that whole map.
- The **nine new Forever dungeons do not have a complete captured boss/loot
  dataset**. All remain browsable. Matching native journal encounters, portraits
  and floor maps are used when exposed; missing data is stated. No NPC is called
  a boss just because it is elite, and no new-dungeon map is substituted with an
  unrelated outdoor map or loading-screen illustration.

`WowTogether/DungeonJournalData.json` contains per-page URLs, SHA-256s and counts.
`tools/import_dungeon_journal.py` parses captured literal JSON without running web
code. To reproduce:

```sh
/workspace/.wow-together-tests/bin/python tools/import_dungeon_journal.py \
  --zones /tmp/wt-0824-zones --bosses /tmp/wt-0824-bosses \
  --listfile /tmp/wt-0822-interface.csv
```

The captures are local audit inputs, not distributed web-page copies. The generated
Lua and provenance manifest are in the release.

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
coordinate coverage**, not all 243 encounters: `coverage` lists every unresolved
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

Reproduce the separate factual compilation:

```sh
/workspace/.wow-together-tests/bin/python tools/import_dungeon_positions.py \
  --client-db /tmp/wt-0827-positions \
  --snapshot /tmp/wt-0827-positions/cmangos-full.gz \
  --listfile /tmp/wt-0822-interface.csv
```
