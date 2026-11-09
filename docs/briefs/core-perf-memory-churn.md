# Performance brief — memory churn in party mode

## Why

The beta report shows high external addon attribution and intermittent party-mode FPS drops. The addon probe reports about 69.6 MiB including optional data, while an external monitor reported 142.5 MB. That gap may be uncollected allocation churn; the tester will compare readings before and after a manual full collection. The current repository has no per-subsystem allocation ledger, so this change adds a bounded rolling ledger to `/wt probe`.

## What changes

- Cache minimap display points and safety/terrain contexts by route/path/map inputs; reuse projection and screen-coordinate arrays each tick. Remove per-segment scratch tables from the safety/terrain hot checks.
- Reuse navigation state, sample points, route waypoints, path-line points, and arrow geometry. Cache presentation and text until the stop, label, rounded distance, or route/progress inputs change.
- Compare travel path inputs directly; cache the personal-transport signature and build travel-line points once per path cursor/revision.
- Add a fixed-size, allocation-free sampling ledger for minimap, navigation, arrow, travel, recorder, and probe sections; report rolling 60-second deltas and sampled Lua heap/peak in `/wt probe`. Do not force garbage collection.
- Reuse passive recorder sample points.
- Keep the ledger and any caches bounded to fixed buckets or the current route/path revision.
- Files: `WowTogether/Core.lua`, `WowTogether/DataStore.lua`, `WowTogether/UIControls.lua`, `WowTogether/MinimapRoute.lua`, `WowTogether/Navigation.lua`, `WowTogether/StandaloneArrow.lua`, `WowTogether/TravelNetwork.lua`, `WowTogether/Travel.lua`, `WowTogether/TravelPersonal.lua`, `WowTogether/GuideControls.lua`, `WowTogether/QuestConfirmation.lua`, `WowTogether/TravelTrails.lua`, `WowTogether/TravelSafety.lua`, `WowTogether/TravelTerrain.lua`, `WowTogether/Planner.lua`, `WowTogether/PerformanceLedger.lua` (new), `WowTogether/WowTogether.toc`, this brief, `changes/core/perf-memory-churn.md`, and `tests/test_perf_memory_churn.py`.

## Tests

- Use `collectgarbage('count')` around 1,000 unchanged calls to minimap, navigation, arrow, and travel destination; each steady-state delta must be below 4 KB.
- Exercise changing route, map, travel revision, stop, and rounded distance inputs to confirm caches invalidate and output remains correct.
- Confirm the 60-second ledger wraps and expires old buckets, collects each named section, and does not allocate while recording.
- Confirm `/wt probe` allocation stays under 1 MB in the host fixture and does not force GC.
- Lua 5.1 compile, full host suite, module boundary, PR fragment validation, and release build.

## Acceptance

The named 1 Hz-or-faster paths allocate less than 4 KB over 1,000 unchanged host calls, `/wt probe` reports allocation and Lua heap data without collecting garbage, and all existing guide/navigation behavior remains unchanged. The 30-minute / 70 MiB and external monitor checks remain an in-game acceptance test; host measurements do not establish native FPS or client memory attribution.
