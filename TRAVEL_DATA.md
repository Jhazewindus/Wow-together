# Travel routing — updated for 0.8.45

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
- 48 settlement footprints bound the source's town/city centers, their scoped
  service locations and same-map flight points; an estimated 100-yard margin is
  applied using public physical map sizes. These are approximate occupied areas,
  not measured guard boundaries. Missing/private scales retain literal bounds.
- Retail data, service POIs, class spells/items, race portals and unconfirmed
  flights are excluded as travel/action nodes. Scoped service coordinates only
  contribute settlement footprints. The upstream engine, actions and UI are not used.

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

Version 0.8.20 uses town/city ownership to repair 26 missing flight-point labels.
Full ground-segment intersection checks apply to Dijkstra links and local map
previews, including projected cross-zone lines. Cached points and legacy flight
approaches/exits use the same ownership/crossing rules. Friendly and neutral
settlements do not block travel; a neutral town alone does not identify ownership
of its separate flight masters. Air/boat rides are not ground crossings.

When a walking segment crosses an approximate enemy footprint, the search may
use another existing published connection. No detour points or road geometry are
invented. If no bypass is known, hide that ground line and show a caution instead
of a straight arrow through town. Keep the real quest marker and guide progress.
Leaving an enemy area and intentionally visiting a real destination inside it
are permitted; such quest work is never automatically skipped or completed.
This reduces known hostile-town shortcuts, but does not establish guard-safe or
terrain-safe routing. Public projected coordinates and current faction are used.

Executable flight access remains per character. Only links observed as reachable from an
opened flight map enter the graph; sourced taxi coordinates never unlock flights.
Measured personal flight times replace estimates where available. Saved flight
points projected onto outer zones retain their city-map identity in the graph,
so they cannot supply a walking shortcut through city walls. Native reachable
slot checks and the existing opt-in auto-flight/combat safeguards remain in place.

## Nearer unlearned flight masters — 0.8.45

The same pinned Forever snapshot's `Flights.lua` contributes **266 directed,
faction-scoped reference legs**, preserving their supplied estimated flight
seconds. Its SHA256 is
`69da48451cef3cbf66c2514984ad89d6484fcc4cf300b11c297968d7996e8111`.
Only numeric taxi endpoints already in the retained point graph qualify. No
upstream engine, generator, UI or flight actions are included. Reference links
also supplement missing master ownership; 61 of 71 native-ID points now have
published ownership. Ratchet's shared Bragok master is explicitly neutral,
corroborated by [Bragok's public faction reactions](https://warcraft.wiki.gg/wiki/Bragok).
Native public ownership takes precedence. Separate faction masters in neutral
towns are not assumed neutral. The source is a partial reference, not a complete
or currently beta-verified flight database.

A separate prospective Dijkstra calculation prices a visit to one unlearned
departure. Every landing/intermediate master must already be unlocked by this
character; directed faction-compatible reference or confirmed personal links
must connect them. It prices connecting tickets with one 45-second boarding
allowance. Personal confirmed durations take priority where available. This
calculation never alters the executable graph, unlock flags or guide order.
Native explicit unreachable results exclude the corresponding reference
connection, persist for this character/build and clear on a reachable reread.
Changing builds clears those negative reference overrides.

Compare at most three nearest friendly candidates within 750 metres, excluding
known hostile crossings and masters already visited or dismissed for this goal.
When the known journey starts with a flight, the candidate must be at least
30 estimated yards closer than its departure. A check needs more than the
larger of 30 seconds or 10% of the baseline journey in savings, after a 20-second
visit allowance. If its menu offers nothing useful, the estimated known-route
fallback may add at most 150 seconds. Walking uses current speed and existing
detour factors, not certified roads. Cache by goal, travel revision, faction and
speed; reconsider after 125 estimated yards of movement, comparing fresh journey
costs. A held ship/zeppelin crossing cannot be replaced by a discovery check.
This is a bounded
comparison, not exhaustive optimization across all unknown masters.

A qualifying visit becomes the transient arrow destination. The text says
Check flights and gives potential savings; the line draws only the walk to the
master, never an unconfirmed airborne connection. Keep walking, or the check's
standalone strip ×, dismisses the visit without a quest/step skip. Opening the
native map replaces the estimate with actual reachable flights. Existing
auto-flight still requires a currently reachable visible slot. Fixed quest
sequence and the actual destination markers are retained. Both flight routing
and nearby-flight tips must be enabled. Checks pause in combat, flight, corpse
recovery, scans and previews; profession/trainer guides retain their own travel.
Host checks reproduce Ratchet 60.3, 38.7 with synthetic physical transforms;
actual beta connections, timings, map drawing and terrain need tester validation.

## Flight duration — 0.8.23

Version 0.8.33 compares the same level-25 Horde tester's Thunder Bluff probes on
build 70235. Before opening the menu there were 14 saved connections; afterward
there were 19 and a Thunder Bluff → Orgrimmar leg. The selected Hillsbrad guide
also changed from including current quests to its ordinary scope, with a different
final quest. Counts do not identify which individual cached link was lost. These
reports establish the difference, not the exact original cause. Confirmed code
weaknesses are addressed: weaker
`isUndiscovered` map flags no longer erase menu-confirmed reachable flights, and
missing live geometry no longer omits a confirmed flight if a duration estimate
is available. An explicit unreachable result on the source menu can still remove
that directed connection. Unlocks alone never add edges; automatic selection
still requires a currently reachable visible slot.

Duration fallback order is current public geometry, saved public same-continent
world positions, then directed published walking-distance totals between taxi
nodes. The latter only prices an already confirmed airborne edge; it cannot add
a flight or ground shortcut. Non-walk links are excluded from that lookup, whose
graph and maximum eight source rows are bounded and dataset-scoped. Validated
same-build/route samples retain priority. Arrival validation still uses actual
native GPS; estimated distances cannot validate a timing sample.

Directions describe the first remaining non-walking connection, including a
zeppelin before a later Eastern Kingdoms flight. Within 40 estimated yards of
the boarding point, keep ship/zeppelin/tram directions through movement, zone
discovery and unavailable GPS, suppressing a bearing back to the dock. This
does not establish boarding or arrival. Advance only at a public position on the
destination map within 100 estimated yards. Scan releases/replans the crossing;
changing/stopping guides clears it. Transport map lines keep a gap. Beta tests
are still required. Diagnostics report restored connections and ignored conflicts.

Romits reports reliable walking ETAs and inconsistent flight ETAs, with no exact
trip or version supplied for this report. Code inspection identified distance-only
estimates, event-order capture gaps and no destination check on prior samples.
These are confirmed implementation weaknesses; they do not establish the cause
of his specific trip. Walking speed/time calculation is unchanged.

Read-only native `GetNumRoutes(slotIndex)` and
`TaxiGetNodeSlot(slotIndex, routeIndex, isSource)` expose the connecting taxi
stops used by Blizzard's Forever flight-map renderer. Capture only complete,
contiguous routes through public visible slots, bounded to 32 legs. No inferred
route unlocks or intermediate edges are added. Sum connecting-stop geometry
for untimed flights, retaining the earlier estimated 32 yd/s and 1.35 detour
factor. Share geometry caches with the graph. This approximates intermediate
stops, not the actual airborne curves; a missing/private/invalid route uses
the straight-distance estimate. Both remain labelled estimates.

Source: [Forever UI snapshot a84e2b1b41d3d4137127c07e4da448aa3251d6f1](https://github.com/Gethe/wow-ui-source/tree/a84e2b1b41d3d4137127c07e4da448aa3251d6f1),
`Interface/AddOns/Blizzard_FlightMap/FM_FlightPathDataProvider.lua`
(`HighlightRouteToPin` uses GetNumRoutes/TaxiGetNodeSlot; OnClick uses TakeTaxiNode)
and `Interface/AddOns/Blizzard_UIPanels_Game/Shared/TaxiFrame.lua`. API signatures
are verified in this source; availability/results on the running beta still need
the capability probe and tester validation. No Blizzard UI implementation is copied.

An observed selected departure starts the clock. Control-event state lag gets
up to 20 retries at 0.1 seconds; existing visible navigation updates can also
notice landing. Recording works with both panels hidden when the native events
arrive. A one-second read-only visible-slot snapshot handles the native map closing
before the TakeTaxiNode post-hook; it is never used for automatic flight actions.
A selected request older than 30 seconds cannot attach to another flight.
Only a public non-taxi state, duration between 1 second and 2 hours, matching build,
and landing within an estimated 300-yard tolerance of the selected flight master
permit a timing sample. Missing/late GPS gets the same bounded retry window, using
the original landing time so postflight walking is excluded. Early/unknown arrivals
and death are not measurements. Reload during a ride loses the departure context;
partial rides are not learned. Samples/flight networks remain personal.

Validated timings include build and directed native route signature. A changed
build or different/unknown previously captured route uses an estimate until timed.
Earlier unverified samples are retained for inspection but excluded from planning
and countdowns, then replaced by the first validated ride. Subsequent matching
samples update the existing bounded rolling mean. Both route solvers and both
timer panels share this provider. This improves consistency without promising
exact first-flight times. `/wt probe` reports capabilities, sample/route counts,
selected estimate basis and last expected/actual timing.

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
Unscoped locations are excluded. Supported binder interaction events can record
a new inn for this character; HEARTHSTONE_BOUND records a manual binding. INN_INFO
is not registered. These native events and published coordinates still need
current beta verification.

Flight tips require a friendly known location within 350 metres, or up to 750
metres ahead when its visit adds at most 200 metres of estimated walking to the
current navigation leg. Inn advice retains its 150-metre range. Published
coordinates/ownership do not establish unlocks: confirmed unknown-to-character
paths say Get, unconfirmed states say Check, and known paths are hidden. Inn tips
require upcoming work away from the hub followed by at least two distinct nearby
turn-ins among the next 48 guide stops. Tips do not supply travel graph edges,
change quest order, select flights or bind homes. Disabling/dismissing them does
not skip any quest. Each type has its own Travel routing toggle.

Version 0.8.43 fixes the settlement-label-only discovery loop: all **71 native-ID
taxi points** in the existing attributed travel snapshot are considered, plus
client-observed masters. The remaining published symbolic taxi point has no
native ID; its unlock cannot be checked, so it stays outside discovery advice.
This is catalogue coverage, not proof that every Forever flight master is mapped.
Native public ownership and positions take precedence, with source ownership as
fallback; missing ownership is never guessed from a neutral settlement. Public
continent observations can be projected onto the current zone, using the existing
map/world transform. Private/missing scale/position/faction data cannot produce
a reminder. Known paths and masters already confirmed current are excluded.

The Stonetalon screenshot places the player at 49.6, 61.0; the published Sun Rock
taxi is at 45.16, 59.89. The former 150-metre radius can therefore exclude a
master that looks close on the zone map. Synthetic checks reproduce this with
an explicit physical scale; no live probe was supplied to establish the exact
cause/distance on that client. The standalone arrow also previously exposed tips
only on hover. Both visible layouts now name the stop and explain future travel
benefit. Opening its native map confirms unlock/reachability as before; discovery
advice does not add flight edges or change guide steps. Hostile ground crossings
are excluded using the same approximate footprints as travel routing. A short
detour uses geometric distances, not certified walkable roads. Cache keys include
the current leg and travel revision, reusing the existing navigation updates.

Version 0.8.21 extracts **151 class-trainer locations**, covering classes
1/2/3/4/5/7/8/9/11, from that same hash-verified POI snapshot. Explicit NPC faction
takes precedence over scoped settlement ownership; unknown ownership is excluded.
NPC IDs and optional settlement labels are retained. Existing quest-entity names
identify known NPCs; otherwise the label names the trainer's class. Profession,
pet, demon, weapon and riding trainers are excluded. These are location facts,
not a spell/rank schedule, proof of accessible terrain or trainer level caps.

The optional personal training step becomes due every even level. It may appear
near a pickup/return or just before leaving a known hub for distant work. It
requires public class/faction/position and physical distance within 150 metres,
with at most 150 game yards of **estimated** extra walking. Hostile settlement
checks apply; map/world geometry determines distance rather than raw normalized
coordinates. No new polling loop is added, and failed candidate checks are cached
briefly. Done/Skip acknowledgements and pending visits are saved per character;
the original quest plan, skips, credit and party data remain unchanged. Skills
are bought manually. Full-map preview includes T beside the retained quest stops.

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
