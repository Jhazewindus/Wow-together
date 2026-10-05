# Performance maintenance — 0.6.9

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
