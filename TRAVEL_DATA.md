# Travel routing — 0.7.0

Wow Together implements its own Dijkstra search with a binary heap, deterministic
ties and nonnegative travel-time costs. It finds a path **between quest steps**;
it does not reorder the fixed zone guide or change quest credit. A separately
movable arrow is available in **Settings → Arrow and map**. The large direction
panel and standalone arrow have independent visibility and positions.

The bundled point graph is adapted from [Mapzeroth](https://github.com/tr0tsky0/Mapzeroth),
Forever 0.6.0 at commit `fd68cfe2153379898680c66a01833846f9933587`:

- 256 zone-border, city-entrance, flight-master and transport points.
- 1,620 directed walking/transition/ship/zeppelin/tram links.
- Kalimdor, Eastern Kingdoms and Zephras Isle; coverage is partial for new zones.
- Original node coordinates, container boundaries, directional transport links,
  known faction restrictions and estimated geometry/time costs are retained.
- Retail data, service POIs, class spells/items, race portals and unconfirmed
  flights are excluded. The upstream addon engine, action code and UI are not used.

[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) preserves the project's published
MIT notice. [TravelData.json](WowTogether/TravelData.json) records source revision,
input hashes, exclusions and limitations. The reproducible adapter runs selected
data files in a namespace-only Lua sandbox without game, filesystem or network APIs:

```sh
/workspace/.wow-together-tests/bin/python tools/import_travel_network.py /path/to/pinned-mapzeroth-checkout --license-file /path/to/published-MIT-LICENSE
```

The published walking geometry joins points within containers and uses measured
or estimated detour factors. **It does not contain detailed road polylines or a
collision/terrain mesh.** This improves crossing, gate and transport selection;
walking between these points can still need human road/terrain judgment. Local
quest-to-quest segments and uncovered areas retain direct directions. More road
samples are needed to avoid arbitrary mountains within each zone.

Flight access remains per character. Only links observed as reachable from an
opened flight map enter the graph; sourced taxi coordinates never unlock flights.
Measured personal flight times replace estimates where available. Saved flight
points projected onto outer zones retain their city-map identity in the graph,
so they cannot supply a walking shortcut through city walls. Native reachable
slot checks and the existing opt-in auto-flight/combat safeguards remain in place.

Costs use current public ground speed, imported walking-distance estimates and
transport estimates, including their supplied loading allowance (10 seconds per
loading screen). Boat wait/ride times vary. Ordinary travel remains manual: walk,
board the indicated transport and select a flight unless existing auto-flight is
enabled. There is no auto-walking, portal casting or boat interaction.

Version 0.8.7 adds optional guide advice separate from Dijkstra routing. The
same pinned `Data/Forever/Pois.lua` supplies 49 scoped inn locations and 36 taxi
settlement labels. `GuideServiceData.json` records its SHA256 and scope;
reproduce with `tools/import_guide_services.py /path/to/pinned/Pois.lua` under
the test Python environment. The adapter verifies the source hash and extracts
facts only, with no upstream runtime/UI. Inn ownership follows its settlement.
Neutral towns do not establish flight-master ownership: their separate faction
masters need native public ownership flags before tips can recommend a visit.
Unscoped locations are excluded. A public INN_INFO interaction can record a new
inn for this character; HEARTHSTONE_BOUND records a manual binding. These native
events and published coordinates still need current beta verification.

Flight tips require a friendly known location within 150 metres. Published
coordinates/ownership do not establish unlocks: confirmed unknown-to-character
paths say Get, unconfirmed states say Check, and known paths are hidden. Inn tips
require upcoming work away from the hub followed by at least two distinct nearby
turn-ins among the next 48 guide stops. Tips do not supply travel graph edges,
change quest order, select flights or bind homes. Disabling/dismissing them does
not skip any quest. Each type has its own Travel routing toggle.

Zone changes and significant detours refresh the travel path while keeping the
quest step/order. Arrival at a walking waypoint advances only travel directions.
Reaching a dock does not count as taking its boat; directions remain there until
the destination is reached. The current travel path supplies the first map leg;
later quest markers remain guide previews. Lines break for transport rides rather
than depicting a walk across the sea. Lines do not draw on the minimap.

Public scale/coordinate reads are reused within a single search, not persisted.
Missing/private positions are retried; unsupported maps retain normal quest
directions. No remote service is contacted by the addon. The source data records
community observations and estimates. We have not retested its endpoints or
native map behavior in the Forever beta; checklist items 26–28 cover this release.
