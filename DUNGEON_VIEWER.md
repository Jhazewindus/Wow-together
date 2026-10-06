# Dungeon viewer — 0.8.24

**See dungeon** opens the full journal from the main addon's Dungeon quests cards
from anywhere. Cards place **Quest list** beside **Start route**; clicking the
card opens the viewer. Inspecting a dungeon never starts or alters a quest guide.

Choose floors, select an encounter from the paged boss list or an available
numbered map marker, and browse its notable drops. Loot has literal name search,
equipment/other filters, paging, native item icons, cached client tooltips and
standard modified-item clicks. Client item requests are bounded to once per
visible item per viewer session. Common junk/consumables and generic common drops
are omitted. Boss list order is alphabetical within level, not a walkthrough.

**Map only** collapses the journal into a small gameplay window; **Full view**
restores bosses and loot. Both views move and resize using native frame sizing,
with aspect-correct map tiles and letterboxing. Their sizes and positions are
saved independently in `WowTogetherDB.dungeonViewerUI` and shared across all
dungeons. BG toggles the background; artwork and text stay visible. These are
owned, unprotected frames at MEDIUM strata. Combat does not close the viewer.

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
Reference maps never get guessed clickable boss positions. Embedded skulls in
Blizzard's older map illustration are part of the image, not addon buttons.

Native EJ/maps, textures, tooltips and instance-entry behavior **still need beta
retesting**. `/wt probe` lists capabilities and viewer snapshot counts; presence
alone does not establish successful behavior. Host UI pictures render actual
addon frame definitions with database data, preview-only Blizzard map/art assets,
and substituted fonts; they are not WoW beta screenshots. Preview image files
stay outside the addon and source repository.
