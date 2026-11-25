# RETIRE THE LEGACY DUNGEON VIEWER

For players:
- Dungeon cards and access requirements use the Instances page. The legacy map, loot browser, and outdoor approach map are removed.
- The optional dungeon map and loot data package is no longer installed or released.

Please check:
- Open an instance page, inspect its access requirements and quest list, and start a quest route.
- Verify there is no dungeon approach map or old viewer window on entry.

Developer notes:
- Dungeon quest routes now read interior map IDs from the compact instance definitions in the main addon. Encounter ordering and class-specific loot hints from the old optional journal data are retired with the viewer. The dungeon access/quest catalogue remains.
- Host tests and static checks cover the removal and current route entry points. No live-client verification was performed.
