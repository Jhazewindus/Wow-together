# Performance maintenance — 0.6.9

## Whole quest-flow compilation in 0.8.49

Dependency-closure candidates use complete-guide state replay and pooled published
travel rows. Candidate closures are bounded at 24 actions, lookahead at 128,
eight alternatives per objective and two passes. Cheap changed-edge comparisons
reject zero/tiny savings before replay. No planner work runs from resize geometry;
started guide progress still reads its immutable plan.

On this Lua 5.1 host, a mocked 5000×3500 Mulgore build took about 1.0 seconds of
total resume execution across 1,538 cooperative slices; the largest slice was
8.54 ms. The existing timer adds scheduling delay between slices. This is a host
responsiveness check, not a native FPS/loading-time promise. Source compilation
and initial unpacking do more work than later progress updates.

The ordinary host benchmark measured roughly 954 ms for Mulgore compilation,
9 ms for progress, 44 ms for browsing and 7 ms for the 240-stop map redraw.
These include mocked APIs and host load; they do not establish a speedup against
0.8.48 or predict beta timings. Graph caches are bounded (32 rows for a compile
policy; eight for existing flight geometry). Generic compile state is released
after the plan/result, without retaining model closures or personal flight data.


## Elite spawn hints in 0.8.32

The separate spawn compartment keeps 343 NPC records inert until a current target
needs them. It adds about 0.3 MiB to the Lua 5.1 host startup heap (about 28.7 MiB
total); it does not materialize every spawn or scan the quest catalogue each frame.
Map buttons are pooled and reused, with the same viewport projection as route
markers. Hidden-map cleanup runs once and unchanged objectives do not redraw their
spawn overlay. These host figures exclude native frames/textures and SavedVariables.

## Expanded dungeon loot in 0.8.31

The Vanilla loot audit stores 5,557 item facts once and retains drop relationships
as ID arrays. Item records load individually; opening dungeon metadata does not
materialize every NPC's loot. Boss, trash and treasure views reference those shared
item records. Repacking retains this boundary.

The same Lua 5.1 host fixture retains about 28.4 MiB at startup and 29.7 MiB after
browsing Ragefire Chasm, Blackfathom Deeps, Blackrock Depths and Hall of Thanes.
Opening their journal data took about 3, 7, 19 and less than 1 millisecond,
respectively, on this host. These exclude native client textures, frame memory
and existing SavedVariables; they are not beta timing or memory guarantees.

## Data memory in 0.8.29

The reported 80–110 MB prompted a retained-heap audit. In the previous Lua 5.1
host load, QuestCatalogue.lua alone retains about 45.2 MiB, comprising 5,230
quests and NPC/object/item data. Dungeon journal/map data adds about 3.2 MiB;
travel data is about 0.5 MiB. Disk archive size and native texture/frame memory
are different measurements.

DataStore.lua now keeps nested fields as inert, length-independent token strings
and decodes a requested field once. Quest scalar metadata stays resident for
all-zone browsing and eligibility checks. Entity metadata also loads by ID;
dungeon bosses/loot and floor/quest positions unpack per requested dungeon.
The versioned compiler shares a string dictionary, preserves numbers/booleans/
Unicode/empty tables, and removes the packed payload after successful decode.
No loadstring, downloaded code, HTTP, GC control or new native loading API runs
in the game. Decoded tables remain stable because runtime map resolution and
annotations mutate them. Visiting more content therefore grows the loaded data;
this is demand loading, not an eviction cache or an in-game memory ceiling.

Full materialization of all six datasets matches the previous source exactly.
Existing guide-list, compiled-order and map-geometry fingerprints match.
The same solo host fixture, with empty SavedVariables, gives:

| Retained Lua heap after collection | 0.8.28 | 0.8.29 |
| --- | ---: | ---: |
| Startup | 51.7 MiB | 25.2 MiB |
| Guide/library browsing | 54.0 MiB | 28.3 MiB |
| Compiled Mulgore guide | 55.0 MiB | 29.4 MiB |
| Wailing Caverns viewer open | 55.2 MiB | 29.7 MiB |
| Twenty further refresh/browse/viewer passes | 55.2 MiB | 29.7 MiB |

These are external Lua 5.1 heap measurements with mock frames/APIs. They exclude
native textures/frames, existing account SavedVariables and client attribution;
they do not predict an exact beta memory/FPS result. No collection is forced in
game. `/wt probe` capability-checks the client memory API and reports its total
when available; compartment lines give record/field load counts and remaining
packed payload bytes, not estimated total memory ownership per feature.

Reproduce with:

```sh
/workspace/.wow-together-tests/bin/python tools/benchmark_memory.py --baseline-ref v0.8.28 --output /tmp/wow-together-memory.json
```

`tools/pack_data.py` repacks owned generated datasets deterministically without
network access or changing provenance manifests. Source importers emit the same
format; offline audits materialize fields before enumeration. Test file
`tests/test_0829.py` checks lazy load boundaries, stable mutation, replacements,
missing keys, codec values, source hashes and guarded diagnostics. The friend
script covers actual beta memory, first-use pauses, maps, NPCs and guide progress.

The same release incorporates Romits' resizable/closable guide-step window with
saved geometry and width-matched attached panels. Layout changes do not rebuild
or scan guides. Dungeon lists refresh character context and require verified
identity compatibility; explicit collection starts no longer fall back to the
entrance-recording list when locations are missing. Targeted host tests cover
Blackfathom factions, stale/private character context, explicit/list/card starts,
pending unmapped collections, combat-safe owned-window layout and close/reopen.

## Dungeon refresh hotfix in 0.8.28

The supplied 0.8.27 stack enters the leveling browser through background
`SyncNow(false) -> Refresh -> Render`. Its probe shows a future bracket, four
waiting peers, Wailing Caverns, level 23 and no public player map ID; window
visibility is not recorded. Transport refreshes were rendering the dashboard regardless of
its visibility, including after each outgoing/incoming packet.

The shared transport/roster refreshes, zone entry and objective events now use
the background path. Guide, tracker, map and arrow progression still update;
the closed dashboard does not scan its catalogue. Visible background dashboard
work coalesces for 0.1 seconds, obtains a fresh query after the timer and skips
the already performed guide update. Explicit actions/manual refreshes retain
their synchronous behavior; closing/resizing the window defers queued work.

An isolated host replay used the shipped 5,230 quests, a level-23 Horde Priest,
three accepted Wailing Caverns quests, four waiting peers, map ID 0, future
bracket 31–40 and the compact map open. Loading the owned v0.8.27 transport code
and current transport code into separate matching fixtures produced:

| Work across one sync and its send queue | 0.8.27 transport | 0.8.28 transport |
| --- | ---: | ---: |
| Hidden guide-browser scans / dashboard renders | 18 | 0 |
| Catalogue record constructions | 17,964 | 216 |
| Native completion API reads | 17,913 | 1,263 |
| Outgoing packets | 15 | 15 |

Both retained `dungeon:wailing-caverns` and the open map. These are Lua 5.1 host
call counts, not an in-game timing/FPS guarantee. Guide rules, static datasets,
fixed sequence, skips and transport protocol are unchanged. The shared dispatch
frame also reuses successful event subscriptions when a viewer listener replaces
or chains a handler; unsupported first registrations and handler errors remain
visible. The mock returns false on duplicate native registration to exercise
the reported five rejected viewer subscriptions.

`tests/test_0828.py` covers the supplied workload, closed/visible dashboards,
incoming snapshots, fresh batched history, zone/objective events, unchanged
fixed order, chained progress/marker refresh and solo-mode unsubscription.

## Later changes in 0.8.3

The measurements below describe the earlier maintenance pass. 0.8.3 expands
compile-time local search to move short nearby bundles intact; it yields during
search and preserves a selected guide's fixed order. Patrol redraws inspect at
most 1,024 points and draw at most 256 segments for the next three giver steps.
Quest history queries still reuse one synchronous pass. Confirmed ordinary
completions now additionally persist per character/build to resist zone-loading
resets; false and unknown/private results are never persisted as completion.
These are host-checked limits, not a claim about beta FPS or terrain optimality.

## Original 0.6.9 measurements

This pass preserves guide decisions, prerequisite gates, fixed/adaptive route
order, UI/settings and sync protocol/timing. It removes redundant reads and
allocations rather than changing the planner's rules or limiting guide scope.

Measured with the existing Lua 5.1 host fixtures and the shipped 5,230-record
catalogue. The guide fixture is a solo level-12 Horde Shaman in Durotar, with a
60-quest Mulgore compiler/progress workload. The map fixture has 240 stops across
two synthetic zones, viewed on their shared continent map. These measurements
do **not** establish in-game FPS, native API latency or live beta rendering.

| Work per operation | 0.6.8 | 0.6.9 |
| --- | ---: | ---: |
| Dashboard completion API reads | 1,971 | 596 |
| Dashboard party-list constructions | 1,036 | 3 |
| Browser catalogue record constructions | 1,888 | 618 |
| Fixed progress completion API reads | 241 | 60 |
| Compiler map-scale API reads | 367 | 1 |
| Compiler learned-prerequisite lookups | 6,842 | 54 |
| Full-map world/coordinate API conversions | 725 | 163 |
| 20 cross-zone arrow updates: world-coordinate reads | 80 | 40 |

Dashboard completion reads drop about **70%**, and the map fixture's coordinate
conversions drop about **77%**. Counts are more reliable than timing comparisons
on a shared cloud host. Representative sequential warmed median timings were:

| Operation | 0.6.8 (ms) | 0.6.9 (ms) |
| --- | ---: | ---: |
| Browse guides | 27.4 | 16.7 |
| Compile fixed Mulgore guide | 25.3 | 8.5 |
| Update fixed progress | 2.2 | 2.1 |
| Refresh dashboard | 26.1 | 20.5 |
| Redraw full map fixture | 7.1 | 3.9 |

Timings vary with host load; these are samples, not promises for every guide or
client. Guide-list, compiled-step and map-geometry fingerprints matched the
0.6.8 baseline (`2c40bc4`). Separate pre-optimization synthetic fixtures verify
fixed dependencies, missing/external locations and adaptive cost tie ordering.

History/party reuse lasts for one synchronous read pass. Mapping reuse lasts for
one redraw. The compiler clears temporary prerequisite/scale caches whenever it
yields, and learned-rule indexes follow the saved-data revision. Unknown/private
history and unavailable coordinates are queried again on the next update. No
persistent completed/blocked-quest cache or new automatic action was introduced.

Run tests and benchmark sequentially with the prepared environment:

```sh
/workspace/.wow-together-tests/bin/python -m unittest discover -s tests -q
/workspace/.wow-together-tests/bin/python tools/benchmark_addon.py --output /tmp/wow-together-performance.json
```

Keep matching catalogue, settings, fixtures and host conditions when comparing
releases. Test checklist item 25 covers live beta smoothness and state freshness.

## 0.8.36 crafting compartment

A matching Lua 5.1 host comparison with 0.8.35 measured retained startup heap
of 26.41 MiB before and 27.00 MiB after (+0.59 MiB).
The 2,009 recipe facts remain packed by profession until selected. Browsing all
six cards does not unpack their recipe/material/trainer tables. This is host
measurement after collection, excluding native frames/textures and saved data;
it is not a promised beta memory figure. Preview work yields every eight skill
states; recipe/bag updates coalesce and stock reads are shared within a refresh.
