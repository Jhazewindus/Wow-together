# Wow Together changelog

## 0.8.61

**SESSION CHECKPOINTS AND DUNGEON TRACKING**

- Add **Pause** to the small guide window and **Session** to Recommended.
  Save & pause stops the guide and keeps a resumable checkpoint. Resume checks
  current quest/crafting progress and retains same-version fixed order and skips.
  Paused guides wait for Resume after login; running guides still resume normally.
- Add a live position/facing marker on exact native dungeon floors when the
  client supplies public coordinates. Locate me refreshes the map and follows
  your floor. Boss/floor browsing suspends following; movement repaints only
  the marker. Missing/private coordinates or reference-only art keep the map
  static, including in combat. HiddenMaps itself documents static interiors;
  this is native support, not a claim that Forever exposes every interior.
- Show a compact personal summary of actual XP, unique quest hand-ins, played
  time and level change. Normal reloads continue the summary without offline
  time/XP. Pausing, stopping or changing guides finishes that session. Missing
  native XP/time stays unavailable or partial; level notifications do not count
  the previous level's XP twice. No leveling estimates enter these totals.
- Keep one guide blueprint plus at most two small summaries per character.
  Stop/Exit still discard an active guide; closing an already-paused window
  preserves its checkpoint. The latest summary remains accessible in Recommended.
  Resize/move the summary using the existing window controls. WoW normally
  flushes SavedVariables on logout/reload; crash recovery is not guaranteed.
- Include the guide branch's initial Dun Morogh coverage review and scoped audit
  checks. Review through 8371d24: Durotar/Mulgore and the expanded Dun Morogh
  source corrections remain drafts. Route comparisons flag delayed rewards,
  log/XP tradeoffs; class/race eligibility and cross-zone handoffs need review.
  Preserve those guards and current route fundamentals while those drafts await
  a coordinated compiler decision.
- Validation: 273 related host checks pass, including 23 session checkpoint,
  native-XP, offline-time, crafting, stop/resume and UI checks, plus eight scoped
  coverage checks, 14 new native tracking checks and 40 dungeon viewer/marker
  regressions. All 86 Lua files compile under Lua 5.1. Native position/event
  delivery and live UI/save behavior still require the attached beta checklist.

## 0.8.60

**INVENTORY-AWARE SERVICE STOPS**

- Add optional nearby vendor advice when four or fewer regular bag slots remain,
  or an equipped item reaches 25% durability. Optional food/drink advice tracks
  common level-appropriate supplies; mana classes get drink reminders. Choose
  a restock target of 10, 20 or 40 in Settings → Bags, repairs and supplies.
- Learn vendor locations, repair capability and common supply stock from actual
  merchant visits. Reuse those observations for compatible characters on the
  same realm/build/faction. Inn/trainer locations never imply vendor services.
  New characters need a vendor visit before that location can be suggested.
- Show a compact tip beneath either arrow. Click to visit: the arrow and map
  temporarily point to the vendor, with the reason and estimated amounts to buy.
  Done or Skip visit resumes the unchanged quest plan; resolving the recorded
  needs also resumes it. Purchases, sales and repairs remain manual.
- Dismiss a need until it recovers; keep character dismissals separate from
  quest skips and research. Save accepted visits across reloads, and clear them
  when stopping or switching guides. Suspend detours during combat, flights,
  ghost travel, previews and loading. Crafting retains its own material guide.
- Limit advice to nearby vendors with a short estimated detour and existing
  hostile-crossing checks. Inventory reads are event-batched, never performed
  by the movement repaint. Turning the feature off stops its inventory reads.
- Validation: 230 host checks pass, including 29 dedicated inventory, compatibility,
  manual-transaction, UI/map and unchanged-progress checks. All 84 Lua files
  compile under Lua 5.1. Native merchant/bag API behavior and actual paths still
  require the attached beta checklist.

## 0.8.59

**DUN MOROGH CHAIN FIX**

- Add the reported missing prerequisite: hand in Treacherous Cold before
  picking up Rime's Wrath. Fixed guides now place its pickup, all objectives
  and turn-in before the follow-up; adaptive pickups use the same shared gate.
  Merely accepting the prerequisite or finishing its objectives does not unlock
  the next quest. All 151 Dun Morogh 1–10 guide actions remain.
- Retain the identity-checked correction and tester provenance for future data
  rebuilds. It applies to compatible characters, rather than only the reporting
  dwarf/class. Preserve all other quest data, locations and character progress.
  Installing this version rebuilds saved guide order; manual skips remain saved.
- Validation: 126 related host checks pass, including six new prerequisite,
  identity/conflict, cross-character and fixed/adaptive route checks. Audit all
  152 guide sections and 11,822 source points; all 83 Lua files compile under
  Lua 5.1. Confirm actual NPC offers with the short beta checklist attached.

## 0.8.58

**BETTER TRAVEL CONNECTIONS**

- Correct nearby connection ranking in guide-cost comparisons. Mixing raw
  distance with adjusted cost could discard a nearer connected point and call
  a reachable leg unmapped. Keep the same bounded search and safety checks;
  generic compilation still does not assume personal flights or hearths.
- Compare corrected prices after the complete established quest flow, including
  its terrain-aware reward visits. Change order only for a shorter full journey
  that preserves every action, prerequisite, escort, endpoint and recovery
  boundary. No work loses previously collected rewards; log, level, difficulty
  and shared-kill guards remain. Started guides keep fixed order.
- Compare all 152 sections and 12,985 actions with 0.8.57. Published Forever map
  bounds support 25 guarded changes in 13 sections; 139 retain their order.
  Barrens 11–20 collects The Forgotten Pools reward earlier and combines nearby
  work without delaying existing rewards. Durotar, Elwynn and other sections
  also improve. All 608 additional bracket/starting-XP replays pass.
- Repeat the comparison without native physical map geometry: 13 changes in
  seven sections, using explicitly estimated fallback scale. Preserve all
  actions and 608 state replays there too. Record full named old/new sequences
  and both geometry modes in GuideFlowAudit.json; Connection ordering appears
  only in diagnostics. No new world/NPC/road locations are claimed.
- Validation: 278 related host checks pass, including six new connection,
  source-name-order, cache, directed-transport and reward-preservation checks.
  Audit all 152 sections and 11,822 published points; all 83 Lua files compile
  under Lua 5.1. Source completeness remains 33 sections; 119 need more facts.
  These are improved estimated journeys, not proven fastest or gap-free routes.

## 0.8.57

**TERRAIN-AWARE QUEST FLOW**

- Price guide alternatives through the mapped terrain waypoint graph used by
  live navigation. Reject crossing local chords, point attachments and walking
  links. Keep directed ordinary transports; generic guides never assume a
  personal flight/hearth. Missing lift/ramp approaches remain unresolved.
- Preserve established pickups/objectives, useful early rewards and onward
  endpoints before comparing terrain-aware changes. Retain prerequisites,
  escorts, log/XP/difficulty/kill guards and recovery boundaries. Do not delay
  known reward XP before work. No live reordering after a guide starts.
- Compare all 152 sections and 12,985 actions against 0.8.56 with identical
  published Forever map bounds and source facts. Two guarded changes improve
  two sections; 150 retain their order. Hypercapacitor Gizmo's work joins a later
  Thousand Needles visit; The New Frontier's pickup moves within the Moonglade
  guide's onward journey. All 608 extra bracket/starting-XP replays pass.
  Without native geometry, all 152 sections retain their previous order.
- Keep bounded compilation caches and cooperative loading. Terrain comparisons
  are separate in diagnostics and GuideFlowAudit.json. Default flight-distance
  lookups and the imported source graph remain separate from terrain pricing.
- Batch small loading yields within a 3 ms budget and at most 16 resumes per
  callback, reducing timer-frame overhead. Missing/private/invalid timers keep
  the previous single-resume behavior. Preserve cancellation and job errors.
- Validation: 1,417 broad host checks pass; 272 final targeted checks pass,
  including 20 new checks for visible bends, hidden/zero-cost crossing
  shortcuts, unknown approaches, map projection, transports, personal flight
  assumptions, cache isolation, cooperative loading, established rewards,
  scheduling budgets, cancellation and missing/private timers.
  All 83 Lua files compile under Lua 5.1. Terrain coverage is still twelve
  approximate Thousand Needles footprints; 119 guide sections still need source
  facts. These are estimated improvements, not proven fastest/gap-free routes.

## 0.8.56

**TERRAIN WAYPOINTS**

- Route the live arrow and map line around mapped terrain footprints using
  intermediate waypoints. Apply barrier checks to graph links, player/goal
  attachments and direct local shortcuts; distant travel points cannot bypass
  a known mesa. Keep waypoints stable while walking along a segment, advance
  only when the next corner is clear, and reattach after an actual detour.
- Add twelve approximate Thousand Needles mesa outlines reviewed against the
  Classic zone artwork. Reuse static visibility; read current public coordinates
  for each calculation. This is initial terrain coverage, not an elevation or
  collision mesh. Other mountains/approaches still need mapping and ground tests.
- Hide unrouted preview chords crossing mapped barriers while keeping quest
  markers. When a mapped mesa's lift/ramp/entrance approach is unknown, show
  brief advice without a walking arrow through its wall. Local work atop the
  same mesa still works. Preserve guide order/credit, confirmed personal flights,
  directed ships/zeppelins and transport line gaps. Legacy flight suggestions
  cannot bypass the same ground checks.
- Validation: 209 relevant host checks pass, including 17 new checks for shortest visible bends, stable movement,
  corner clearance, detours, public/private positions, cross-zone projection,
  map geometry, barrier endpoints, known flights and directional transports.
  All 83 Lua files compile under Lua 5.1.
  Actual silhouettes, approach locations and rendering require Forever beta
  ground testing; see TESTING.md and TRAVEL_DATA.md.

## 0.8.55

**SMALL CRAFTING STEPS**

- Craft the affordable portion as soon as bags cover it. Four Light Leather
  can become four Light Armor Kits without buying the whole milestone first.
  Check all required reagents together; the scarcest reagent limits the count.
  Use the same behavior for Alchemy, Blacksmithing, Enchanting, Engineering,
  Leatherworking and Tailoring, including intermediate preparations.
- Buy/gather for work toward at most five skill points before the next recipe/
  color/cap milestone. Estimated craft counts still depend on current skill,
  recipe color and points per successful gain. Smaller purchases work too.
  Recheck actual skill and remaining stock after crafting; failed skill-ups do
  not finish a step. Next-batch Materials follows the current work; the full-goal
  forecast and auction price scan remain available separately.
- Remove repeated crafting descriptions from the arrow hover and context.
  Show the action, current skill/goal and one short instruction. Local crafting
  no longer says its quest location is missing or asks for the quest tracker.
  Trainer destinations retain their rank/recipe explanation and coordinates.
- Validation: 177 relevant host checks pass, including 13 new checks for partial supplies, preparatory work,
  all six professions, native reagent amounts, shared stock, skill gains,
  reload, hover updates and trainer-trip explanations. All 81 Lua files compile
  under Lua 5.1. Native bag/recipe events and visual layout remain Forever
  beta-client checks.

## 0.8.54

**BETTER TRAVEL ORDER**

- Compare published travel connections after the existing pickup/work/hand-in
  flow passes. Reuse the bounded step and bundle search. Accept a change only
  when the complete guide's estimated travel improves; every changed leg must
  use a published connection or a short local estimate, with at least one
  changed connection involving the network. Unmapped shortcuts are rejected.
- Replay each viable change against all required actions and onward endpoints.
  Keep prerequisites, escorts, recovery boundaries, quest-log peak, known level
  shortfalls, required-kill lower bounds and total rewards. Do not delay known
  reward XP before another objective. Check the bottom/middle/top bracket and
  a partly filled XP bar, including possible later grey-quest reward losses.
- The identical-source comparison retains all 12,985 actions in 152 sections:
  142 travel changes improve 60 sections; the other 92 keep their previous
  order. All 608 additional starting-level/XP checks pass. GuideFlowAudit.json
  records complete old/new steps, changed-leg evidence and separate travel
  traces. Prior trip/reward traces are not counted as new improvements.
- Keep bounded attachment/leg caches between loading frames instead of
  recalculating them at every yield. Explicit cache resets remain available.
  The 246-action Durotar host fixture uses 1,783 loading resumes, compared with
  2,391 previously; host timings do not guarantee native frame performance.
  Started guides remain fixed during play, scans and same-version reloads.
- Quest/NPC/transport facts are unchanged. The source audit still has 33
  gap-free sections and 119 needing facts. Terrain, drop delays, combat XP and
  complete-trip timings remain beta-client checks; no XP/hour is invented.
- Validation: all 1,371 host tests passed, including 61 targeted flow/cache/
  recovery checks. All 81 Lua files compile under Lua 5.1; the source audit
  checks 11,822 points and 16,849 action reasons across all 152 sections.

## 0.8.53

**EARLIER REWARDS**

- Collect ready hand-ins during existing mapped visits, individually or together.
  Search all hand-ins, including rewards beyond the old trip lookahead. Move
  only hand-ins whose work already precedes the visit; retain pickup/objective
  order, prerequisites, escorts, endpoints and unavailable/review boundaries.
- Compare known quest XP collected before every objective. Earlier rewards can
  improve the level curve even when final XP, peak log and minimum-level
  shortfalls stay equal. Do not delay XP before another objective, add walking
  for earlier rewards alone, or worsen the existing full-route state guards.
  Also replay the bottom, middle and top bracket levels and a partly filled
  middle-level XP bar: reject losses from leveling before a later grey quest.
  Unknown combat/drop XP and timing are not invented.
- Explain useful earlier hand-ins in the small guide: collect XP while you are
  there, before the next work. Keep the reason after reload. Started guides
  retain their order during quest updates and scans; installing this version
  rebuilds a saved guide under the new rules while applying personal progress.
- The identical-source comparison retains all 12,985 actions across 152 guide
  sections and supports 47 earlier-reward visits in 32 sections. The other 120
  retain their previous order. Quest/NPC/transport source facts are unchanged.
  GuideFlowAudit.json records full old/new steps and rewards before work;
  ROUTE_OPTIMIZATION.md explains the estimates and remaining source gaps.
  All 608 additional bracket/starting-XP replays preserve the reward and
  progression guards.
- Validation: all 1,360 host tests passed, including 50 targeted flow/recovery
  checks; all 81 Lua files compile under Lua 5.1. The source audit checks 11,822
  points and 16,849 action reasons. Its 33 gap-free sections and 119 sections
  still needing source facts are unchanged; native terrain, reward scaling and
  complete-trip timing remain beta-client checks.

## 0.8.52

**BETTER QUEST TRIPS**

- Compare two or three overlapping later quests as one complete trip after the
  existing objective and hub passes. A move considered alone can leave another
  return necessary; moving their pickup/unlock/work dependencies together can
  remove that visit. Retain every action, per-quest order and onward endpoint.
- Require a full-route benefit without increased held-quest peak, known XP
  shortfall, difficulty, repeated kills or uncertain/blocked travel. Preserve
  escorts, item-use stages, actual NPC offers, skips, deferrals and fixed order
  during play. Loading remains cooperative; existing arrow reasons explain
  collecting the overlapping work before leaving.
- The identical-source comparison retains all 12,985 actions across 152 guide
  sections. Nine additional trip changes improve seven sections; the other
  145 retain their previous order. Quest/NPC/transport source facts are unchanged.
  Estimated improvements require whole-loop beta timing; no XP/hour is invented.
- Validation: all 1,349 host tests passed, including 39 targeted flow/recovery
  checks; all 81 Lua files compile under Lua 5.1. The source audit checks 11,822
  points and 16,849 action reasons. Its 33 gap-free sections and 119 sections
  still needing source facts are unchanged; all route invariants pass.

## 0.8.51

**CLEAN LEVELING**

- Make leveling cards shorter and clickable. Keep the title and quest count;
  remove the right-hand level badge, repeated route/list buttons, XP paragraphs
  and future-level helper text. Use the left bracket selector; All levels keeps
  section names in the title so repeated zones remain clear.
- Open the ordered quest preview before starting. Start route lives in its
  footer and waits for loading to finish. Closing or switching previews cancels
  stale work; browsing leaves the running guide in place. Keep the existing
  early-level warning and choice to include current quests.
- Move quest supplies and party catch-up into a contextual More menu in the
  preview. Path to Orgrimmar uses the same click-to-preview/start flow. Keep
  window resizing and scrolling, and restore other views when reusing cards.
- Validation: 286 relevant host checks passed for preview/start/cancellation,
  resizing, future guides, class filters, travel, supplies, party catch-up and
  other browser views. All 81 Lua files compile under Lua 5.1. Native beta
  rendering remains a live-client check.

## 0.8.50

**SMARTER HAND-INS**

- Evaluate same-hub pickup/hand-in alternatives after the existing objective-loop
  optimizer. A ready hand-in can precede new pickups when the complete guide has
  less quest-log pressure or less known XP/difficulty shortfall at equal travel.
  Retain all valid actions, prerequisites and endpoints; never add walking just
  to lower the number of held quests. The added hub pass leaves objective work
  in order, protects nearby unlock visits ahead of unrelated pickups, and does
  not reshape a started guide during play.
- Explain useful reward-first and quest-log visits in the small guide window,
  and retain those explanations after reload. Preserve actual NPC-offer gates,
  manual skips, deferrals, abandon recovery, escorts and quest-item stages.
- Exclude explicit `<NYI>`/`<TXT>` editorial placeholders from leveling guidance,
  including the unmapped Get those Hyenas!!! entry. Keep their catalogue facts
  searchable. Real Thousand Needles introductory quests remain suitable at level
  25; optional/elite/class quests still use their existing rules.
- Allow complete-route replay to include explicit starting XP and unrelated
  reserved quest-log slots when those facts are supplied. Unknown capacity,
  combat/drop XP, inventory preparation and transport timing remain unknown.
  Avoid equivalent hub-state replays so cooperative loading stays bounded.
- Compare the new optimizer with the 0.8.49 optimizer using identical corrected
  quest scope and source data. Record full old/new sequences and log/progression
  benefits in GuideFlowAudit.json. Removing bogus entries is a scope correction,
  not evidence of a faster route. See ROUTE_OPTIMIZATION.md for assumptions.
- Validation: all 1,334 host tests passed, including 35 targeted flow/recovery
  checks; all 81 Lua files compile under Lua 5.1. The full-route comparison
  retains 12,985 valid actions across 152 sections and supports 19 additional
  hub changes in 13 sections. The source audit has 33 gap-free sections; 119
  still need facts. Beta timing, terrain and API behavior still need live tests.

## 0.8.49

**QUEST FLOW**

- Improve whole quest trips inside the existing fixed-guide compiler. Consider
  prerequisite work/hand-ins, follow-up pickups and overlapping objectives
  together, rather than only relocating adjacent steps. Retain every action,
  each quest's order, immediate escorts and the same start/finish. Ignore tiny
  estimated savings; a started guide retains its order during questing/scans.
- Replay the complete candidate's quest state, log peak, known acceptance levels,
  quest-reward XP and difficulty pressure. Reject increased progression/log
  shortfalls, reduced reward estimates or increased required kill work. Shared
  NPC kills give credit only to matching quests already accepted; later pickups
  receive no retroactive credit. Drop rates/combat XP/timings remain unmeasured.
- Compare published directed ground/ordinary transport links with faction and
  hostile-settlement checks. Keep local attachments/uncovered roads estimated;
  do not assume personal flights, mounts or hearths in generic zone plans.
  Keep live confirmed flight routing unchanged. Isolate cooperative graph caches
  from flight-distance queries and yield during graph/state work.
- Explain useful unlock/overlapping trips in the small guide window when their
  related quests remain relevant. Keep source commentary and counters in
  diagnostics. Missing-offer deferrals, manual skips, level/identity filtering,
  objective item-use and progress recovery remain in place.
- Save complete old/new sequences and assumptions in GuideFlowAudit.json, with
  a reproducible same-source comparison tool and ROUTE_OPTIMIZATION.md. Every
  compiled action is accounted for; mapping/source coverage remains distinct.
  Strict source audit still identifies 32 gap-free sections and 120 sections
  needing facts; this release does not claim 100% world mapping or optimal XP/hour.
- Validation: all 1,321 host regressions passed, including 17 new whole-flow
  checks; all 81 Lua files compile under Lua 5.1. All 152 sections retain 13,087
  actions/endpoints; 68 loop improvements are accepted in 38 sections, with
  state/travel non-regression checks. The cooperative Mulgore host build's
  largest resume was 8.54 ms; native timing, terrain and APIs need the checklist.

## 0.8.48

**YOUR NEXT ADVENTURE**

- Open on Recommended: a featured leveling-zone guide and smaller cards for
  the crafting professions the character knows. Show short reasons, current
  skill, saved skill goal, next crafting action and compatible quest progress.
  Keep the existing Leveling, Professions, Dungeons, Quest log and All quests
  browsers in the menu, with saved searches/brackets independent of the home.
- Continue an active guide without replacing its order or crafting batch.
  Preview a quest list or profession plan before starting. Recommendations use
  existing level/identity/progression rules and crafting planners; opening the
  screen never starts a guide. No suitable guide, unknown character details,
  level cap and no known crafting profession have concise empty states.
- Cache read-only cards across geometry updates; quest/profession changes refresh
  them. Read public profession skill when opening, load detailed profession
  facts only for known professions, and keep resizing free of planner work.
  Hide stale party summary entries in solo mode and separate footer controls.
- Add recommendation providers for future activities without adding placeholder
  daily/mount guides. Use the approved subtle zone themes and native profession
  icons. Code-rendered previews use example data; native beta rendering needs
  the live checklist.
- Validation: all 1,304 host regressions passed, including 17 new recommendation
  checks; 140 targeted home/menu/browser/crafting checks passed. All 79 Lua
  files compile under Lua 5.1. In-client rendering and event delivery remain
  part of the friend checklist.

## 0.8.47

**CRAFT BY CRAFT**

- Group auction-house materials into expandable recipe boxes, in planned
  crafting order. Show approximate crafts, skill range, intermediate
  preparations and estimated buy cost, so shopping can be funded in parts.
  Each recipe's Search uses its own missing amount; bag stock and earlier
  outputs are shared once across the full plan.
- Fill the public commodity buy quantity once after the player's matching
  selection, where the native control is supported. Respect manual changes,
  fresh bag additions, stock limits, combat, guide changes and closing the AH.
  Item auctions retain manual quantities. No purchase is started or confirmed.
- Load missing item metadata before exact-ID queries; skip unresolved details
  after five seconds. Catch rejected item-data requests and auction queries.
  Install the response watchdog before sending, show a countdown and move past
  unanswered requests after 20 seconds. Old timers cannot advance newer queries.
- Report priced/skipped counts and failed item IDs/reasons in diagnostics,
  without replacing older cached prices with zero. A panel refresh failure
  cannot disable the scan watchdog. Retain bounded pagination, pacing, manual
  browsing cancellation and current-guide price reassessment.
- The reported silent 10/40 stall is not confirmed on a live beta client.
  Host regressions cover an unresolved tenth item in a 40-item queue; live
  scanning and native quantity controls need the checklist below.
- Validation: 1,286 full-suite host checks, 117 auction/UI regressions and
  197 profession checks passed; all 77 Lua files compile under Lua 5.1.
  Forecast recipe boxes match aggregate buy totals for all six crafting
  professions. Partial source paths remain labelled incomplete.

## 0.8.46

**GUIDE REASONS**

- Share destination reasons across the guide window, standalone arrow and quest
  list: useful follow-ups, nearby eligible pickups, accepted work, grouped
  rewards, dungeon preparation and training. Lower-level exceptions name the
  worthwhile later quest or dungeon benefit.
- Explain long generic pickups honestly: their level and selected-guide role,
  with no special unlock claimed. Offer Skip quest when the detour is not worth
  it. Unverified requirements name the giver; missing coordinates stay explicit.
- Keep alternative branches optional. Exclude completed, accepted, skipped,
  disabled-class and incompatible follow-ups from prerequisite benefit claims.
  Preserve build-scoped learned rules without observer names in routine UI.
- Show reasons without hovering in the standalone-only layout. Wrap main guide
  explanations with room to read them; retain saved geometry, advice dismissal,
  training controls and useful kill/loot/item-use instructions.
- Use the previewed guide's facts in its quest list. Cache decisions until
  progress, identity, route, learning settings or destination facts change;
  query completion only for actual follow-up relations.
- Audit all 5,230 records, 16,849 source/missing-stage destinations and 13,087
  compiled steps across 152 faction/level-section guides, including 1,114
  cross-map transitions. Retain order, prerequisite, escort and distance checks.
  This is explanation coverage; source-data gaps remain separately reported.
- Fixed guide order, eligibility, automatic quest actions and progress are
  retained. Live Forever fonts, rendering, NPC offers and travel need retesting.
- Validation: 1,266 full-suite host checks and 104 targeted regressions passed;
  all 76 Lua files compile under Lua 5.1. The catalogue/guide audit passed its
  existing invariants and new explanation-coverage checks.

## 0.8.45

**SMART FLIGHT DISCOVERY**

- Compare a nearby unlearned master's connections towards unlocked destinations
  against the known journey, including walking, connecting flights and landing
  travel. Require a meaningful estimated saving and a bounded fallback detour.
- Add 266 directed, faction-scoped reference connections from the existing
  attributed Forever travel source. Supplement missing flight-master ownership;
  identify Ratchet's shared master as neutral. Native observations take priority.
- Make a qualifying check the arrow's next travel stop, with its reason and
  potential saving. Keep walking resumes the known route without a quest skip.
  The standalone arrow also exposes the reason and a dismiss button.
- Price connecting reference flights with one boarding allowance. Cache checks
  by goal, movement, speed and personal travel changes; examine at most three
  nearby candidates. Fixed guide order, progress and map quest markers remain.
- Opening the flight map replaces the check with actual reachable flights.
  Explicit unreachable results override reference links for this build. Draw
  only the walk to the check; unconfirmed connections never become flight actions.
- Host checks cover the Ratchet screenshot geometry, useful/slow/disconnected
  flights, faction and unlock gates, dismissal, menu confirmation and caching.
  Walking geometry, reference timings and live beta availability remain estimates.
- Validation: 1,245 full-suite host regressions passed, followed by 131 travel
  regressions after the movement-cost refinement. All 75 Lua files compile
  under Lua 5.1; live Forever flight access and map rendering need retesting.

## 0.8.44

**QUEST MARKER HOTFIX**

- Match possible mob/item-source associations to unfinished readable objectives.
  Suppress outdated source entries that do not match the active objective list.
- Respect a public native false for local-only quest mobs. Missing, restricted
  or failed native reads require a matched pending objective; native true cannot
  introduce unknown mobs, future objectives or unaccepted quest-start drops.
- Keep stars for synced unfinished party objectives independently of the local
  flag, and retain friendly guide pickup/turn-in/confirmation markers. Completing
  one objective removes its mob stars even while the quest has other work left.
- Add a diagnostic count of local candidates rejected by the native flag.
  Preserve out-of-combat reads, marker toggles, fixed guide order and saved skips.
- Reproduce a Winter Wolf/Stocking Jetsteam source association with a synthetic
  native false; test changed objectives, item counts, restricted/absent APIs,
  combat, stale hints and party demand. The tester's exact star remains
  unconfirmed without a marker-toggle/tooltip check on their beta client.
- Validation: 243 relevant host regressions passed; all 75 Lua files compile
  under Lua 5.1. Live beta quest-mob flags and rendering still need retesting.

## 0.8.43

**FLIGHT PATH DISCOVERY**

- Suggest nearby friendly unlearned flight masters within 350 metres, or up to
  750 metres ahead when visiting adds at most 200 metres of estimated walking.
  Exclude known hostile settlement crossings; retain fixed quest order.
- Check all 71 bundled native-ID taxi locations instead of only 36 settlement
  labels. Include client-observed masters and project public continent positions
  into the current zone. Ownership must be known; location never unlocks a flight.
- Show dismissible discovery advice beneath the standalone arrow as well as the
  guide panel. Name the stop and explain why learning it helps future trips.
  Confirmed undiscovered paths say Get; uncertain unlocks say Check. Confirmed
  known/current masters hide the tip. Flight advice also works in travel guides.
- Add diagnostic catalogue/range/nearest-master details for missed reminders.
  Cache by current leg and character travel changes; no extra polling loop.
- Host checks include the Sun Rock screenshot position with a known Barrens
  flight, bounded detours, faction/secret values, native-only locations, both
  arrow layouts and unchanged quest steps/connections. Beta retesting required.
- Validation: 1,220 host regressions passed; all 75 Lua files compile under Lua 5.1.

## 0.8.42

**GUIDE POLISH**

- Stabilize resizing around a scaled top-left anchor; finish on global mouse
  release/hide. Reflow smaller choice prompts, quest lists, materials, profession
  and diagnostics windows; save their geometry. Keep dropdowns above dialogs.
- Resize guide/dungeon panels through the same helper. Keep compact/full dungeon
  bounds distinct and do geometry work during drags, content work on release.
- Put the reason for long/cross-zone/flight/transport trips first in the arrow:
  skill-cap training, useful prerequisites, grouped visits or the chosen fixed
  guide. Keep quest/NPC actions and transport details in its tooltip. Larger
  guide windows give explanations more room; no exclusive unlock is invented.
- Permit larger same-hub pickup/turn-in bundles in newly compiled fixed guides,
  preserving stages, prerequisites and escorts. Running fixed order is retained.
- Review 231 new source captures; add 11 missing mapped points plus item/NPC
  facts without replacing reviewed locations or identity/prerequisite gates.
  Audit all 5,230 records, 152 faction/level-section guides and 11,822 points.
- Handle empty AH listings in materials text. Include all 75 Lua files and the
  0.8.41 taint mitigations. Fully restart; beta UI/taint retesting remains required.
- Validation: 1,210 host regressions passed; all 75 Lua files compile under Lua 5.1.

## 0.8.41

**TAINT HOTFIX**

- Select the current accepted guide quest through the native quest API without
  calling Blizzard's Lua quest-details UI helper on guide changes.
- Leave Blizzard auction-window anchors untouched. The materials panel stays
  beside it and can be dragged; closing it never repositions the native window.
- Preserve out-of-combat selection/tracking, fixed guides and auction scans.
  Host checks cover repeated changes, combat deferral and untouched native UI.
- Fully restart the client after installing. These remove two avoidable taint
  paths; the reported aura/Edit Mode error still needs a fresh-client beta retest.

## 0.8.40

**MARKET SMART**

- Replace the AH toolbar with a panel on its left: scrollable material rows,
  approximate Buy amounts after bags/planned outputs, Search buttons and skill goal.
  Make room when screen space allows; restore the AH's position on close.
- Add Scan auction house for the chosen profession/goal. Price viable recipe
  alternatives too, using exact item queries one at a time, at least 1 second
  apart. Respect throttling; bound pages, waits and retries. Stop on close,
  manual searches, browsing, guide/goal changes or Stop scan; pause in combat.
- Save up to 256 price snapshots for this character's realm/faction/build,
  expiring after 6 hours. Guard public buyouts/quantities; ignore owned, bid-only
  and private offers. Empty full results clear old prices. Partial books stay estimates.
- Reassess current crafts and the full goal path from observed prices, skill and
  stock. Prefer priced paths; compare buying intermediates with raw material
  cost/preparation time. Use cached native cast times, otherwise a time estimate.
- Keep purchases, training and crafting manual. Add scan/cache capability probes
  and host checks. Include all 74 Lua files and Media; retest native auction
  query behavior, placement and market results on the current beta.

## 0.8.39

**CRAFTING HOTFIX**

- Starting a crafting guide offers Scan current progress. Its manual button
  opens the profession window and refreshes skill, learned recipes and materials.
  Scan guide offers the same refresh; missing beta support asks you to open it.
- Preserve confirmed learned recipes through empty/partial loading reads.
  Refresh after training; stale unknown recipes ask for a fresh window read
  instead of repeatedly sending you back to the trainer.
- Use current client reagents for preparation recipes as well as final crafts.
  Show the craft estimate and skill milestone during gathering and training;
  size the profession next-step area to its text. Add diagnostic material counts.
- Only mark mobs linked to accepted unfinished quest objectives. Remove generic
  quest-flag guesses and markers for future drop-start quests; keep giver stars.
- Keep eligible elite/raid quests visible solo with a party/raid explanation and
  Skip quest choice. Preserve level, identity, prerequisites and explicit skips.
- Include all 72 Lua files and Media. Host regressions cover recipe refresh,
  Cured Light Hide at skill 31, live intermediate reagents, markers and elite
  guides. Retest the profession-window opener and UI on the current beta.

## 0.8.38

**SMART SUPPLIES**

- Add Next batch / To skill goal material estimates. Subtract bags once and reuse
  planned intermediates. Yield calculations and label partial data.
- Add Search AH buttons and a material toolbar. One search per click; require an
  open AH, cached names, no combat and query capacity. No buying or background scan.
- Public commodity/item/legacy buyouts provide session prices. New prices can
  change unfinished work immediately, using actual skill/bags. Unknown prices stay unknown.
- Estimate crafts to the milestone from the recipe's skill-up chance and points
  per gain. Remove fixed 1/3/5 limits. Failed gains leave the gap unchanged; actual
  milestones end steps. Reassess on skill/stock/color changes and resume on reload.
- Fix premature Expert-trainer detours below the current cap. Explain useful
  training visits. Remember positive opened-trainer offers by character/build.
- Exclude explicit level-0/zero-XP entries from every leveling guide, fixing
  Applejack Still's Elwynn detour. Preserve library facts and fixed-order progress.
- Include all 72 Lua files and Media. Host checks cover materials, repricing,
  trainers, craft estimates and Elwynn. Native AH/trainer UI still needs beta tests.

## 0.8.37

**SKILL BY SKILL**

- Use actual profession skill and explicit next milestones in all six crafting
  guides. Limit batches near recipe unlocks, difficulty changes and rank caps.
- Count down remaining crafts after matching public craft-success casts. Keep
  unfinished batches through bag refreshes, previews and reload; prepare only
  the intermediates needed for remaining crafts. Extra batches start from actual
  skill when some crafts give no skill-up.
- Prefer fresh skill-line readings over stale crafting-window skill snapshots.
  Reassess recipes at milestones, batch completion and loss of skill-up eligibility.
- Make profession logos fully visible; preserve card backgrounds and layout.
- Simplify main navigation to Leveling, Professions, Dungeons, Quest log and
  All quests. Remove Personal professions settings; the guide chooses batch
  quantities from the next milestone and estimated skill-up reliability.
- Include all 69 Lua files and Media. Host checks cover Leatherworking at skill
  11, intermediate consumption, all six professions, failed skill-ups, persistence
  and existing guide/UI behavior. Verify craft-event delivery on the beta client.

## 0.8.36

**CRAFTING COMPANION**

- Add compact cards for six primary crafting professions; learned professions
  appear first. Preview a skill path and choose a 75/150/225/300 skill goal.
- Suggest the next craft from profession skill, known recipes, skill-up colors
  and bag stock. Character level gates rank training. Show a named friendly
  trainer, next-batch materials and preparation crafts for intermediates.
- Use our own balanced material/time scoring and yielding future-path preview,
  informed by 2,009 attributed recipe facts and 150 trainer locations. Live
  public recipes/materials override reference facts. Unknown prices remain
  unknown; manual AH results and ordinary merchant listings inform costs.
- Start personal crafting guidance in the existing small guide window, with
  Next recipe, Materials and Refresh. Preserve Stop/Exit and reload checkpoints.
  Keep quest skips, party routes and automatic crafting/purchases separate.
- Keep details packed until used; batch profession/bag events and cancel stale
  previews. Preserve existing combat and leveling event handlers.
- Include all 69 Lua files and Media. Skill-up chances/future craft counts are
  estimates; a 300 preview does not confirm beta training availability.
  Host checks cover planning, state, privacy, UI and progression; native APIs
  and six profession windows still need beta testing.

## 0.8.35

**DUNGEON BROWSER**

- Arrange dungeon cards in two columns at normal widths and three when wider.
  Keep full-card faint artwork, dungeon names, level ranges and concise quest
  summaries. Reflow during resizing without querying quests or replanning guides.
  Keep zone leveling guides as wide cards.
- Make the whole dungeon card open its journal; remove separate See dungeon,
  quest-list and route buttons from the browser cards. Put Quest list and Start
  quest route side by side in the journal. Browsing preserves the active guide.
- Reuse dungeon collection, run and hand-in guidance when starting a quest route.
  Disable starting when no matching unfinished, unskipped quests remain. Keep
  journal actions hidden in Map only; preserve saved geometry and combat display.
- Include all 66 Lua files and Media. Host checks cover layout, pooled cards,
  resizing, journal selection and route entry; retest beta fonts and artwork.

## 0.8.34

**ZONE GUIDE CHAPTERS**

- Split newly selected zone guides into actual 1–10, 11–20, 21–30 and later
  quest sets. All levels lists separate sections. Omit empty and isolated
  single-quest sections; keep useful earlier prerequisites and close-level,
  linked cross-zone continuations. Later unrelated quests stay in later guides.
- Match quest lists, counts, quest-level bands and XP estimates to the section.
  Known later Forever content can have its own section in a starter zone.
  Preview future sections freely; starting early still warns and waits for real
  level, identity, prerequisite and NPC-offer requirements.
- Preserve a section through Scan, quest updates, location changes, reload and
  route sharing. Keep existing saved full-zone scopes. Offer the next useful
  local section after current work ends; switching remains optional.
- Keep fixed order, class-quest filtering, nearby pickup bundling and useful
  low-level prerequisite explanations. Include all 66 Lua files and Media.
  Host checks cover logic; retest availability and guide transitions in beta.

## 0.8.33

**HANDINS AND TRAVEL CACHE**

- Keep a dungeon guide after entry. Wait for its objectives, then route ready
  quests to their hand-in NPCs. Unfinished quests and missing turn-in locations
  stay pending. Preserve phase and goal set through Scan/reload. Individual
  quest-pickup routes still finish on acceptance.
- Preserve confirmed flights when weaker map discovery flags conflict. Keep
  saved world positions when login projection is unavailable. Use saved geometry
  or published distance estimates to price confirmed flights when live geometry
  fails; validated flight timings retain priority. Unlocks alone add no flights.
- Describe the next transport before later flights. At ship/zeppelin/tram boarding
  points, retain the crossing through movement, zone discovery and unavailable
  GPS until arrival. Suppress an arrow back to the dock; Scan recalculates it.
- Add flight-cache restoration/conflict counts to diagnostics. Opening the
  reported Thunder Bluff menu added five connections and selected Orgrimmar;
  the exact original loss remains unconfirmed from the two probes alone.
- Include all 66 Lua files and Media. Host checks cover state and saved data;
  actual beta flights, transport arrival and dungeon returns need testing.

## 0.8.32

**ELITE TARGET SPAWNS**

- Show skulls at known possible spawns for the current unfinished elite kill /
  drop objective only. Keep future hunts hidden even in full-route preview.
  Clear on completion, skip, guide switch and stop; synced party objectives stay
  marked until the last relevant member finishes.
- Add Show elite target spawns on the map in Quest markers settings, on by
  default. Keep route order, ordinary nameplate markers and quest destinations.
  Spawn facts load per target; retain all selected reference points, with older
  positions limited to unchanged quest identities. Possible locations are not
  live mobs or guaranteed current-beta positions.
- Add Open guide beside Diagnostics to reopen the small guide window. After
  Exit, it opens empty without reviving a stopped guide. Hidden active guides
  keep their progress; close the browser to reveal the guide. Handle corpse map
  previews without available coordinates.
- Include all 66 Lua files and Media; replace the complete folder, then reload.
  Host checks verify logic; markers and source positions still need beta testing.

## 0.8.31

**VANILLA LOOT AUDIT**

- Use original Vanilla encounter IDs for classic dungeons. Fix BFD's SoD raid
  identities and their map-marker clicks; include omitted Vanilla encounters.
- Audit all 933 listed Vanilla NPC loot tables and 95 treasure-container tables.
  Keep 5,557 item facts shared and lazy. Preserve captured Forever additions;
  exclude 13,127 season-only source rows. Source coverage is not a guarantee of
  current beta drops or measured drop rates.
- Separate encounter loot from shared/world drops. Add each sourced trash mob
  and treasure container beneath bosses, with its own loot and existing search /
  class filters. Keep trash and treasure loot sources off the dungeon map.
- Include reported boss drops for Hall of Thanes, Ruins of Lordaeron and
  Excavation Site: Wetlands. Keep unpublished beta loot unknown.
- BG changes opacity. ST stops the guide and leaves an empty window. Exit (×)
  stops and closes it. Cancel scans, planning, saved restore and pending combat
  starts immediately; only protected map cleanup waits for combat to end.
- Include all 64 Lua files and Media; replace the complete folder, then reload.
  Host checks verify data and logic; UI and live loot still need beta testing.

## 0.8.30

**DUNGEON PREPARATION**

- Start route runs a personal Get dungeon quests guide in the existing small
  guide window. Collect suitable quests across zones, complete required chains,
  then head to the entrance. Quests already in your log count as collected.
- Remove the one-zone restriction and 19-pickup cap. Compare known travel links
  and flights, improve visit order while preserving prerequisites, and schedule
  planning behind Loading route. Reuse the itinerary during ordinary progress.
- Select a quest card or Route to pickup for that quest's own preparation guide.
  It stops after acceptance, without sending you to unrelated quests or the entrance.
- Replace the text list with compact quest cards, giver/zone/level/status, counts
  and All / To collect / In your log / Completed filters. Remove Record entrance here.
- Keep verified identity, actual offers, skips, guide restore and opt-in
  selected-guide acceptance. Missing facts wait rather than bypass requirements.
  Switching guides cancels old planning and reuses the same window.
- Include all 64 Lua files and Media; replace the complete folder, then reload.
  Host checks verify logic; travel and UI need beta testing.

## 0.8.29

**MEMORY COMPARTMENTS**

- Load detailed quest fields, NPC/item/object records and dungeon maps/loot on
  demand. Preserve all 5,230 quests and source facts; decoded tables keep runtime
  corrections, and their packed copies are released.
- Reduce retained host Lua memory from 51.7 to 25.2 MiB at startup and 55.2 to
  29.7 MiB after representative use. Beta memory needs testing. `/wt probe`
  reports compartment counts and client memory when available; no forced GC.
- Make the guide-step window resizable/closable with saved geometry and reflowing
  attached panels. Closing keeps the guide running; reopen with the arrow setting.
- Refresh/filter dungeon quest lists by verified faction/class/race, including
  Blackfathom Deeps. Start route starts directly; unmapped collections remain
  selected instead of opening the entrance-recording list.
- Boss selection follows its mapped floor; the journal opens above the main
  window. A class loot dropdown defaults to your class, with All classes available.
  Known weapon/armor types filter by usability; unclassified drops stay visible.
- Preserve guide order/progress, skips, eligibility and sync. Include all 62 Lua
  files; update the complete folder, then reload.

## 0.8.28

**ROYS BIG DUNGEON BANANZA - HOTFIX**

- Fix the reported dungeon timeout: background sync, packet sends/receives,
  roster changes, zone entry and objective events no longer rebuild a closed
  guide browser. Guide, tracker and arrow progress still update.
- Batch visible background dashboard refreshes for 0.1 seconds using fresh
  quest history. Keep explicit UI actions and manual refreshes immediate.
- Reuse existing event subscriptions when chaining dungeon handlers. Avoid
  repeated registrations incorrectly disabling viewer updates; keep genuine
  unsupported-event and handler errors visible.
- Preserve guide rules, fixed order, skips, dungeon markers, loot and layouts.
  Include all 61 Lua files; actual beta responsiveness still needs testing.

## 0.8.27

**ROYS BIG DUNGEON BANANZA**

- Add clickable boss portraits on dungeon floors; Map only expands to the
  selected boss and its loot. Keep saved resizing/positions and combat visibility.
- Add quest pickups, objectives and turn-ins at known interior NPC/object
  positions, with concise action cards and a saved Quests toggle. Hide completed
  or incompatible quests; keep city quest givers outside the interior map.
- Map 158 bosses / 139 quests across 19 Classic complexes from attributed floor,
  spawn and Forever quest facts. Native coordinates win; reference points require
  matching artwork. Ambiguous positions and new-dungeon gaps remain unplaced.
- Remove invalid level-9999 boss placeholders, including BFD. Include all 61 Lua
  files; actual Forever textures, coordinates and behavior still need beta testing.

## 0.8.26

- Clean up dungeon windows: remove technical footers and map-position explanations,
  shorten unavailable messages, and keep boss/loot/level information concise.
- Remove source-coverage notes from guide cards and map tooltips, shorten preview
  and loading text, and remove the arrow tooltip's chat command. Keep technical
  information in diagnostics/docs and preserve useful quest instructions.
- Shorten settings explanations, profession cards and quest-review text; keep
  useful restrictions, choices and prerequisite guidance clear.
- Preserve guide order, progress, map markers, dungeon controls and saved layouts.

## 0.8.25

- Hide the dungeon map-level dropdown when only one map, or no verified map, is
  available. Close any open floor menu when switching to those dungeons; retain
  the selector for multiple maps in both Full view and Map only.

## 0.8.24

- Add See dungeon first on Dungeon quests cards; keep Quest list beside Start
  route. The full journal opens from anywhere without changing a quest route.
- Add floor images, paged boss/portrait selection, notable loot with item icons,
  literal search, equipment/other filters, cached native tooltips and modified
  item clicks. Capture attributed Forever facts: 243 encounters / 2,766 notable
  drop entries in 19 Classic complexes. Native floor/portrait data takes
  precedence; unknown boss positions and new-dungeon loot are not invented.
- Add Map only / Full view, smooth resizing, saved separate sizes/positions and
  a BG toggle. Share layouts across all dungeons/reloads; keep owned map windows
  open during combat. Entering a recognized dungeon optionally asks Open map?
  and opens the compact map. Add a setting to disable that prompt.
- Reference Blizzard client artwork only; no external art or source scripts in
  the addon. Include all 59 Lua files and source provenance. Beta API behavior,
  texture availability and instance matching still need real-client testing.

## 0.8.23

- Romits: improve untimed flight estimates using native connecting stops when
  public route data is available. Keep first rides labelled estimates; curves
  between stops remain unknown. Preserve the working walking-time calculation.
- Capture delayed departure/landing state with short bounded retries, including
  when both arrows are hidden; retain slot identity briefly if the native map
  closes before the selection hook. Confirm arrival near the selected flight master
  before saving a duration; exclude interrupted, stale and unconfirmed rides.
  Position retries retain the original landing time, excluding later walking.
- Share validated build/route-specific timings between both timers and planners.
  Keep older unverified samples but re-time them before use. Add recording,
  route-capability and expected/actual diagnostics. Include all 56 Lua files;
  native beta behavior still needs testing. Romits' exact failing trip is unknown.

## 0.8.22

- Give Dungeon quests cards official Blizzard client artwork, stretched across
  the entire block at a uniform, faint 14% opacity. Keep labels and controls clear;
  resize/reuse the same texture and clear it when the card becomes an ordinary row.
- Read available dungeon-journal images without opening it or changing its tier.
  Published filenames cover 19 Classic complexes and four Forever dungeons. The
  other five use native journal art when available, then a neutral client background;
  missing assets leave a plain card. No external images are bundled or downloaded.
- Add artwork capabilities/resolution counts to diagnostics and document sources
  in DUNGEON_ARTWORK.md. Preserve guides, progress and skips. Include all 55 Lua
  files; actual asset availability and rendering need beta testing.

## 0.8.21

- Add optional personal class-training steps near quest visits or before leaving
  a hub. Even levels trigger a check; require a friendly trainer for your class
  within 150 metres and an estimated extra walk of at most 150 yards. Nearby
  objectives, NPC checks, flights and corpse travel take priority.
- Done training / Skip training resumes quests and saves the choice per character
  until the next even level. Retain pending visits after reload; preserve quest
  order, progress and skips. Separate Leveling guides toggle defaults on.
- Import 151 trainer locations for all nine classes from the attributed pinned
  Forever geography source. Mark active visits with T on the map; provide Done /
  Skip controls when only the standalone arrow is visible. No automatic purchases
  or inferred spell availability. Include all 54 Lua files; beta testing required.

## 0.8.20

- Check entire walking segments for crossings through known enemy settlements,
  including Astranaar. Use another existing graph connection when available;
  otherwise hide the crossing line and explain that no mapped bypass is known.
  Keep quest markers, fixed guide order, progress and manual skips.
- Repair 26 missing flight-point faction labels from the pinned geography source.
  Apply ownership checks to published points, cached flights and fallback flight
  approaches/exits. Friendly and neutral places remain usable; flight rides can
  pass over enemy towns. Intentional quest destinations are not auto-skipped.
- Add 48 approximate settlement footprints from published occupied locations,
  with an estimated 100-yard margin. These are not guard boundaries or verified
  roads; terrain and beta rendering still need player testing.
- Preserve the supplied partial export without counting its repeated older
  events twice. Include 53 Lua files and faction/crossing/map regressions.

## 0.8.19

- Select and track the accepted current guide quest in Blizzard's log for map
  highlights. Default on under Arrow and map; waits until combat ends, follows
  the latest step, and does not open the map or add a user waypoint.
- Add a compact Use item button for the current accepted objective's special
  quest-log item. Manual click outside combat; recheck the quest's log index on
  each click. No automatic use or targeting. Missing/restricted data hides it.
- Keep complete NPC absence evidence across other progress and reload, scoped
  to character/build. Fresh offers restore deferred quests in fixed order;
  partial dialogs confirm only their own quest. Accepted work and skips remain.
- Our Ancient Enemy and The High Chieftain require actual NPC offers while their
  exact Forever unlocks remain unresolved. No prerequisite/race gate is guessed.
- Add the published Report to Kadrak alternative-ID relationship. An accepted or
  completed version blocks the other pickup across guides. Keep the accepted
  turn-in; do not mark the unchosen quest complete or infer aliases from titles.
- Preserve all supplied raw exports, clearly marked truncated. Recover 94 shared
  Mulgore events once and 77 separate Kadrak-report events. Add source-validated
  corrections and Lua 5.1 regressions. Include all 52 Lua files; test native
  selection/map highlights and quest-item use on the beta client.

## 0.8.18

- Romits (0.8.16): retain quest markers and full-route previews during flight,
  keeping ground lines hidden until landing. Separate ride duration from full
  journey time; show the same estimated/timed countdown above the standalone
  arrow and in the guide panel. Overdue estimates show elapsed flight time.
- Store remote flight-map points in the destination zone and repair saved
  continent points without adding unlocks/connections. Dijkstra uses localized
  flight geometry and refreshes travel costs when walking/mount speed changes.
  Boat/zeppelin instructions name the boarding place with map coordinates.
- Add walking/mount ETA to the next waypoint. Hide the duplicate guide-panel
  arrow when the standalone arrow is shown; retain instructions and controls.
- Advance known item-collection stages from personal bag counts, refreshed on
  bag events, in fixed/adaptive guides. Fresh Zhevra Carcass now advances to the
  next Ishamuhale objective without granting quest completion. Never use bag
  possession to complete kill/use steps or infer another player's progress.
- Include class quests defaults on for new/unset settings; preserve explicit
  opt-outs and incompatible-class filters. Keep fixed guide order and skips.
- Add regressions for flight connections/geography, timing, map visibility,
  transport directions, arrow layout and collection progression. Joker's cache
  comment remains a hypothesis; native routes/timing need beta retesting.

## 0.8.17

- Combine the supplied Wowhead Forever overview, 23 bounded dungeon quest lists
  and the attributed Forever geography snapshot. Add all 19 Classic complexes
  with entrance areas, plus nine Forever dungeon entries; four new entrances
  are mapped and five remain explicitly unknown. Preserve 339 quest memberships.
- Show dungeon run ranges, locations, wing ranges and Quest list on dungeon
  cards/details. Keep collection pickup levels separate; identity, prerequisites,
  offers and class/repeatable filters still apply. Fold duplicate names together;
  class/city/raid tags no longer create fake dungeon cards. Keep all quest records.
- Prefer saved entrance recordings, then public client links, then published
  points. Keep the entrance as the last collection stop across zones and use
  travel instructions. Distant pickups remain optional and explained.
- Add editable DungeonData, source hashes and DUNGEONS.md. Points mark entrance
  areas; cave/portal positions still need beta testing. Document two conflicting
  new-dungeon level descriptions; use the overview chart/table consistently.
- Include 50 Lua files. Add source, membership, native fallback, UI and route
  regressions; retain fixed leveling-guide order, progress and travel costs.

## 0.8.16

- Replace anonymous internal junction labels across all guides with readable
  directions, e.g. Go to waypoint — The Barrens (54.0, 26.6). Keep named gates,
  docks and flight masters. The arrow and map tooltip share the directions;
  short context describes travel towards the destination, rather than calling
  every intermediate point a crossing. Coordinates are map percentages.
- Include the current travel leg, coordinates and final quest/destination in
  diagnostics for terrain reports. Keep graph points, costs and guide progress.
  The reported label is confirmed; an actual terrain defect needs live context.
- Retain the agreed -3/+3 work band with explained useful prerequisites and ready
  hand-ins. No new automatic/manual skips or stricter level policy are added.
- Add Lua 5.1 regressions covering all 30 shipped anonymous junctions, the
  reported point, map/arrow text and travel-only advancement. Beta rendering
  and terrain paths still need player testing.

## 0.8.15

- Scan fresh personal quest-log, objective and completion data. Retry briefly
  during loading and recheck changes during large scans. Keep fixed order and
  preserve skips on failed/cancelled reads; Reconsider skips applies on success.
- Refresh arrow/map even with the dashboard hidden/resizing. Batch overlapping
  quest events into a 0.1-second personal update; avoid rebuilding hidden UI.
  Party messages keep their separate two-second batch and existing protocol.
- Bridge confirmed accepts/turn-ins while native entries catch up. Keep the last
  complete public log during incomplete reads; add bounded retries/diagnostics.
- Keep useful prerequisite exceptions to the -3/+3 level band. Label them and
  explain the quest they unlock, with its level or dungeon purpose. Filter
  unrelated unfinished low-level work consistently; retain ready hand-ins.
- Optionally suggest a suitable adjacent zone after leveling when no useful
  current work is ready. Keep NPC/location checks; require Start zone guide or
  Keep my guide. Respect level, identity, pickup and completion requirements.
- Add Lua 5.1 scan, event-burst, delayed-log, fixed-order and zone regressions.
  Native beta smoothness, API timing and display still need player testing.

## 0.8.14

- Add a small BG button to the guide panel to switch its background between
  opaque and see-through. Keep arrow, text and controls fully visible, including
  attached objective/tip panels. Save the choice across reload and expose the
  same option under Settings → Arrow and map.
- Keep this appearance toggle independent of guide progress, route drawing,
  travel calculations and saved skips; it also works during combat.
- Preserve and review the supplied 23-event Durotar export, retaining event
  versions/build/sessions. Confirm existing starter-quest giver matches and add
  replay regressions against unsupported prerequisite learning from stale or
  inconsistent history. No new prerequisites or coordinates are inferred.

## 0.8.13

- Fix false “Guide complete” messages when every runnable fixed-guide step was
  hidden by the level/group filter. Require actual quest completion across
  applicable enabled guide quests, independently of route eligibility.
- Retain filtered unfinished steps in the remaining count and show a paused
  explanation when no suitable work is available. Keep manual skips distinct
  from quest completion, and avoid completing empty/incomplete plans or unknown
  history. Preserve fixed order, close-level filtering and ready hand-ins.
- Keep completion and route summaries in diagnostics after completion. Report
  unfinished, skipped and unknown-history quests, plus filtered unfinished steps.
- Refresh the navigation hover tooltip when its state changes, removing stale
  loading text. Add regressions using shipped Hillsbrad quests, the reported
  level-24 solo context, later-level progress, party, skips and reload behavior.

## 0.8.12

- Add faint zone-themed landscape backgrounds to guide cards across current
  zones. Give the Orgrimmar travel guide a settlement theme and dungeon
  collection cards subdued ruins; keep a quiet fallback for future zones.
- Fade scenery into charcoal behind the text area, retaining readable labels,
  buttons and borders. Crop proportionally during resizing and reuse one
  texture per card. Clear artwork when pooled cards become plain quest rows.
- Bundle sixteen original generated landscape motifs, their source atlas and
  provenance. All assets load locally; no in-game downloads or animation.
- Preserve guide order, pickup requirements, quest credit and party behavior.
  Add asset-integrity, release-packaging, card-reuse and resize regressions.
  Install the complete addon, including the new Media folder.

## 0.8.11

- Show upcoming zone guides in manually selected level brackets and All levels.
  Keep default recommendations suited to the actual lowest player level, and
  preserve faction/class/race, category and leveling-area filters.
- Preview any visible guide's complete quest order without replacing the
  running route. Label upcoming guides clearly and rank suitable guides first.
- Warn before starting too early, with the suggested entry level and an
  effective unfinished guide for the current context when one is known.
  Offer Start recommended, Start anyway and Cancel; retain pickup restrictions.
- Keep an explicitly started future guide waiting instead of marking its
  level-filtered work complete. Save its fixed order and early-start state
  across reload. Retain the existing Include current quests choice.
- Add browsing, search, warning, prerequisite, reload and shipped-catalogue
  regression checks. Keep manual installation; no installer is included.

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
