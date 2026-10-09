# Classic dungeon tracking and finder adapters

Reviewed 9 October 2026 for the reported Forever client 1.60.1 / 70291.

## Report comparison

- RFC screenshot: WoW Together's reference artwork has bosses and quest markers
  but no player marker. This image is not evidence of a native dungeon UI map.
- Finder screenshot: Forever's Classic Looking For Group Browse page is open;
  our 0.8.64 role view is absent. The old adapter targeted the retail frames.
- Barry-Batsman's 0.8.64 probe confirms `UnitPosition` and the public LFG player
  APIs exist, but is captured in Orgrimmar, not inside RFC. It does not show
  actual interior coordinates. Role/class filter behavior and RFC alignment
  therefore still require the targeted in-game checklist.

## Dungeon world geometry

Retain the published rectangles from the same sources already used to project
static dungeon NPC/object spawns. Hashes match `DungeonMapData.json`:

- [DungeonMap.csv](https://github.com/eXPeRi91/ClientDB-Diff/blob/ac1d02cba59374c5d599f78ede0cd3984f4312a1/DungeonMap.csv)
  SHA-256 `8501cb2f71c8a9d0c48281cc4572e602028c6b7c0887eca4efcaa6e90b42f5fb`.
- [WorldMapArea.csv](https://github.com/eXPeRi91/ClientDB-Diff/blob/ac1d02cba59374c5d599f78ede0cd3984f4312a1/WorldMapArea.csv)
  SHA-256 `426f03ac2248302b2ec6f3c38eb2a386ed953b83056390b2550ee37da4bfcb86`.

The augmentation retains all existing boss/quest relationships and introduces
51 reference-floor world rectangles. RFC uses game instance 389, DungeonMap
row 136: left -285.993, right 452.871, bottom -452.953, top 39.6232.
Map x = (right - worldY)/(right - left); map y = (top - worldX)/(top - bottom).
Use only public `UnitPosition` values inside the confirmed matching instance.
Overlapping floors, private positions, missing transforms and outdoor data are
not replaced with guessed points. Old rectangles are not certified Forever
measurements. No downloaded addon implementation was used.

## Forever finder source facts

Read the public Forever UI reference at Gethe/wow-ui-source commit
[`9465cb273b5513495d8ecc12fbb19930dd6b8957`](https://github.com/Gethe/wow-ui-source/tree/9465cb273b5513495d8ecc12fbb19930dd6b8957).
This is a pinned Forever reference, not a claim that build 70291 is identical.
Relevant paths below are under `Interface/AddOns/`:

- `Blizzard_GroupFinder_VanillaStyle/Classic/Blizzard_LFGVanilla_ParentFrame.xml`
  defines `LFGParentFrame` with the `LFGBrowseFrame` Browse child.
- `Blizzard_GroupFinder_VanillaStyle/Blizzard_LFGVanilla_Browse.lua`
  reads `C_LFGList.GetFilteredSearchResults`, `GetSearchResultPlayerInfo`,
  `classFilename`, native selected activity IDs and explicit role flags.
- `Blizzard_APIDocumentationGenerated/LFGListInfoDocumentation.lua`
  defines `LfgSearchResultPlayerInfo` with `classFilename` and `lfgRoles`.
  Forever's LFGRoles is a structure containing `tank`, `healer` and `dps`.

The companion is independently implemented using these API/frame facts. It
filters its own rows and menus without changing native scripts, providers,
searches or invite/message actions. Class filters use the public class token;
roles come from assigned roles/declared flags, never inferred from class.

## Checks

`tests/test_0865.py` covers reference-world movement/resize alignment, instance
and secret-value rejection, ambiguous floor handling, hidden/combat behavior,
diagnostics, actual Forever frame names, structured multi-role players, combined
class/role filtering, native activities, self-result filtering and UI ownership.
Existing native player, secret-aura isolation and sourced dungeon-marker tests
remain part of the release checks. See `TESTING.md` for live beta verification.
