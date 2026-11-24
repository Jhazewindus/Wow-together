# Dungeon journal: current Forever encounter and loot coverage

## Goal

Add source-backed encounter and item-drop records for the five newer dungeons
whose journal sections are currently empty. Use public Forever NPC/item facts
and current guide tables to identify and cross-check IDs. Keep loot icons and
dungeon artwork on native client assets; do not bundle third-party images.

## Behavior

- Add only boss/item links whose IDs and names match captured source pages.
- Mark third-party/community tables as reported rather than exhaustive; keep
  unknown trash, containers, maps, and drops unknown.
- Preserve the viewer's existing encounter, loot-filter, and fallback behavior.

## Files

- `docs/briefs/dungeon-loot-guide-refresh.md`
- `tools/dungeon_forever_additions.json`
- `tools/audit_dungeon_loot.py`
- `WowTogether_DungeonData/DungeonJournalData.lua`
- `WowTogether/DungeonJournalData.json`
- `DUNGEON_VIEWER.md`
- `tests/memory-data-fingerprints.json`
- `tests/test_0824.py`
- `tests/test_0829.py`
- `tests/test_0831.py`
- `changes/core/dungeon-loot-guide-refresh.md`

## Checks

- Record exact dungeon/boss/item IDs, source hashes, native item icons, and
  partial coverage where evidence is missing.
- Run syntax check, host suite, boundary check, and release build.
- Require in-game confirmation of artwork and visible loot item icons before
  merge.
