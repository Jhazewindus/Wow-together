# Wow Together changelog

## 0.8.10

- Fix the startup failure caused by the unsupported INN_INFO event, present
  in 0.8.8 and 0.8.9. Observe binder interactions through the modern enum/event
  and the older confirmation event only where supported.
- Validate event support when the native capability API exists; catch rejected
  registrations so other files and features still initialize. List unavailable
  subscriptions in diagnostics without chat warnings. Handler errors still surface.
- Keep hearthstone binding manual. Record a visit separately from a confirmed
  binding; clear stale candidates when a new visit cannot be read. Native home
  detection continues when the binding event is unavailable.
- Reproduce the reported startup failure with a stricter host event mock;
  add full-load, fallback, registration-result and binder-state regression checks.
  Verify startup and inn behavior on the current beta client after updating.

## 0.8.9

- Keep eligible class quests in the full zone-guide sequence. Apply the existing
  Include class quests checkbox to runtime steps and the quest-order preview,
  rather than removing their instructions before compiling the guide. Join
  class-category quests to known pickup zones with unambiguous map data.
- Update the arrow and map immediately when toggled, including with a hidden
  or resizing dashboard. Restore class steps in their original fixed order;
  preserve manual skips, completion credit and prerequisite gates.
- Keep known faction, race and class restrictions. Disabled class work cannot
  bypass the checkbox through accepted quests, ready hand-ins, catch-up or
  NPC auto-accept. Exclude it from newly calculated XP estimates and discovery.
- Recover omitted optional class records from older saved zone guides once on
  upgrade. Add host regression checks and a focused friend-testing checklist.
- Group currently eligible planned pickups within 100 yards of the next pickup
  across guides, using physical map/world scale and the existing nearby-pickup
  toggle. Move only accepts; retain objective/turn-in order and the saved plan.
- Recheck requirements after NPC dialogue without rebuilding the guide. Keep
  unavailable/uncertain, skipped, distant and other-zone pickups out of the hub;
  protect escorts. Auto-accept still requires a real NPC offer.

## 0.8.8

- Name the giver in branching-prerequisite warnings. Direct the current
  confirmation step to its known NPC, with a large addon map star and a
  friendly-nameplate confirmation hint. Preserve pickup gates and fixed order.
- Add Map NPC for that confirmation only. It can set a native Blizzard waypoint
  on supported maps; normal routes still never set one. Clear the owned waypoint
  after confirmation, protecting a different waypoint placed by the player.
- Combine nearby accepted kill, gather and loot tasks into a compact scrollable
  area checklist with independent quest names and live objective counts.
  Grouping is generic across guides, uses a 250-metre radius around the current
  objective and respects pickup/turn-in/travel/zone/missing-location barriers.
- Keep separate drops from the same mob and different members' progress
  distinct. Completed or skipped tasks leave the list independently. Preserve
  guide order, individual skip behavior and quest completion credit.
- Cache the area list between arrow updates and move optional service tips
  below it. Add host regressions and a beta test checklist; native waypoint
  behavior and live layout/nameplates require current-client testing.

## 0.8.7

- Add a small dismissible tip strip below the guide controls, across all guide
  zones with known services. Keep the current quest, route order and arrow intact.
- Suggest a friendly flight master within 150 metres using physical map scale.
  Hide known unlocks; distinguish confirmed undiscovered paths from unknown
  paths that need checking. Replace the previous forced nearby flight-check stop.
- Suggest setting a hearthstone at a nearby inn only when upcoming objectives
  return to that hub for multiple turn-ins. Hide the current home suggestion;
  record actual inn interactions and confirmed manual bindings per character.
- Bundle 49 attributed Forever inn locations, including Zephras Isle, and
  36 taxi settlement labels. Native faction flags settle ownership in neutral
  towns with separate flight masters. Apply the same logic to every guide; unknown
  geography stays unknown. Add independent toggles in Travel routing settings.
- Remember dismissed advice per character, hide tips during combat/flights/
  scans/previews, and reuse position samples between arrow updates. Tips do not
  bind hearthstones, unlock flights, skip quests or change travel decisions.
- Add host regression checks and beta testing steps. Published coordinates,
  native inn events and the new strip still need testing in the current client.

## 0.8.6

- Fix the beta startup error in search boxes by supplying an explicit empty
  font-flags string. Make shared labels use the complete font signature too.
- Allow initialization to finish before later quest, reputation and zone
  events use character identity, quest state and tracker controls; restore
  creation of the minimap button. The reported
  missing-field errors followed the interrupted UI initialization.
- Validate font arguments in the host mock and add startup/event regression
  checks. Preserve the compact UI, guide behavior and saved character data;
  clearing SavedVariables is not required. Confirm startup on the beta client.

## 0.8.5

- Give the guide panel distinct accept, turn-in, kill, gather, loot, buy,
  interact, escort, heal and quest-item instructions, with named targets.
- Show remaining quantities and matching objective progress beside distance.
  Keep separate item goals from the same creature distinct; match named
  tool-use progress such as Peons Awoken through its recorded objective identity.
- Add short action hints and known zone/coordinates beneath the arrow;
  distinguish remote destinations, published patrols and missing locations.
  Never show a planning anchor as a mapped objective.
- Add full fact-based instructions, progress and supplied quest items to hover
  details on guide panels and quest-order rows. Preserve pending-step details
  alongside the existing blocking reason.
- Retain compact panel sizes, fixed route order, routing, automation and sync.
  No new quest locations or unverified landmark descriptions are invented;
  live beta readability still needs testing.

## 0.8.4

- Redesign the interface with matte charcoal panels, fine gold borders,
  Classic headings and clearer body text. Use only built-in game textures/fonts.
- Replace the large main-window banner and stat boxes with a compact header;
  bring filters and search together and give more space to the guide list.
- Reduce guide rows to 122 pixels; remove duplicate zone names and move
  source coverage counts to hover details. Keep quest counts and XP estimates.
- Reduce the movable guide panel from 248 to 168 pixels tall. Place the arrow
  beside the instruction and distance; retain step browsing, skips and Scan.
- Compact settings, quest-order lists and party progress. Keep longer text
  available on hover; reuse only visible quest-list rows when scrolling.
- Style search boxes, dropdown chevrons, close buttons and disabled controls
  consistently. Opening a dropdown closes the previously open menu.
- Preserve existing guide order, routing, quest automation, saved positions,
  party options and smooth resizing. This release changes presentation only;
  confirm game fonts, clipping and readability on the current beta build.

## 0.8.3

- Restrict auto-accept to eligible actual NPC offers in the selected guide;
  leave unrelated quests manual. Preserve explicit dungeon/personal guide support.
- Default quest-objective markers to stars; retain cross, skull and quest ! choices.
  Show published patrol search paths for upcoming quest givers, with a map toggle.
- Preserve the last valid quest-log snapshot during zone loading. Save confirmed
  non-repeatable completions per character/build, so temporary history reads do
  not bring completed fixed-guide steps back after zone entry or reload.
- Count down first flights with labeled estimates; use personal recorded flight
  times after landing. Keep elapsed time when no duration can be estimated.
- Improve fixed route generation by moving nearby bundles intact, preserving
  prerequisite hand-ins, per-quest stage order and escort adjacency.
- Add route-start quest-XP/finish-level estimates to guide information and quest
  lists. Unobserved thresholds use a labeled Classic curve; kills/exploration,
  rested/party effects and unknown rewards remain outside the estimate.
- Require an actual NPC offer for The New Horde while exact race eligibility is
  unresolved. Do not guess race restrictions from the reported recommendation.
- Capture 144 more quest pages and 138 more entity pages; import explicit patrol
  facts. Remaining source needs fall from 485 to 405 quest records. All 77 guides
  pass host invariants; 72 still have source gaps. Repeated source denials stopped
  capture; this release does not claim 98%/100% completeness or beta certification.

## 0.8.2

- Expand all-zone geography from public Forever quest, NPC, object and item
  facts, with pinned source hashes and 46 published outdoor/capital map bounds.
  Keep converted baseline facts distinct from beta observations.
- Add typed event, escort and healing steps; use supplied quest items instead
  of farming them. Shared-credit targets form one objective; retain explicit
  counts and leave absent counts unknown.
- Retain objective counts/item actions in adaptive routes, and shared target
  labels and IDs after a guide reload. Match nearby objectives by target and
  distance so one item's count cannot replace another's.
- Require every parent in AND prerequisites; preserve OR variants and fixed
  route order. Keep escorts together and retain nearby NPC hand-off bundles.
- Preserve current faction/class/race data over older baseline restrictions,
  including unrestricted masks; support explicit Skyborne race requirements.
- Fill narrowly attributed community ground-item coordinates when an exact
  item/zone observation exists. Conflicting reports stay unknown.
- Import missing native Warcraft DB quest-map destinations, including two
  Westfall well-sampling areas. Keep supplied items out of shopping requirements.
- Add a per-guide missing-facts queue and a strict completion audit. This is
  an expanded partial dataset, not a claim that every guide is gap-free or
  terrain navigation is solved. Beta testing is still required.

## 0.8.1

- Prefer a proven source whose creature name matches the requested item, within the same farming zone. Scorpid Worker Tails now point to the published Scorpid Worker area rather than Sarkoth. This applies to item-source selection generally.
- Keep alternative sources, fixed guide order and existing skip credit. A matching name never invents a drop relation or justifies travel to another zone.
- Recheck all zone guides and source-choice regressions. Full data/terrain coverage remains blocked by missing source captures and needs beta testing.

## 0.8.0

- Expand the captured 5,230-quest catalogue: 2,877 mapped pickups, 1,218 objective areas and 3,044 hand-ins. Coverage remains partial; source denials and beta changes still need resolving.
- Join named NPC/mob/item facts, quantities and proven drop/vendor sources. Keep supplied quest items out of farming steps; retain item-use actions and bundle common drop areas.
- Add guarded native conversion for identity-matched unchanged quests. Reject unverified map transforms; retain source/license notices and per-zone coverage.
- Improve fixed route distance while preserving quest stages, prerequisites and NPC hand-off bundles. Keep fixed order during play and saved item-specific skips.
- Separate uncategorized new zones and exclude outdoor crafting categories from leveling. Real beta NPC offers can contradict marked older-world prerequisites.
- Add all-zone host audits and regression checks. Retest coordinates, instructions, loading and NPC actions in the beta; terrain navigation remains approximate.

## 0.7.7

- Fix /wt lua errors when opening, pasting or displaying results: the text-height
  handler called a FontString method on an EditBox.
- Measure wrapped input/output with an owned text label, update the scroll area
  and shrink it again when cleared. Guard unavailable or restricted measurements.
- Add regression checks with native-style text-change callbacks and the correct
  EditBox method boundary. Retest pane scrolling and copying on the current beta.

## 0.7.6

- Group useful selected-guide quests actually offered by an NPC into one pickup
  visit, including when their locations were already known. Respect level bands,
  prerequisites and saved skips; retain fixed objective/hand-in order.
- Save public dialogue pickup locations per build to fill missing pickup points.
  Pending visits resume after reload; availability/completion remain personal.
  Include these approximate locations in manual /wt findings exports.
- Refresh the route immediately on acceptance. Optional selection/acceptance
  collects the next quest when the native NPC list returns; unrelated quests stay manual.
- Add /wt lua: paste read-only API checks/assertions, view tables, returns and
  errors, and copy output. apiType checks actual presence; secret values are hidden.
  Compilation capabilities and NPC dialog behavior need current-beta testing.

## 0.7.5

- Fix known farming locations being discarded when an item has multiple drop
  sources. Keep their coordinates and select one stable area near the quest giver;
  alternatives do not become a required tour of every mob.
- Reprocess the same cached Forever pages: mapped objective coverage increases
  from 196 to 319 quests. Quest count, requirements and source capture stay the same.
- The Battleboars now has a routed Flank farming area; its remaining source gap
  stays explicit. Use your public quest-tracker objective location for an unmapped
  active fixed-guide step when available. Never recycle a published point as proof
  of a missing objective or infer an item drop from nearby mobs.
- Retain fixed step order, completion checks and saved skips when a native
  objective location changes. Quest details distinguish alternatives from missing
  data. Retest actual guide locations on the Forever beta.

## 0.7.4

- Refresh the arrow and map immediately when a flight is learned. Reconsider
  the Orgrimmar gate before choosing directions or selecting a flight.
- Use the same Dijkstra travel decision for directions and auto-flight. A
  walking leg to a flight master names the upcoming flight; a terminal walking
  leg cannot be replaced by a conflicting fallback flight recommendation.
- During an actual flight, show its destination and hide ground route lines.
  Restore ground directions after landing; the selected quest guide is retained.
- Scan guide shows a rotating loop in both arrow displays while checking progress,
  then restores the arrow. History batches yield to the UI. Cancel stale scans on
  guide changes; fixed step order and saved-skip preferences are preserved.
- Host checks cover state and logic. Retest flight actions, map rendering and
  spinner animation on the current Forever beta build; travel times remain estimates.

## 0.7.3

- Skip quest/step updates the selected route, arrow and owned map markers
  immediately, including with the main window hidden/resizing. Clear the old
  travel target; keep saved skips and fixed guide order.
- Apply the close level band to fixed, adaptive, retained quest/circuit and
  current-quest routes. Include current quests no longer bypasses it. Normally
  choose quests from three levels below to three above the lowest synced player;
  retain ready hand-ins, class progression and explained useful prerequisites.
  Filtering does not abandon quests, mark completion or learn a prerequisite.
- Add Path to Orgrimmar in Leveling guides for Horde levels 1–60. Compare known
  city crossings and use the existing travel search for transports/confirmed
  flights. Save across reload, finish on entering the city, and explain unmapped
  connections. Travel times and walking links remain estimates.
- Show the preferred band and lowest synced player in Diagnostics, and the
  band/reason in quest details. Exact beta XP reductions are not inferred.

## 0.7.2

- Fix flight-map detection: use the global GetTaxiMapID(), with a guarded
  visible FlightMapFrame fallback. Never pass a missing or guessed map ID to
  GetAllTaxiNodes. Retry briefly while the map loads; closing cancels retries.
- Recognize character-specific unlocked flight paths from public map discovery
  flags where supported. Refresh on login, zone changes and flight-path discoveries;
  save paths per character, including in solo mode.
- Keep ownership separate from reachable flights. Only actual flight-master
  observations add connections; remove a connection when that master explicitly
  reports it unreachable. Unlock flags alone cannot invent flights or grant access.
- Add probe lines for known paths, mapped locations, observed connections and
  the exact flight-map read result. Unknown/private data leaves flights manual.

## 0.7.1

- Add Solo leveling mode in Play mode settings: stop party messages, hide party
  controls and use only your progress. Local guides, objectives and learning continue.
- Add a gold star above eligible guide quest givers with visible friendly NPC
  nameplates. Its toggle is in Quest markers; markers hide during combat.
- Replace Show route on leveling cards with a scrollable Show quest list: the
  complete pickup/objective/turn-in order and progress, without starting a route.
- Match brackets to useful work in actual leveling areas. Exclude capital pickup
  hubs and sparse level outliers; display the area's main quest band.
- Exclude all seven Collector's Edition Welcome! variants from leveling guides;
  retain them in All quests and preserve the rule when rebuilding quest data.
- Apply low-value filtering to fixed guides as well as adaptive planning. Favor
  closer-level work; keep useful chains, class progression and ready turn-ins.
  Fixed guides also ask before including current quests. Guide order stays fixed.

## 0.7.0

- Add a separately movable standalone arrow toggle in Arrow and map settings.
  It can stay visible with the large guide panel hidden; both share one update.
- Add our own Dijkstra travel search over 256 Forever travel points and 1,620
  directed links: zone crossings, city gates, ships, zeppelins and the tram.
  Adapt geographic data from Mapzeroth with source credit and its MIT notice;
  no upstream routing engine or UI is included. Guide quest order is unchanged.
- Add only character-observed usable flights to the graph, including multiple
  legs. Recheck travel after zone changes/detours and keep transport boarding
  pending until arriving. Map lines break at transport links. Walking segments
  remain estimates, not collision-safe roads; beta retesting is required.
- Fix guide generation crashing on missing turn-in coordinates before a mapped
  follow-up. Exclude retired <UNUSED>/zzOLD quests from leveling plans and ignore
  those steps in retained guides. Repeated Mulgore/Durotar switching is tested.

## 0.6.9

- Performance maintenance with guide decisions, route order, pickup gates,
  settings, UI and sync behavior preserved. Reuse completion reads and party
  lists within each update; build guide records only for matching brackets.
- Index learned follow-ups and avoid build/identity work for unrelated rules.
  Reuse compiler scale/prerequisite reads until its next cooperative yield,
  and compute adaptive tie-break keys once rather than on every comparison.
- Reuse coincident coordinate projections within each map redraw and skip flight
  comparisons when no flight connections are known. The next update reads fresh
  public data; caches do not persist quest progress or restricted values.
- Includes repeatable host benchmarks and baseline route fixtures. Host measurements
  show about 70% fewer dashboard completion API reads and 77% fewer coordinate
  conversions in the large map fixture. Live beta smoothness still needs testing.

## 0.6.8

- Filter recommended and alternative zone guides by actual player level, useful
  quest difficulty and known pickup/prerequisite levels. A broad browser bracket
  no longer makes level-20 work suitable at level 12. Applies across all zones;
  useful earlier chain steps remain included, and All quests keeps future browsing.
- Draw the starting line from your live position, including travel to another
  zone. Public world positions project routes onto zone/continent maps; lines
  clip at zone edges and the arrow continues across borders. Fixed guide order
  stays unchanged. Missing/private coordinates leave gaps and travel instructions.
  Lines show visiting direction; terrain-aware road routing is still needed.

## 0.6.7

- Simplify Leveling guides to one Recommended zone guide and Alternative zone
  guides. Remove duplicate standalone questline cards; chain order and
  prerequisites remain inside full zone guides. Existing selected/shared
  questline guides still work, and search still finds quests inside zones.
- Includes 0.6.6: reload restoration, optional party catch-up, persistent guide
  controls, clean labels, smaller nameplate markers and controls below the map.

## 0.6.6

- Resume the selected guide after /reload or login, using fresh quest progress.
  Preserve the fixed sequence and saved skips; never reopen the map or send a
  new party invitation just for resuming. Clear route removes its checkpoint.
- Offer Catch up party for confirmed useful progression gaps in the current
  zone. Include missing prerequisites and nearby work; keep the current guide
  until accepted. Friends still choose Follow route or Keep my route.
- Improve nearby prerequisite hand-in/pickup bundling for every zone guide.
  Sharing and completion APIs remain separate from pickup eligibility.
- Keep the arrow and guide controls visible during outside-guide questing,
  blocked steps and completed routes. Explicit Clear route still closes them.
- Remove Observed by labels from playing UI. Keep evidence in optional exports.
  Put smaller enemy markers beside their visible name, with a Quest ! style and
  a separate nameplate toggle that leaves item tooltip hints enabled.
- Move route controls below the world map viewport so they do not cover pins.
  Retest the footer in your beta map layout; walking lines still need terrain.

## 0.6.5

- Temporarily defer fixed-guide pickups blocked by actual complete NPC offers or
  known level/prerequisite requirements. Keep every stage in the fixed sequence;
  ordinary progress/NPC events restore eligible quests without a manual Scan.
  Unknown data remains unknown; manual skips and active quests stay separate.
- Fix generic ordering with incomplete objective geography. Missing coordinates
  no longer push hand-ins/follow-ups behind unrelated distant travel. Restart
  a guide after updating; unknown steps retain explicit missing locations.
- Record observed automatic deferrals/restorations and precise manual-skip guide,
  step and level context in local exports. Omit invited-route player identities.
  Missing offers/skips alone never become shared Horde prerequisites or skips;
  clean observed unlock patterns retain account-local build/faction reuse.
- Wait for your own full relevant dungeon collection pickup-level threshold.
  Exclude incompatible identities, repeatables and professions; explain unknown
  requirements and prerequisites. Personal collection routes work without party
  snapshots, and unmapped collections open the entire quest list for review.
- Keep leveling as the focus. Walking lines remain visiting-order connections;
  verified roads/terrain are still needed to avoid mountains.

## 0.6.4

- Reuse ordinary observed prerequisites across classes and races within the same
  faction/client build on this account. Class/race quests or prerequisites keep
  those restrictions. Preserve source attribution and published alternatives.
- Migrate existing findings and merge matching sources/proofs. Conflicting
  predecessors remain disabled for review instead of choosing one silently.
- Correct the tester-reported Mulgore gate: hand in The Hunt Begins (747) before
  picking up The Hunt Continues (750). Fixed/adaptive guides use the same gate;
  imports preserve the correction and identify its tester provenance.
- Record manual step/quest skips as separate export events. Explain in tooltips
  and diagnostics that skipping alone does not learn a prerequisite or prove
  NPC absence. Live learning still needs a clear observed hand-in/new-offer pair.
- Keep running fixed-guide order stable; newly started guides use learned gates.

## 0.6.3

- Fixed zone/questline guides are now the default: compile the complete sequence
  once, then advance progress without changing order on pickup, hand-in, abandon,
  travel or Scan guide. Adaptive trips remain optional in settings.
- Show full route covers all currently eligible mapped quests, beyond the old
  trip limit. Keep fixed step numbers; draw other zones without false connections.
- Show separate pickup/objective/turn-in coverage. Add 253 detailed quest pages
  across zones: 1,619 detailed records; 905 pickups, 196 objective areas and 972
  turn-ins mapped. Some source pages/coordinates remain unavailable.
- Learn tentative prerequisites from one clean full-list/hand-in/new-offer pair.
  Matching characters on this account reuse them; influenced steps credit the
  source. Live contradictions disable them; published alternatives stay intact.
- Export guide findings and supporting evidence with /wt findings or settings.
  Source names are optional; raw research exports omit names. No automatic upload.
- /wt questlines displays public native questline fields and optional chain IDs
  in a copyable window. Retest API results on the current Forever build.
- Fix the 20-ID party invitation bound when sharing large complete guides.

## 0.6.2

- Remove the incorrect IsPushableQuest pickup gate, setting and packets.
  IsQuestCompletable remains for opened turn-in dialogs only.
- Check known prerequisites before every pickup in all route modes. Accepted,
  ready or skipped prerequisites and positive offers cannot bypass a hand-in.
  Alternative prerequisites need a real completion; unknown history stays unknown.
- Retain locked future quests and accepted work. Event sync rechecks unlocks.
  Actual NPC lists can confirm missing requirements; fresh peer offers stay
  separate. Opening one dialog preserves a prior complete list in the same context.
- Clear invalidated pickup markers and guard optional guided dialog selection.
  Diagnostics now show per-character requirement reasons and NPC evidence.
- Record the latest 300 local NPC-offer/acceptance/turn-in observations per
  character, with build, history, level and reputation-change context. Identify
  recommended pickups missing at an NPC; infer no automatic new prerequisites.
- Use /wt research or Settings → Quest data for testing to copy an export for
  feedback. Recording can be disabled; exports omit character names/chat and
  are never uploaded automatically. The test checklist covers before/after visits.

## 0.6.1

- Browse full zone guides and published questlines across the catalogue, with
  level brackets, deferred search and pages. Single quests stay in All quests;
  explicit quest-log trips move to Party quests.
- Keep a full guide's later levels and known cross-zone chain steps. Offer an
  optional next-zone guide when party level/progress fit; Keep my guide preserves
  the selection. Full-guide invitations identify the same plan for friends.
- Generate nearby trips asynchronously with Loading route in the arrow.
  Compare dependency-ready walking orders, retain each trip through pickups,
  then select later work as progress unlocks it.
- Read native quest-greeting offers as well as gossip. Public NPC absence blocks
  unavailable pickups in the current progress context; restricted data stays
  unknown. The exact unpublished scorpion prerequisite still needs beta evidence.
- Enable the user-tested IsPushableQuest beta pickup gate, with a settings switch.
  Recheck unlocks automatically and sync each character's own results; accepted
  work stays in the guide and nearby new pickups can join the current trip.
- Stop setting the extra Blizzard waypoint pin; keep numbered route markers,
  lines and the navigation arrow. Remove the Guide replanned footer.
- Expand detailed outdoor data to 1,366 pages; preserve unresolved zone points
  for safe native-name matching. Locations and hidden gates remain partial.
- Add guide/trip/stop diagnostics and all-zone, cross-zone and greeting tests.

## 0.6.0

- Keep the chosen guide through quest acceptance and zone changes. Scan guide
  now replans real progress without a report popup; optionally reconsider skips.
- Filter low-level pickups, explain useful chain/dungeon exceptions and focus
  party routes on the member behind in known progression.
- Refresh Classic-style panels with grouped settings and dropdowns. Rename
  Library to All quests and the old All quests to Party quests.
- Add a current-quests choice at guide start, previous/next previews, yards or
  metres, automatic party-panel visibility and dungeon Start route.
- Distinguish Kill, Pick up and Talk instructions. Add cross markers/item hints,
  observed NPC pickup availability and opt-in selection of the current NPC quest.
- Add observed flight-network suggestions, flight clocks and optional flight
  selection; show corpse directions while retaining the guide. Beta testing is
  required for the new APIs/actions; unknown data keeps travel manual.
- Add quest-log review suggestions and expand the friend test checklist.
  Known repeatable filtering is retained; the reported repeatable was already fixed.

## 0.5.7

- Keep known repeatable quests out of automatic leveling plans, including
  **Spirit of the Wind**. They remain available in the quest library.
- Add **Skip step**, **Skip quest** and **Scan guide** to the arrow. Skips are
  saved per character; settings can reset them. Starting a guide checks its
  quests, known series and prerequisites against real progress/history.
- Remove skulls for completed mob objectives without letting the generic
  quest-related flag restore them. Other unfinished objectives stay marked.
- Redraw unprotected addon map geometry during combat pan/zoom. Protected
  drawing and native waypoint/map actions still wait until combat ends.
- Add the recurring Discord release command with matching archive/docs and
  confirmed-post receipts to prevent duplicate uploads.

## 0.5.6

- Focus map lines and markers on the current place and two ahead. Map controls
  switch to the full route or choose zero, one or two places ahead.
- Prioritize mapped active quests over discovery; finish local work before
  distant deliveries. Improve objective walking order without moving returns
  ahead of their work.
- Keep cross-zone routes, explain the next stop under the arrow, and add
  **View route zone** when viewing another map. The first leg follows your
  current public position; quest progress advances the preview.
- Add opt-in turn-in for opened NPC quest dialogs with no reward choice.
  Reward choices remain manual; beta action compatibility needs testing.

## 0.5.5

- Fix the general **Vile Familiars** being blocked behind a Warlock-only
  introduction. Parallel class variants now keep their own prerequisites;
  **Burning Blade Medallion** still requires its completed prerequisite.
- Include a friend-testing checklist and copyable bug-report template.

## 0.5.4

- Bundle eligible nearby pickups with current party quests, within the walking
  budget. Ready turn-ins stay first; missing objective locations stay partial.
- Add a nearby-pickup setting and retain pickup stages in shared party routes.

## 0.5.3

- Smooth main-window resizing and add **Start route**, with **Follow route** /
  **Keep my route** invitations for friends.
- Improve prerequisite, faction and nearby-zone checks; name NPCs on arrival.

## 0.5.2

- Add **Finish our current quests first** and prioritize ready turn-ins.
- Repair world-map projection, clipping and clustered route pins.

## 0.5.1

- Add the movable navigation arrow for a selected route.

These are beta releases. The testing script checks actual client behavior;
host tests alone do not establish that every API or drawing path works.
