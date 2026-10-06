# Performance maintenance — 0.6.9

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
