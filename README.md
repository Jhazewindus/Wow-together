# WoW Together

A **WoW Forever companion** for the **World of Warcraft: Forever beta**, with
leveling at its core and optional tools for travel, dungeon preparation and party
progress. Version
**0.8.54 — BETTER TRAVEL ORDER** targets interface **16001**, uses Lua **5.1**, and reads capabilities
rather than choosing a Classic implementation from `WOW_PROJECT_ID`.

Friends share their own active quests, completion checks, objectives and
public character context. The guide combines nearby work, preserves selected
routes and shows whose progress needs the next step. It also works solo.

## Install

Extract the release ZIP and copy the complete `WowTogether` folder to:

```text
World of Warcraft\_classic_beta_\Interface\AddOns\WowTogether\
```

Replace the folder on **every party member's client**, including all **81 Lua
files** and the **Media folder**, then fully restart the client. Restart if a new addon folder does
not appear. Enable Lua errors with `/console scriptErrors 1` during testing.
No Battle.net credentials, external API service or in-game HTTP access is needed.

**0.8.54 also checks travel ordering against published connections.** After the
existing full quest-flow passes, compare step/bundle alternatives while keeping
every required action, prerequisite, escort and onward endpoint. A shorter
estimate cannot delay known rewards before work or worsen progression/log/kill
guards; uncertain branches remain recovery boundaries. Changed legs need
published connections or short local estimates. All 152 sections retain their
12,985 actions; 142 accepted changes improve 60 sections, and 92 stay unchanged.
Bounded travel caches reduce repeated work during loading. These are estimated
complete journeys; source coverage and actual terrain/timings still need
verification. See [ROUTE_OPTIMIZATION.md](ROUTE_OPTIMIZATION.md).

**0.8.53 collects ready rewards during existing visits.** The compiler considers
individual and grouped hand-ins within an estimated 100 yards of a planned
stop, including rewards beyond the old lookahead. Earlier collection matters
even when the final reward total, log peak and minimum-level shortfall are the
same. Every objective must retain at least as much previously collected quest
XP; earlier XP alone cannot justify additional full-route walking. Work stages,
prerequisites, endpoints and fixed order during play remain. The small guide
explains collecting XP while you are there, and keeps that reason after reload.
Bracket replays also reject losses caused by leveling before a later low-level
reward. The identical-source comparison supports 47 earlier-reward visits in 32 of 152
sections, preserving all 12,985 actions. Combat XP and live travel times remain
unmeasured; this is not a guarantee of a level or globally optimal XP/hour.
See [ROUTE_OPTIMIZATION.md](ROUTE_OPTIMIZATION.md).

**0.8.52 considers overlapping quests as a complete trip.** A single quest move
can leave the same area needing another visit. The fixed-guide compiler now
also compares two or three nearby later quests and their pickup/unlock/work
dependencies together, retaining the whole guide and its onward endpoint.
The full-route comparison accepts nine additional changes in seven of 152
sections without worsening log, known progression, combat or geography guards.
Started guides keep their order; actual NPC offers and personal progress still
control which steps are ready. See [ROUTE_OPTIMIZATION.md](ROUTE_OPTIMIZATION.md)
for the comparisons, bounds and unmeasured assumptions.

**0.8.51 gives leveling guides compact, clickable cards.** Each card keeps its
title and quest count. Select it to preview the ordered quests, then use Start
route in that window. The bracket stays in the left dropdown; an All levels
view names sections in their titles so identical zones remain distinguishable.
Supplies and party catch-up appear under More in the preview when relevant.
Browsing preserves the running guide; starting keeps the existing level and
current-quest choices.

**0.8.50 considers useful hand-ins as well as distance.** The existing fixed-guide compiler can
bring a prerequisite hand-in, follow-up pickup and overlapping objectives into
one trip. It retains every action and the same endpoints, rejects increased
quest-log pressure, known progression/difficulty shortfalls and repeated kill
work, and ignores tiny estimated savings. Same-hub hand-ins can also move before
new pickups when they reduce held quests or known XP shortfalls without adding
travel. Their objective work stays in place. Explicit `<NYI>`/`<TXT>` placeholders
stay searchable in All quests but no longer become leveling instructions.
Published ground/transport links
inform comparisons without assuming personal flights or hearthstones. Live
NPC availability, progress, recovery and fixed order during play remain intact.
Arrow reasons explain useful unlock, reward and quest-log visits. All 152 guide
sections are compared against the previous planner with the same valid quest
scope; removing placeholder records is never counted as a route optimization.
This is a bounded search,
not proof of optimal XP/hour or complete world mapping. See
[ROUTE_OPTIMIZATION.md](ROUTE_OPTIMIZATION.md) for evidence and remaining gaps.

**0.8.48 opens on Recommended.** A featured leveling card suggests a suitable
unfinished zone section, with a short reason and quest progress. Personal cards
show the crafting professions you know, their current skill, selected goal and
next action. Continue returns to an active guide without changing its order.
Browse the other sections from the menu; saved searches and future-level filters
do not affect the home recommendations. Viewing the screen starts no guide.
Cards refresh after quest/profession updates; resizing only reflows their geometry.
The same guide eligibility and crafting planners remain in use. Dailies and mount
guides can be added later, when supported. See [RECOMMENDED.md](RECOMMENDED.md).

**0.8.47 groups auction shopping by what you will craft.** Expandable recipe
boxes follow the planned craft order and show approximate crafts, skill range,
preparations, materials to buy and estimated cost. Shop for one part at a time;
bag stock and earlier outputs are shared across boxes. Search fills a supported
commodity display's buy quantity once you select the matching material, keeping
manual edits and native stock limits. Purchases remain manual. Unresolved item
details, rejected queries and missing auction replies cannot hold the scan
indefinitely; skipped items appear in its summary and diagnostics. Actual Forever
quantity controls and the reported 10/40 stall still need in-client retesting.
See [PROFESSIONS.md](PROFESSIONS.md).

**0.8.46 explains why each destination matters.** The guide window, standalone
arrow and quest-list previews share reasons based on useful follow-ups, nearby
eligible pickups, accepted objectives, grouped rewards, dungeon preparation or
training. Lower-level prerequisites name the worthwhile later quest. A long
generic pickup says that no special unlock is known and offers Skip quest;
unverified requirements name the NPC to check. Previews use their own guide's
facts. Arrow text wraps without changing saved geometry; the standalone-only
layout shows its reason without a hover. The audit checks all 5,230 records and
152 compiled guides; explanations do not fill missing map/prerequisite data or
prove globally optimal travel. Fixed order, eligibility and progress remain
unchanged. See [GUIDE_REASONS.md](GUIDE_REASONS.md).

**0.8.45 compares nearer unlearned flight masters with the known journey.**
When a nearby friendly master has a published connection towards your unlocked
destinations, compare walking there, connecting flights and travel after landing
against the current route. Ratchet's neutral ownership is now included. A check
qualifies only with a meaningful estimated saving and a short fallback detour.
The arrow says Visit Ratchet and explains the potential saving until you open
its flight map; only that menu can confirm the flight. Keep walking resumes the
known route without skipping a quest. Confirmed unreachable connections override
reference facts. This applies to supported locations across guides, preserves
their quest sequence, and uses estimates rather than certified road paths.
The bundle adds 266 directed, faction-scoped reference connections; it never
unlocks flights or automatically takes an unconfirmed route. Retest the Ratchet
case on the current beta; see [TRAVEL_DATA.md](TRAVEL_DATA.md).

**0.8.44 tightens active quest-mob stars.** Possible item-drop sources in the
catalogue are checked against unfinished, readable objectives. A public false
from the client's active quest-mob flag rejects a local-only mob association.
An unavailable/restricted flag can retain a matched pending objective; it cannot
confirm an unmatched source. A native true cannot add unknown or future mobs.
Completed individual objectives hide their stars while other work remains.
Synced party needs and friendly pickup/turn-in markers remain separate. These
rules apply across quests, without changing guides, skips or source data. The
reported Winter Wolf star's owner remains unconfirmed: our star normally has a
quest tooltip. Test Settings → Quest markers → Nameplate markers when back online,
and capture the tooltip plus `/wt probe`. Actual beta flags still need retesting.

**0.8.43 improves nearby flight-path discovery.** A friendly unlearned master
within 350 metres gets a reminder beneath the guide window or standalone arrow.
A master up to 750 metres ahead can also qualify when the current leg adds at
most 200 metres of estimated extra walking. The reminder names the stop and
explains the benefit for future trips; hover for coordinates. Discovery checks
all 71 bundled locations with native taxi IDs, plus client-observed masters,
instead of only the 36 settlement labels. Your other flights do not unlock this
one. Public character unlock/ownership observations take priority; uncertain
unlocks say Check. Opening the flight-master map confirms access. Quest order
and confirmed travel connections are retained. Locations and live reminder
behavior still need testing on the current Forever beta.

**0.8.42 polishes guide windows and destination advice.** Smaller guide-start,
profession-scan, activity and party prompts now resize and remember geometry.
Quest lists, materials, the profession viewer and diagnostics reflow their text
and controls; guide/dungeon resizing uses a stable top-left anchor and ends cleanly
when the mouse is released outside the grip. Dragging changes geometry; it does
not replan a guide. The arrow explains why a long trip is needed: a skill cap,
useful prerequisite, grouped visit or the fixed guide you selected. Hover for
quest/NPC actions and full transport details without opening the browser.
Newly compiled guides can combine larger nearby pickup/turn-in visits while
retaining quest stages, prerequisite hand-ins and escort adjacency. Existing
fixed guide order stays saved. The source pass reviews all 5,230 records and
152 faction/level-section guides, and supplements 231 captured pages with 11
missing mapped points and item/NPC references. Coverage remains partial.

**0.8.41 removes two avoidable taint paths.** Guide changes now select quests
through the native API without calling Blizzard's Lua quest-details UI helper.
The auction materials panel is movable and no longer moves Blizzard's auction
window. **Fully restart the client after installing this hotfix.** The reported
aura/Edit Mode error needs a fresh-client beta retest; host checks cannot prove
that client-side taint is eliminated.

**0.8.40 adds goal-based auction shopping.** The panel sits left of the auction
house with a scrollable material list, approximate amounts to buy after stock,
per-item Search buttons and a skill-goal selector. Scan auction house prices the
selected profession's materials and viable alternatives through a paced queue.
Prices are saved for this character's realm/faction/build for up to six hours;
new prices can change current work and the estimated path to the goal. Buying
intermediates is compared with making them from raw ingredients plus craft time.
You buy, train and craft yourself. Test the exact-query APIs in the beta.

**0.8.39 refreshes crafting progress.** Starting a guide offers Scan current
progress: click to open the profession window and refresh skill, learned recipes
and materials. Scan guide offers it again after training. Empty/partial recipe
reads retain learned recipes; current client reagents also cover preparation
crafts. Craft estimates stay visible while gathering or training. Mob hints
require accepted quest objectives rather than generic quest flags or future
quest-start drops. Eligible elite/raid quests remain in solo guides with a brief
group explanation and the choice to Skip quest. Retest the window opener in beta.

**0.8.38 adds material forecasts and AH shortcuts.** Materials offers Next batch
and To skill goal. The estimate subtracts bag stock once and reuses planned
intermediates; yellow/green skill gains can change quantities. Search AH buttons
and a small auction-house toolbar search one selected material per click. Public
commodity, item-auction and supported legacy results can supply session prices.
New prices immediately reconsider even an unfinished batch, using actual skill
and remaining stock. No buying, background price scan or crafting is automated.
Craft counts estimate the remaining skill milestone from the recipe's skill-up
chance and points per gain. Failed gains leave the gap unchanged; actual skill
ends the step. The former fixed 1/3/5-craft limits are removed.
Recipe training below the current cap no longer forces an Expert-rank detour.
Opened trainer offers can override stale rank listings on the same character and
build; training steps explain the recipe milestone or why the cap must rise.
Explicit level-0/zero-XP entries such as Applejack Still stay out of leveling
guides across all zones while remaining in All quests. Full-route map lines show
quest order, including later eligible work; they are not terrain paths.
Native AH/trainer behavior still needs beta testing. See [PROFESSIONS.md](PROFESSIONS.md).

**0.8.37 tracks remaining crafting work.** All six crafting guides show actual
skill and the next milestone. Partial batches count down after matching public
craft casts; consumed intermediate materials are deducted from remaining work.
New batches start from your current skill, including when crafts give no point.
Fresh skill-line readings take priority over stale crafting-window snapshots.
Reload preserves the unfinished batch. Profession logos are fully visible on
the existing cards. The guide chooses batch quantities; the Personal professions
settings category is removed. Main navigation is Leveling, Professions, Dungeons,
Quest log and All quests. Native craft-event delivery still needs beta testing.

**0.8.36 adds six personal crafting guides.** Choose Profession guides to see
compact cards with learned professions first. Preview a skill path, choose a
goal, then Start crafting guide in the same small window used for quests. Your
profession skill, learned recipes, bag stock and skill-up colors decide the next
batch; character level gates rank training. Materials opens a buy list, and
training steps name a friendly NPC. Guides update after crafting/training and
resume after reload. Crafts and purchases remain manual. Future paths, skill-up
chances and costs are estimates; missing prices stay unknown. Open your profession
window to supply live recipe data. See [PROFESSIONS.md](PROFESSIONS.md).

**0.8.35 makes dungeon browsing compact.** Dungeon cards form two columns at
normal window sizes and three when wider, with the existing faint artwork,
level range and short quest summary. Click anywhere on a card to open its
journal. Quest list and Start quest route sit together there; starting reuses
the small guide for collection, the run and hand-ins. Browsing never starts or
replaces a guide. Map only keeps these actions hidden during gameplay. Zone
guide cards retain their wide layout. Resizing reflows existing cards without
replanning routes; retest text wrapping and artwork in the beta.

**0.8.34 splits zone guides into level sections.** Each newly selected section
has its own 1–10, 11–20, 21–30 or later quest set, quest list and XP estimate.
Earlier required quests and nearby linked continuations stay included, with
useful low-level exceptions explained. All levels lists the separate sections;
future sections can be previewed, but real pickup rules still apply. Scan, reload
and movement preserve the selected scope and fixed order. Existing saved
full-zone guides retain their scope. The next useful section can be suggested
after current work ends; it never replaces your guide automatically.

**0.8.33 keeps dungeon guides through the run and hand-ins.** After collecting
quests and entering, the guide waits for objectives. Ready quests then route to
their actual turn-in NPCs; unfinished quests stay pending. Scan and reload retain
that phase and quest set. Individual Route to pickup still ends on acceptance.
Confirmed flight connections survive weaker conflicting map discovery flags.
Saved positions or published distances provide estimated flight costs when live
geometry is missing, without inventing connections. Directions name the next
transport, including zeppelins before later flights. Boarding retains that leg
until reaching its destination; Scan can recalculate. Retest remembered flights
after reload, transport boarding/arrival and dungeon returns in the beta.

**0.8.32 adds current-step elite spawn hints.** Known possible locations for the
unfinished elite kill/drop target show as skulls on the world map. They clear
when that objective finishes, is skipped or the guide changes/stops. Full-route
preview never adds future hunt skulls. In synced parties, markers remain while
a member still needs the objective. Turn the overlay off in Settings → Quest
markers. Positions are reference facts, not live spawns; older-world coordinates
apply only to unchanged quests and need beta retesting. See [QUEST_DATA.md](QUEST_DATA.md).
**Open guide**, beside Diagnostics, brings the small guide window back. After
Exit (×), it opens empty; starting a guide reuses it. An active hidden guide keeps
its current progress when reopened. The browser closes so the guide is visible.

**0.8.31 corrects dungeon loot.** Classic encounters use original Vanilla IDs,
with captured Forever changes. All 933 published Vanilla NPC tables and 95
treasure-container tables were audited. Trash mobs and treasures have their own
loot beneath bosses, without extra map markers. Shared/world drops are separate
from encounter loot. Hall of Thanes, Ruins of Lordaeron and Excavation Site:
Wetlands include explicitly reported beta drops; other unpublished Forever loot
remains unknown. Item facts load on demand. BG changes the guide background;
ST stops the guide and leaves an empty window, while × / Exit guide stops and
closes it. Neither leaves a guide running or a saved guide to resume.

**0.8.30 adds dungeon preparation guides.** Start route collects all suitable
dungeon quests across zones and their necessary prerequisites, then directs you
to the entrance. Already accepted quests count as collected. Known transport and
flight links help order the visits; planning yields behind Loading route, and
normal progress preserves the itinerary. The same small guide window serves
leveling and dungeon guides. Quest cards show giver, zone, level and status, with
filters and an individual Route to pickup action. That route ends on acceptance.
No entrance-recording button is needed. Missing offers or locations remain pending;
travel estimates are not a guarantee of the shortest terrain-safe path.

**0.8.29 reduces database memory.** Quest metadata stays ready for browsing;
nested locations/requirements unpack on first use. NPC/item/object records and
dungeon details stay compact until requested. The complete source facts and
guide decisions are preserved. Retained Lua 5.1 host memory falls from about
52 to 25 MiB at startup, and 55 to 30 MiB after browsing, a guide and a dungeon.
Actual beta memory includes client allocations and needs measurement. `/wt probe`
shows loaded records/detail fields by compartment and total memory when the
client exposes its memory API. See [PERFORMANCE.md](PERFORMANCE.md).
The guide-step window now has a resize handle and close button. Size/position
persist; attached panels follow its width. From 0.8.31, closing stops your guide.
Reopen with `/wt arrow` or Arrow and map → Show the direction arrow.
Dungeon quest lists refresh your character details and hide incompatible or
unverified identity requirements. Dungeon Start route starts directly; Quest list
remains a separate preview, and missing destinations wait within the chosen route.
The dungeon journal opens above the main window. Selecting a mapped boss changes
to its floor. A class dropdown starts on your class and filters known weapon and
armor types; All classes shows every drop. Unclassified items stay visible.

**0.8.28 fixes background refresh work and shared event subscriptions.** Sync,
zone entry and objective events keep guide progress current without rebuilding
a closed dashboard. Visible background refreshes use a short batch with fresh
history. Existing subscriptions are reused when chaining viewer handlers;
unsupported events and handler errors remain visible. Retest in the beta.

**Dungeon portrait and quest markers** remain available. Portraits open that
boss's loot, including from Map only. Quest icons show pickups, objectives and
turn-ins for the actual NPC/object location; **Quests** hides/shows them.
Completed quests and incompatible faction/class/race quests are hidden. BFD's
invalid level-9999 placeholders no longer appear as real boss levels.
The source snapshot maps **158 bosses and 139 quests** across the 19 Classic
complexes. Some boss/floor/quest positions and new Forever dungeons remain
unresolved. Reference points require matching artwork; native exact-floor boss
positions take precedence. No coordinates or portraits are guessed.

**0.8.26 simplifies player-facing text.** Dungeon windows, settings, profession
guides, quest previews and map tooltips keep actions and useful information
concise. Technical source notes and API explanations stay in diagnostics and
documentation. Missing content uses short
messages such as **Map unavailable**; useful prerequisite explanations remain.

**0.8.24 adds the Dungeon viewer.** Clicking a dungeon card opens its journal from anywhere.
The map-level dropdown appears only when multiple maps are available. Click a
boss and browse notable drops with item icons, search,
filters and cached client tooltips. Dungeon cards keep **Quest list** beside
**Start route**. Entering a recognized dungeon optionally asks **Open map?** and
opens a compact movable map. Both views resize and stay open during combat; their
positions, sizes and BG choice are saved across all dungeons and reloads.

The offline snapshot contains 243 encounters and 2,766 notable drop entries across
19 Classic complexes, with 164 client portrait references and 19 client map
reference sets. Current exposed client floors/markers take precedence. Older
layouts can differ from Forever; unknown boss positions are not guessed. New
Forever dungeon boss/loot coverage remains incomplete. No external image files
are bundled. See [DUNGEON_VIEWER.md](DUNGEON_VIEWER.md) for sources and beta limits.

**0.8.23 improves flight timing following Romits' report.** Untimed rides use
the native flight map's connecting stops when public `GetNumRoutes` and
`TaxiGetNodeSlot` results are available; otherwise they retain the distance
estimate. Actual flight paths can curve between those stops, so first trips
remain clearly labelled estimates. Walking-time calculation is unchanged.

Short, bounded retries handle departure/landing events arriving before the public
taxi state or position settles, even with both arrow panels disabled. A one-second
read-only slot snapshot identifies manual flights when the map closes before its
selection hook runs. A duration
is saved only after an observed departure and confirmed arrival within 300 yards
of the selected flight master. Interrupted, stale, unknown-position or untracked
rides do not become full-trip measurements. Arrival retries preserve the original
landing time, excluding walking after the ride. Reloading during a ride loses its
departure capture; that partial ride is not learned.

Validated timings are personal, directional, client-build scoped and matched to
the native connecting route when available. Both timers and travel planners use
the same timing source. Older unverified samples remain saved but are excluded
until a confirmed ride replaces them; after updating, some countdowns will
therefore say Estimated again. `/wt probe` now includes connecting-route
capabilities, timing counts, recording status and expected/actual duration.
See [TRAVEL_DATA.md](TRAVEL_DATA.md) and test native behavior on the current beta.

**0.8.22 adds official Blizzard artwork to Dungeon quests cards.** One faint
image stretches across the whole card at 14% opacity, leaving the text and
controls clear. Native dungeon-journal images take precedence; published client
references cover all 19 Classic complexes and four Forever dungeons. The five
remaining Forever dungeons use their journal art when available, otherwise a
neutral Blizzard dungeon-wall background. Missing assets leave a plain card.
Artwork resizes with pooled cards and changes neither routes nor quest progress.

The addon references artwork already in the game; no Blizzard images or Wowhead
screenshots are bundled or downloaded in-game. Filename metadata and API sources
are documented in [DUNGEON_ARTWORK.md](DUNGEON_ARTWORK.md). Client asset availability
and actual beta rendering still need testing; `/wt probe` reports capabilities
and resolved-image counts. Restart fully if newly referenced textures stay blank.

**0.8.21 adds optional class-training stops.** Under **Settings → Leveling guides →
Include convenient class training** (default on), each even level makes a personal
training check due. It appears near a pickup/return or before leaving a known hub:
the trainer must be within 150 metres and the estimated added walk at most 150
yards. Nearby objective work is not interrupted. The same rules apply across
leveling guides, using your class and known friendly trainer ownership.

Train manually, then choose **Done training** or **Skip training** to resume
quests. Both save that choice for this character until the next even-level check,
including after reload. Pending visits are retained with their selected guide.
The standalone arrow has Done/Skip buttons when the guide panel is hidden.
Training does not buy spells, reorder quests, change skips or sync service visits
to friends; its toggle is separate from Include class quests. The 151 attributed
trainer locations cover all nine supported classes; spell availability and trainer
rank caps are not inferred. Check locations and actual training in the beta.

**0.8.20 checks walking segments for known enemy settlements.** It repairs
missing flight-point ownership, including Astranaar, and prevents cached flights
from bypassing that check. Dijkstra can choose another published connection;
where no bypass is mapped, the crossing map line is hidden and the guide says
to go around the town. Quest markers, order, progress and skips are retained.
Friendly/neutral places and flight rides stay usable. The 48 settlement footprints
bound published occupied locations with an estimated 100-yard margin; they are
not guard boundaries, verified roads or a collision mesh. Retest on the beta.

**0.8.19 follows the current guide quest in Blizzard's quest log/map.**
**Arrow and map → Highlight the current guide quest** is on by default. It
selects and tracks accepted current quests once when the guide target changes,
waits until combat ends, and keeps working with the arrow panels hidden. It
does not open the map or add a user waypoint. The beta must expose the native
selection/tracking APIs, and native highlights require its own location data;
/wt probe reports capabilities and the current selection status.

The guide shows a compact **Use item** button when the current accepted objective
has a special quest-log item. Click it outside combat to call
`UseQuestLogSpecialItem(questLogIndex)`; select any required target yourself.
The index is verified again on each click, including after log entries shift.
Progress/bag/item-data changes refresh the button; it never uses items on its own.
Native targeting, cooldown and item-use behavior still need beta testing;
missing/restricted item data keeps the button hidden and `/wt probe` reports the
API capabilities. The button appears with the main guide panel.

Complete NPC offer lists now retain absence evidence for your character and
build across unrelated progress and reload. Unavailable pickups remain pending
until the giver actually offers them; they are not completed or manually skipped.
Fresh offers restore the existing fixed stages. Other characters/builds and
unchecked alternative givers are not treated as blocked from that observation.
Our Ancient Enemy and The High Chieftain require actual offers while their exact
Forever unlocks remain unresolved. No new prerequisite/race restriction is guessed.

The two published Report to Kadrak IDs (Thork/Darn Talongrip) are now recognized
as mutually exclusive alternatives. Having accepted or completed one prevents
a duplicate pickup of the other. The chosen quest keeps its work/turn-in; this
does not grant completion to the unchosen quest. Matching titles alone never
create this relationship.

**0.8.18 improves travel and item collection progress.** Flight-map destinations
are stored in their own zones, including repaired saved continent points, so
known flights join the walking graph correctly. Reachable connections still
come from your character's native flight-master map; unlock flags alone do not
create flight links. Open a flight master after updating to confirm its routes.
The arrow separates estimated/timed **flight duration** from the **whole journey**
including walking. Actual rides show the same countdown above the standalone
arrow and in the guide panel; untimed rides are marked estimates, and elapsed
time replaces an overdue estimate. Completed rides improve personal timings.
Walking/mount ETAs use public running speed and distance to the next waypoint;
terrain and stops can add time. Transport steps identify the boarding location
and coordinates. Quest pins and full-route previews stay visible during flights;
ground lines resume after landing. Enabling the standalone arrow hides the
duplicate direction graphic in the guide panel, keeping instructions/controls.

Collection steps with known item IDs/counts now check your bags, including
Ishamuhale's Fresh Zhevra Carcass, and advance on bag updates. This applies to
fixed and adaptive guides; it does not complete the quest, a kill/use step, or
another player's progress. Native objective quantities take precedence over
older published counts. Include class quests defaults on for new/unset settings;
saved opt-outs and other-class exclusions remain respected.

**0.8.17 combines the Forever dungeon overview with dungeon quest lists and
published Forever entrance geography.** All **19 Classic dungeon complexes**
have entrance areas, including the level ranges for Scarlet Monastery, Maraudon
and Blackrock Spire wings. The browser also includes the nine new Forever
dungeons; four have mapped entrance areas, while the remaining five keep their
broad locations and explicitly unknown coordinates/quest sets. **339** captured
dungeon quest memberships join the existing catalogue without changing quest
facts. Duplicate dungeon labels are folded together; a Dungeon tag alone no
longer creates class, capital or raid cards. Unassigned records stay in All quests.

Dungeon cards distinguish run levels from the level needed to collect your
character's full quest set. **Quest list** shows known pickups, entrance areas
and wing ranges; manual entrance recording remains inside that window. Recorded
entrances take precedence, then public client map links, then published points.
The entrance remains the collection route's final destination across zones.
Run ranges never override identity, quest levels, prerequisites or actual offers.
These are entrance areas, not mapped paths through caves or guaranteed portal
positions. [DUNGEONS.md](DUNGEONS.md) records coverage, source hashes and two
conflicting new-dungeon level descriptions; the overview's chart/table is used.

**0.8.16 replaces internal travel-point names with readable directions.**
Anonymous junctions say, for example, **Go to waypoint — The Barrens (54.0, 26.6)**
in the guide panel and map tooltip. Coordinates are map percentages. Known gate,
dock and flight-master names stay visible. The short explanation identifies the
destination zone and tells you to follow roads and terrain to the waypoint.
This applies across the travel network without changing its points, quest order
or Dijkstra costs. `/wt probe` includes the current leg, coordinates and final
quest/destination for diagnosing terrain reports. Walking links remain estimates;
the reported label alone does not establish a wrong path through terrain.

**0.8.15 focuses on Scan guide and personal quest progress.** Scan reads a fresh
quest log before objectives/history, retries briefly while the client catches up
and rechecks if progress changes during a large scan. It advances the retained
fixed order even with the dashboard hidden or resizing. An unavailable snapshot
keeps the last valid progress and saved skips; it cannot claim guide completion.
The arrow shows a loop while scanning, then returns to directions.

The leveling band remains **three levels below to three above** the character
(or lowest synced party member). Useful lower-level prerequisites stay in the
guide: the panel labels the exception and names the quest it unlocks, including
its level or dungeon purpose. For example, at level 21, level-16 Harpy Lieutenants
can qualify because it unlocks level-20 Serena Bloodfeather. Unrelated low-level
unfinished work stays excluded, even if accepted. Ready hand-ins are retained.

Quest-update bursts now share a short, 0.1-second personal refresh; the hidden
dashboard is not rebuilt for those background updates. Party messages retain
their separate two-second batch. These host checks establish less repeated work,
not a measured improvement to live beta frame rate. With zone suggestions enabled,
a suitable adjacent zone can also be offered after leveling when the selected
guide has no useful work ready. Missing-location/NPC checks keep their place;
**Start zone guide / Keep my guide** always leaves the decision to the player.

**0.8.14 adds a tiny BG button at the guide panel's top-right.** Switch between
an opaque background and a see-through fill; instructions, arrow and controls
stay fully visible. The same choice is in Settings → Arrow and map → Opaque
guide background. It also covers the attached nearby-objective/tip panels and
persists after reload. Toggling it does not change the route, skips or travel.

The friends' 23-event Durotar export is preserved and reviewed under `research/`.
It confirms starter-quest NPC offers already in the catalogue. Changing offer
lists and stale history do not establish a new prerequisite; no quest order,
race restriction or map coordinate is changed from this report. Host regressions
replay the supplied evidence to prevent unsupported learned gates. Raw player
exports are kept out of the addon ZIP.

**0.8.13 fixes premature completion across fixed zone guides.** “Guide complete”
requires confirmed completion of the guide's applicable, enabled quests.
An empty runnable list caused by the level/group filter, skips, missing steps
or unknown history leaves the guide waiting instead. Later-level work can return
as the character or party context changes; fixed order, pickup requirements and
the close-level filter remain intact. Ready hand-ins still count as unfinished
until turned in. `/wt probe` now retains completed/unfinished/skipped/unknown
quest counts and filtered-step counts, including after genuine completion.
The arrow's hover tooltip follows its current state rather than retaining an
old loading message. Replace the complete addon folder and Scan the resumed
guide; keep SavedVariables. A leveling guide can still omit optional, excluded
or incompatible quests, so this does not certify completion of every zone quest.

**0.8.12 adds subtle zone-themed guide cards.** Forests, prairie, canyons,
deserts, snow and other original landscape motifs fade into the charcoal
background, keeping the text area dark. Every current zone guide has a matching
theme; the Orgrimmar travel guide uses a settlement motif. Dungeon cards now use
client artwork as described above. Unknown future zones use a quiet fallback. Scenery crops
proportionally as the dashboard resizes, with one reused texture per card and
no animation, polling or in-game downloads. Guide order, eligibility and quest
progress are unaffected. Install the complete Media folder with this release;
restart the client if the new artwork remains blank after reload.

These are original generated landscape illustrations, not game screenshots or
downloaded third-party images. The source atlas and artwork provenance are in
`Media/GuideThemes/ARTWORK.md`; no third-party CC0 license is claimed for them.

**0.8.11 lets you browse upcoming zone guides.** Choose a future bracket or
**All levels** in Leveling guides, then select a card to preview the
complete order without replacing your current route. Starting too early shows
the suggested entry level and a suitable unfinished guide for your current
level, when one is known. Choose **Start recommended**, **Start anyway** or
**Cancel**. An early guide stays selected while its locked quests wait; browsing
never overrides pickup requirements. The default bracket still recommends
guides suited to your actual level.

**0.8.10 fixes the INN_INFO startup error reported on 0.8.8.** The same
unsupported registration was still in 0.8.9. Inn visits now use the modern
Binder interaction enum, with the older binder-confirmation event where supported.
All event registrations check the optional `C_EventUtils.IsEventValid` API and
handle native registration rejection. Failed subscriptions appear in `/wt probe`
without interrupting the remaining files or adding chat warnings. This guard
does not catch event-handler errors or make protected actions safe.
Opening a binding dialog records a visit; it never sets your home. Confirmed
bindings use `HEARTHSTONE_BOUND` only if registered, while public
`GetBindLocation` still hides advice for the current home. Replace the complete
folder and `/reload`; keep your existing SavedVariables.

**0.8.9 makes Include class quests a live guide filter.** Eligible class quests
stay in the saved zone sequence; the checkbox shows or hides their steps in the
arrow, map and quest-order preview without reordering that sequence. Known class,
race, faction, level and prerequisite requirements still apply. Existing manual
skips stay saved. Older zone checkpoints recover omitted class records once on
upgrade. Replace the complete addon folder and reload; clearing SavedVariables
is not required.

**Collect useful quests nearby** also groups already planned, currently eligible
pickups within **100 yards of the next pickup** across guides. Only accept steps
move to that local visit; objective and turn-in order and the saved guide remain
intact. Distance uses public map/world scale, never a guessed map percentage.
NPC dialogue updates availability without recompiling the guide. Known pickup
requirements must pass; uncertain requirements or confirmed missing offers
prevent promotion. Actual offers are required for auto-accept. Escorts keep
their immediate work step.

The compact interface uses matte charcoal panels, subtle gold accents and
Classic headings. The main window gives most of its space to guide rows; the
movable instruction panel keeps its arrow, distance and guide controls together.
Hover over a guide or quest-list row for longer details. Resize the dashboard
from its bottom-right corner; existing sizes and panel positions are retained.
The public Zygor, RestedXP and Dugi sites informed the goal of reducing bulk;
their code, assets and distinctive layouts are not included.

The guide panel names the action and target: accept from a giver, turn in to a
receiver, kill a creature, gather an object, loot an item, or use a quest tool.
Matching public objective progress shows the remaining count beside distance.
The two lines below give a short action hint and the known zone/coordinates;
remote destinations say **Travel to**. Hover the panel, standalone arrow or
quest-order row for full instructions, progress and supplied quest-item names.
Missing objective locations stay explicitly unknown; planning anchors never
appear as coordinates. Text uses recorded facts, not invented landmarks or
copied quest descriptions. This does not reorder or change a guide.

Unconfirmed branching prerequisites name the quest giver. When it is the current
pickup step, a large addon map star and friendly-nameplate hint say **Confirm**;
the arrow leads to the known giver location. **Map NPC** opens that location and,
if the client exposes the required waypoint APIs, places a Blizzard waypoint for
this confirmation only. Actual NPC offers still decide pickup availability.
The addon clears its waypoint when the confirmation ends, preserving a different
waypoint you place yourself. Missing giver locations remain explicitly unmapped.

Nearby accepted kill/gather/loot objectives share a compact **In this area** list
under the guide controls, with separate quest names and live counts. Scroll for
more than three tasks. Groups use known destinations within 250 metres of the
current objective in its uninterrupted objective phase; pickups, turn-ins,
travel, other zones and missing locations stop the group. The compiled guide
order, individual skips and quest credit stay unchanged. This applies to every
guide using the route system, without quest/zone-specific cases. Straight-line
proximity cannot prove terrain access or make missing locations known.

| Command | Action |
| --- | --- |
| `/wt` | Open the resizable dashboard. |
| `/wt config` | Open settings grouped by purpose. |
| `/wt tracker` | Toggle the movable, scrollable party progress panel. |
| `/wt arrow` | Toggle the movable direction and instruction panel. |
| `/wt guide scan` | Refresh progress; fixed guides retain their order. |
| `/wt catchup` | Review a route to catch up synced party members in this zone. |
| `/wt research` | Export this character's raw quest observations. |
| `/wt findings` | Export account-wide observed prerequisite findings and supporting evidence. |
| `/wt questlines` | Inspect the current client's questline table and optional chain quest IDs. |
| `/wt guide reset` | Clear all saved guide skips for this character. |
| `/wt sync` | Request fresh party snapshots; let the send queue drain. |
| `/wt probe` | Open diagnostics; Ctrl+C copies and closes the report. |
| `/wt lua` | Paste read-only Lua API checks and copy formatted results/errors. |
| `/wt route clear` | Clear the selected map route. |
| `/wt minimap` | Toggle the minimap button. |

## Choose and start a guide

The dashboard dropdown contains **Leveling**, **Professions**, **Dungeons**,
**Quest log** and **All quests**, in that order. Optional party progress uses
the Tracker button; sync and guide catch-up controls remain available.

For solo leveling, enable **Settings → Play mode → Solo leveling mode**. This
stops outgoing and incoming party messages, clears peer snapshots/invitations and
hides party views and controls. Even while grouped, the planner uses only your
progress. Local quest updates, guides, arrows and research recording continue.
The toggle persists; turning it off requests fresh party data.
All quests supports level brackets, Near party and search committed on Enter
or after a typing pause. It retains manual browsing of known repeatables.

**Leveling guides** lists real zone-guide sections across the
catalogue, including remote zones. Its default bracket follows the lowest party
level (1–10, 11–20, etc.). Choose another bracket or All levels, and search by
zone, quest or known NPC; Enter or a short pause applies the search. Pages keep
later results accessible. Individual quests stay in All quests, and explicit
quest-log trips are in Party quests.

The default bracket recommends zones containing useful work for the actual
lowest player level, respecting known pickup minimums and prerequisite levels.
Manually selected brackets and **All levels** also show upcoming zone guides;
selecting a card previews the full order without starting it.
Known remote-only objectives cannot
qualify their pickup zone as a leveling area; capitals remain available for
travel and quest pickups inside guides. Empty or isolated single-quest sections
do not create cards. A starter zone can have a later section when the catalogue
contains a real higher-level quest set. Cards show the actual quest-level band
of that section's local quests; earlier prerequisites do not inflate the band.
Where detailed objective geography is unknown, the published zone category is
the fallback; the band is an estimate, not an official zone-level declaration.
Sharing the 11–20 browser bracket does not make level-20 work suitable at
level 12. Starting an upcoming guide opens a warning with its suggested entry
level and an effective unfinished guide for your current context, if known.
**Start recommended** selects that suggestion; **Start anyway** selects the
future guide while locked work waits for its real requirements. **Cancel**
keeps your current route. The early selection and fixed order survive reload.
Unfinished same-level prerequisites
stay inside the full guide. NPC offers still confirm hidden pickup requirements.

Suitable cards are **Recommended zone guide** or **Alternative zone guide**;
future work is labeled **Upcoming zone guide**. All-level browsing ranks suitable
guides first. A questline is a linked chain within a zone and is
planned inside its zone section, without a duplicate standalone card.
Searching for a quest or its NPC finds the containing section.

Brackets select actual quest sets for new guides. Earlier required quests are
retained, including known cross-zone prerequisites. Linked continuations up to
three quest levels beyond a boundary can finish the current chain; unrelated
higher-level work belongs to later sections. **All levels** lists these sections
separately. Existing saved full-zone guides keep their original scope. Changing
the browser bracket or scanning never changes a running guide's quest set.
**Follow fixed zone guides** is on by default. Start route compiles the section
once from catalogue geography and prerequisite dependencies. It does not use your location, active
quests or completion history to choose the order. The arrow shows **Loading
route…** while generation runs. Progress then advances completed pickups,
objectives and hand-ins, keeping the saved numbered sequence. When nearby pickup
collection is on, eligible accepts within 100 yards can be gathered at the current
pickup visit; the remaining objective/hand-in order stays intact. Abandoning a quest
can restore its pickup instruction, but does not reshuffle the guide. Scan guide
refreshes progress in that same sequence. During a user scan, a rotating loop
replaces the direction arrow in both arrow displays. History batches yield to the
UI; the arrow returns after scanning (and adaptive planning, when enabled).
Switching or clearing a guide cancels its pending scan. A guide waits when its current pickup
is locked or its location is missing; Skip step / Skip quest remain available.
Catalogue-based routes remain partial where published coordinates are missing;
these are generated guides, not fully hand-verified walkthroughs.

With **Collect useful quests nearby** enabled, opening an NPC's complete list
can add a short pickup group for useful quests already in your selected guide.
Collect those quests in one visit even when their original pickups were later
in the sequence. This also works when all pickup coordinates were already known.
The compiled objective/hand-in sequence and its saved step keys stay unchanged;
once collected, the guide continues with the first remaining original step.
Level usefulness, identity, prerequisites, completion and manual skips still apply.
Unrelated NPC quests remain manual. With **Open guide quests at an NPC** and
**Accept the quest dialog I open** enabled, each returned native NPC list selects
the next pickup. The addon does not reopen a closed NPC dialog remotely.

Public NPC offers save approximate pickup locations for the current build on this
account. These fill missing pickup points at runtime, including after reload and
on another character, without inventing objective or turn-in locations. They are
the player's dialogue position, not an exact NPC spawn. Availability is personal
and rechecked each session; a saved location grants no pickup or completion credit.
Pending pickup-group instructions survive reload. **/wt findings** includes the
observed pickup locations for manual feedback; nothing uploads automatically.

The selected guide now resumes after `/reload` or login. Each character saves
its selection, complete fixed sequence and trip quest set; current quest history
and peer snapshots supply progress. Resuming does not reopen the map or invite
friends again. An addon upgrade recompiles the fixed sequence from updated data.
Outside-guide questing, temporarily unavailable pickups and a finished route keep
the arrow and controls visible. **Clear route** ends the selection and removes
its saved checkpoint; saved quest/step skips are a separate setting.

When a normal synced party has useful progression gaps in the current zone,
**Catch up party** offers an adaptive route for missing prerequisites and nearby
objectives. The existing guide stays selected until you accept. Use the zone
card's Catch up party button or `/wt catchup` to review it again. Friends still
choose **Follow route** or **Keep my route**. Unknown or stale history cannot
establish that someone is behind. Low-level work needs a useful chain or active
quest; required earlier stages explain their purpose under the arrow. Repeatables
and profession quests are excluded. Every zone uses the same known prerequisite
checks; absent catalogue facts still require actual NPC observations.

Guide cards distinguish total quests from published pickup, objective and
turn-in coverage. **Show full route** shows all currently eligible mapped quests,
including those beyond the former six-quest/twenty-stop trip limit. Locked future
quests remain in the internal sequence and enter the map preview after unlocking.
Browse another map to see that zone's eligible markers. The starting line follows
your live position, including when the next stop is in another zone. Public world
coordinates project the line onto the viewed zone or continent map; zone views
clip it at their edges. Entering the next zone continues the direction toward its
destination. This changes drawing, not the fixed guide sequence. Missing/private
coordinates or another continent leave a gap and travel instructions instead of
a made-up connection. These are straight visiting directions, not terrain-aware
roads. Focus next steps restores the short preview.
These controls sit below the map viewport, outside the quest drawing area.

Turn **Follow fixed zone guides** off and start a guide again for adaptive trips.
Those compare nearby dependency-ready walking orders, with up to six quests and
twenty stops per active trip. Their full map preview still includes all eligible
mapped quests. Straight lines express visiting order; follow terrain and roads.

As useful work leads into a suitable nearby zone, an optional popup offers
**Start zone guide** or **Keep my guide**. For example, a known Durotar chain can
continue toward the Barrens while the full Barrens guide is offered. The same
catalogue, level, faction, progress and adjacency checks apply to other zones;
there is no special Durotar/Ashenvale route script. Missing links or locations
remain unknown, and a popup never changes the guide by itself.

**Show route** previews a selection locally. **Start route** starts it and
invites friends with **Follow route** / **Keep my route**. Their route stays
unchanged until they choose to follow. Invitations share selected quest IDs
and pickup roles, up to 20 IDs; each recipient plans against received party
progress rather than copying the sender's coordinates or completion flags.
Zone/questline invitations also identify the selected section and bracket,
so recipients reconstruct its scope beyond the twenty packet IDs. Older
full-zone invitations retain their original full-zone scope.
Update all clients together to use these new invitation modes.

Selecting a leveling-guide card opens a movable, scrollable,
read-only list of every pickup, objective and hand-in in guide order, including
later locked steps. It shows levels and progress, and labels missing locations.
Opening it does not start, switch or save a route. A started fixed guide supplies
its existing sequence. In adaptive mode this is a catalogue-order preview;
the trip's travel order is calculated when you start. Use **Start route** in
the preview's footer when ready.

When you start a new guide while quests are already in party logs, choose
**Start selected guide** or **Include current quests**. The popup explains
that including scattered current quests can cause unusual routes and long
detours. Both choices filter unfinished low-level work; ready hand-ins and useful
prerequisites remain. The former global current-quests-first switch is no longer exposed.
Quest-log plans remain available without replacing an explicitly chosen guide.

**Path to Orgrimmar** is a personal travel guide in Leveling guides, available
to Horde characters from levels 1–60 in each bracket. Search Orgrimmar and Start
route; it compares known city gates and uses the travel graph for crossings,
transports and character-confirmed flights. It does not pick up quests or invite
friends. It survives reload and finishes when you enter Orgrimmar. Scan refreshes
the journey; a missing connection is explained with the guide retained. It uses
the travel graph for this explicitly selected journey even when graph guidance
for ordinary quests is off. Walking costs/transport waits are estimates, so this
chooses the quickest known path rather than guaranteeing collision-free travel.

Normal quest acceptance and zone updates retain the selected quest set.
A committed unfinished objective stays selected while crossing a zone.
In adaptive mode, **Scan guide** refreshes the selection and optimizes it
again. Fixed mode only updates progress in the existing sequence. Ready turn-ins and unfinished friends' work remain separate stages.
Arrival alone never accepts, completes or hands in a quest.

## Planning and party progress

- New leveling pickups use the lowest synced party level and known faction,
  class, race and completion requirements. Discovery favors the current zone
  and suitable known neighbors. Opposing-faction starters and distant unlinked
  zones do not become automatic recommendations.
- Low-value work is filtered while advancing fixed guides as well as planning
  adaptive routes, retained quest/circuit routes and current-quest routes. The
  preferred band is three quest levels below to three above the lowest synced
  player's level. Unsynced/stale member context cannot lower that band.
  This is a leveling preference, not a statement that lower quests give no XP.
  At level 23, the normal band is 20–26; Centaur Bracers (level 14, no known useful
  continuation in the shipped data) is excluded from new pickups and unfinished
  log work. Ready hand-ins remain. Compiled steps retain their order and receive
  no false completion or manual-skip credit when filtered.
  An earlier quest can remain when a known
  useful follow-up or a suitable dungeon quest justifies it; the arrow explains
  the exception. Include current quests respects the same band. Unknown follow-ups
  cannot justify a low-level detour. The catalogue stores quest/minimum levels
  and published base XP where known; this filter is not a tested Forever XP
  formula or an exact reproduction of Wowhead's difficulty colors. Diagnostics
  show the band and player it uses, while quest details explain exceptions.
- Collector's Edition **Welcome!** rewards are excluded from leveling guides,
  including older retained plans. All seven catalogue variants remain browsable
  in All quests. Bonus exclusion rules are retained separately for future imports.
- Among members with comparable known history, the guide focuses on the member
  furthest behind in its selected quests. Unknown history does not prove a
  player is behind. The lowest level is the fallback; missing snapshots retain
  confirmed stages while sync catches up. A downstream prerequisite cannot be
  treated as done because a more advanced player already completed it.
- Eligible nearby pickups can join a quest-log trip. The original walking
  budget limits additions rather than expanding repeatedly to distant quests.
  Pickups precede their objectives and returns; local work precedes long delivery
  detours. Disable **Collect useful quests nearby** for a strict log-only plan.
- Known repeatables stay outside automatic leveling plans. Group/elite quests
  are labeled and excluded from automatic solo discovery. Class quests are an
  optional inclusion with restrictions; profession quests remain personal.
- **Quest log review** suggests reviewing low-value unfinished work. It never
  abandons a quest. Ready turn-ins and class/profession quests are not included
  in those suggestions.

Sync is automatic on party, quest/objective, level and zone events, batched
before a paced send queue. It suppresses unchanged updates and retries explicit
throttle responses. Successful sends or self echoes do not prove peer delivery.
Diagnostics distinguish peers waiting for snapshots from received progress.
Party identity supports public first-name/surname forms found in this beta;
ambiguous sender matches are rejected.

The progress panel shows personal item/kill counts for each player. It opens
when joining a normal party, hides when solo or in a raid, and can be dismissed
for the current party session. Its background and height have clear dropdowns.
A completed player does not erase another participant's remaining objective.

## Arrow, map and guide controls

The Classic-style panel shows the quest, arrow, distance, action and two small
context lines. Actions distinguish **Kill**, **Pick up** and **Talk to [NPC]**.
Choose yards or metres in **Arrow and travel** settings.

The left/right buttons preview prior and later steps without changing quest
credit. Already accepted pickups and completed quests can supply previous
published locations, labeled **History preview**; these do not establish the
order in which a player actually visited them. Visited guide steps are also
kept for the current session.

**Skip step** and **Skip quest** persist per character. They do not unlock
prerequisites or change friends' progress. Recording saves these as explicit skip
events, without inferring NPC absence or a prerequisite. Button tooltips explain
the distinction. **Scan guide** reads actual quest
logs, objectives and completion history, then returns to the current fixed step, or rebuilds the useful adaptive plan without a report popup. History scope includes
known series and prerequisites and is bounded to 512 IDs. Large history scans
yield between batches and restart at most twice if quest/level events change
progress during the scan. A log that is temporarily unavailable gets at most
three short read attempts; if it remains unavailable, retry Scan after loading.
Restricted values remain unknown; peer history waits for received snapshots.
There is no extra "Guide replanned" footer below the arrow controls.
Diagnostics distinguish full guide quest counts, trip quest counts and stops:
one quest can supply pickup, objective and turn-in stops, so eighteen stops do
not mean eighteen quests. Completed progress and missing coordinates also
affect each trip; compare the guide identity and scope before comparing counts.

**Reconsider skips when scanning** is off by default. When enabled, Scan clears
skips for quests in the selected guide only after a successful fresh scan. A quest shared with
another guide has the same saved skip. **Reset guide skips** clears every guide's
skips for this character, across zones; other characters are unaffected.

World-map lines show visiting order, with the current place and two ahead by
default. Map controls choose zero/one/two places ahead or the full route.
Consecutive steps at a shared NPC stay grouped. Hover clustered pins for all
steps. Viewing another zone preserves the route; **View route zone** opens its
current destination map. No segment joins unrelated zone coordinates.

Drawing projects onto the public map viewport, clips at its edges and redraws
after pan, zoom and resize. Existing verified unprotected addon geometry can
redraw in combat; protected frames and native map/waypoint actions defer.
**Lines are on the world map only.** The minimap icon opens the addon.
Normal routes do not set extra Blizzard user-waypoint pins. The explicit **Map
NPC** button can set one for a branching-prerequisite confirmation only. Numbered
route markers and the owned navigation arrow remain; unrelated manual waypoints are
left alone. A pin left from an older release can be removed manually on the map.

Travel directions use the shortest-time point graph described below; local walk
segments still use estimates. Follow roads and terrain. Missing objective
locations stay explicitly partial instead of inventing targets or early turn-ins.

## Travel, NPCs and personal tools

**Show a standalone direction arrow** in **Settings → Arrow and map** enables a
small transparent arrow with its own saved position. Drag it separately from the
guide controls. Hide the large direction panel if desired; the standalone arrow
continues updating. Both arrows use the same navigation state and one poll.

**Use travel connections** in **Settings → Travel routing** is on by default.
Our own Dijkstra search chooses travel between quest steps using 256 Forever
border/gate/transport points and 1,620 directed geographic links adapted from
Mapzeroth with its source credit and MIT notice. No upstream engine/UI is included.
The fixed quest order is unchanged. Walking waypoint arrival advances directions,
not quest credit. Boats, zeppelins, tram and passages remain manual; boarding
directions remain until the destination is reached. Travel refreshes after zone
changes and significant detours; map lines break at transport rides. The current
travel path replaces the first map leg, while later markers remain guide previews.
These are estimated walks between points, not detailed collision-safe roads.
See [TRAVEL_DATA.md](TRAVEL_DATA.md) for source hashes, coverage and limitations,
and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the license notice.

The addon checks public **C_TaxiMap.GetTaxiNodesForMap** discovery flags on login,
zone changes and flight-path unlock events, for the current zone and its parent
maps. A public isUndiscovered=false recognizes an unlocked path; missing/private
flags remain unknown. Opposing-faction map nodes are filtered where faction data
is public. Unlock recognition and known locations persist for this character,
including in solo mode; they do not create flight connections by themselves.
Forever support for these optional fields must be checked on your beta build.

Open flight-master maps to confirm this character's reachable network. The reader
uses the global **GetTaxiMapID()** used by Blizzard's modern flight UI, with the
visible **FlightMapFrame:GetMapID()** as a guarded fallback. The old nonexistent
C_TaxiMap.GetTaxiMapID query could pass nil into GetAllTaxiNodes and fail silently.
The map read now requires a valid map ID and retries briefly for late data;
closing the flight map cancels pending retries. The TAXIMAP_OPENED argument is a
taxi-system selector, not a map ID, so it cannot substitute for the getter.

When public flight
states and positions exist, the guide compares walking with getting to a known
reachable flight, flying and walking from its destination. It includes a
boarding allowance. The travel graph can combine observed flight legs; direct
flight comparisons remain available when no connected graph path exists or with
the graph off. A connected Dijkstra path supplies the same decision to the arrow,
map and optional flight action. Walking to a flight master names the flight that
follows. Learning a flight immediately refreshes those directions and can change
the Orgrimmar gate chosen by the personal travel guide.
Flight times are estimates until that character has timed the route. While
flying, the panel counts down an estimated first trip or a previously measured
duration. If its duration is unknown or the estimate expires, elapsed time is shown.
Ground lines hide during an actual flight; only its known destination is marked.
Ground directions resume after landing. The exact airborne terrain path is unknown.

The probe reports **Flight paths**, **Flight unlock scan** and **Flight map read**:
known paths, those with locations, observed connections and the actual getter/read
result. An unlocked destination is not proof of a reachable flight from every
master. Explicit unreachable observations remove that source's stale connection
without forgetting an already-known unlock. Unknown reads preserve saved evidence.
The probe itself does not query a flight map or select a taxi. Missing APIs, public
positions or current-master data leave connections and flight actions unconfirmed.

Nearby flight-master advice appears in a small optional strip below the guide
controls or standalone arrow within **350 metres**, using the map's physical
scale. Up to **750 metres** qualifies when visiting it adds at most **200 metres**
of estimated walking to the current leg. Hostile settlement crossings are excluded;
these are distance estimates, not road/terrain guarantees. Known paths are
hidden. Confirmed undiscovered paths say **Get flight path**; unknown unlocks say
**Check flight path**. Faction ownership must be known; no quest step is replaced.
Hearthstone advice uses 49 sourced inn locations, including Zephras Isle, plus
inns observed in game. It appears near a friendly inn when upcoming work away
from the hub returns for at least two distinct quest turn-ins. Current home tips
are hidden when the bind location or a recorded manual binding identifies it.
Hover for the reason and location; × saves dismissal for this character.
Both advice types can be turned off separately under **Travel routing**. This
logic applies to every guide, while tips require known service geography.
No automatic hearthstone binding, flight unlock, forced detour or guide reorder.
Unknown reachability, missing positions, continent mismatches or unsupported
APIs keep travel manual. Published service coordinates need beta verification.
**Select the suggested flight** is off by default. If enabled, it requests a
currently reachable native slot only when you open the matching flight master,
outside combat. Its protected-action behavior needs testing on your beta build.

While a ghost, the arrow temporarily directs you to a public corpse position
and retains the guide. A recorded death position is labeled approximate;
unsupported corpse data gives an explicit status. Recovering your body resumes
the guide. No release or resurrection is automated.

NPC observations can correct missing pickup gates: a public complete gossip
or quest-greeting list records what that giver offers for your current quest/level context.
Absence blocks a pickup only after all known givers were checked. A single
quest-detail dialog confirms that quest without claiming the list is complete.
In fixed guides, a confirmed unavailable pickup or known unmet level/prerequisite
temporarily defers that quest's remaining stages while other available steps continue.
The compiled order stays intact. Ordinary progress and NPC events reconsider these
gates; a newly offered eligible quest returns at its original place in that order.
If every remaining pickup is blocked, the guide stays selected and explains why.
Missing data stays unknown; it is not an automatic skip. Already active quests
retain their objective/hand-in steps. Manual skips stay saved until explicitly reset.
Restart a guide after upgrading to compile improved handling of partial objective
locations: a missing location no longer counts as a distant travel destination.
The missing step still has no invented coordinates.
Progress, level or reputation changes invalidate relevant knowledge; visit
again to recheck. This cannot discover every hidden prerequisite in advance.
Every pickup uses known level, faction, class, race and prerequisite rules.
Known prerequisite history is checked before positive NPC evidence: accepting
the earlier quest, completing its objectives or skipping it does not count as
handing it in. An alternative prerequisite needs one confirmed completion;
unknown/restricted history stays unknown. Actual offers can confirm missing or
unverified published requirements but cannot bypass a known unfinished prerequisite.
Without an NPC observation, a candidate is based on published data and may still
have a hidden beta requirement. Visit the giver to confirm it.

`IsPushableQuest` reports shareability and is no longer queried for pickups.
`IsQuestCompletable()` describes the currently opened NPC progress/turn-in
dialog; it is used only for optional turn-in, with no quest-ID argument. Neither
function is an arbitrary-quest pickup check. The old beta pickup setting and
packets are removed; update every client to avoid using the old interpretation.

Each client sends its own history and actual NPC offers. Peer offers are tied
to fresh quest-log context, and an empty list does not mean every quest is
unavailable. Automatic sync batches quest/turn-in/party/level/zone updates for
two seconds, including solo guide refresh. Locked quests stay in the full guide;
in adaptive mode newly eligible nearby work can join the trip while its unfinished objective stays
first. Fixed guides advance through their existing steps. Accepted work remains. Scan guide also rechecks. Diagnostics show candidate,
blocked and unknown counts plus sample per-quest reasons and NPC offer evidence.

Quest research is enabled locally in **Settings → Quest data for testing**.
Each character retains the latest 300 observations across reloads: public NPC
offers (complete lists distinguished from individual dialogs), accepted quests,
turn-ins, build, level/class/race/faction/map and relevant completion-history
checks. Snapshots check at most 128 relevant IDs and mark history truncation.
Level and reputation-change events flag alternative explanations for unlocks;
no actual reputation standing or unobserved NPC offers are guessed.

Use `/wt research` or **Export quest data**, choose **Select all** and press
Ctrl+C. Save the JSON export as a text file and send it with your tester name
after a session; export before older observations roll off. Diagnostics shows
the retained/replaced count. Each friend exports their own character's data;
the export contains no character names, realms, chat or friends' histories.
Records are not sent through party sync or uploaded automatically. Manual guide
skips and observed automatic pickup deferrals/restorations are recorded separately
from NPC offers and quest hand-ins. Their guide key, exact step key/kind and fixed
step number accompany the existing addon/build/level/faction context. Invited route
keys omit player identities. Disable
recording to pause collection; previous observations remain exportable.
Reloads and recording toggles mark a new capture segment so gaps remain visible.
Visit the same giver before and after hand-in for the strongest comparisons.
A missing planned pickup is recorded only for this character at a known giver
with a complete public list. **Use observed prerequisite patterns** is on by default. One complete NPC list
showing a quest absent, followed by exactly one observed hand-in and a positive
offer, can create a tentative relationship. Relevant history must be public and
untruncated; no other newly accepted quest may intervene. Matching build and
faction can reuse ordinary findings on new characters on this account across
classes and races. A class/race restriction on the quest **or its prerequisite**
keeps that dimension specific to the observing character. The original class/race
in an export identifies the observer; classRestricted/raceRestricted show reuse
limits. Existing findings migrate without losing source evidence; contradictory
predecessors that merge across classes/races remain disabled for review. Changed level
makes the pattern review-only. Reputation notifications are noted as a possible
alternative cause, not treated as actual standing measurements. Multiple givers,
repeatables and professions do not become automatic learned gates. Published
alternative prerequisites are never narrowed to one observed branch. A positive
NPC offer contradicting a learned requirement disables that tentative rule.
Playing UI shows the quest action or blocking requirement without observer
labels. Optional findings exports retain provenance. An already running fixed
guide keeps its order; new guides use the current findings.
A missing offer or a skip alone does not identify the unlock. Visit the actual
NPC before and after a hand-in to obtain a useful learning pair.

The bundled **The Hunt Continues (750)** now requires **The Hunt Begins (747)**
to be handed in. This correction is labeled as a Forever beta tester report,
separate from published source facts. Both fixed and adaptive guides use it;
accepting, finishing objectives or skipping The Hunt Begins cannot unlock it.
Reviewed corrections are retained in tools/quest_corrections.json for subsequent
catalogue imports; conflicting published gates require review before importing.

Use **Export guide findings** or `/wt findings` to send retained account-wide
patterns with their before/after evidence plus the current character's latest
raw observations. **Include source names in guide findings** is optional and off
by default. Raw `/wt research` exports always omit names. Each friend exports
locally and sends a labeled file for review; findings never upload or sync
automatically and never overwrite the bundled catalogue themselves. Manual
review of overlapping/contradictory reports is how shared guide data improves.
Repeated manual skips can support a level-specific baseline review when independent
testers report the same guide/version/step/faction/level. They do not automatically
create shared skips or prerequisite rules. Confirmed missing offers are personal
progress evidence; ordinary learned unlock patterns can apply across matching
build/faction characters, with each character's own requirements checked.
Retest capture APIs/events on the beta.

The greeting reader probes GetNumAvailableQuests/GetAvailableQuestInfo and
reads the quest ID from the fifth return, as documented by Mainline's native
QuestFrame. Missing or restricted fields cannot prove that a quest is absent.
Retest these optional APIs on Forever; Sting of the Scorpid's exact unpublished
gate is not inferred from a neighboring quest ID.

Needed public nameplates show a star by default. Cross, skull and quest ! styles
remain selectable in Quest markers settings. A
finished mob objective loses its hint unless another unfinished objective or
participant still needs it. Known required-item tooltips get a cross and quest
name. Friendly givers can show quest names and a downward pointer. Hints hide
in combat and require public data; world objects without nameplates are not
universally marked. No raid-target icons or secure Blizzard controls are changed.

**Quest markers → Star above guide quest givers** adds a large gold star above
an eligible pickup giver's visible friendly nameplate, with quest names beneath.
Accepted/completed or known-blocked pickups do not qualify. The option defaults
on and respects the general NPC/nameplate toggles. Published patrol waypoints
for the next three pickup/hand-in givers appear as thin amber search paths on the
map. Turn these off with **Show quest-giver patrols on the map**. A patrol path is
a possible search area, not a live NPC location. Enable friendly nameplates in
the game's settings to see it; the addon does not change that setting. The star
is our cosmetic overlay and does not put a real raid-target mark on the NPC.

**Quest dialogs** contains separate opt-ins for opening useful selected-guide
pickups at a multi-quest NPC, accepting an eligible selected-guide pickup dialog,
and turning in completed
opened quests with no reward choice. All default off and defer in combat.
Reward choices remain manual. API presence or an attempted action is not proof
of success on the Forever beta.

**Dungeon quests** offers Start route for a personal collection guide across
zones, including required prerequisite work before the dungeon entrance.
**Quest list** shows compact clickable quest cards, pickup NPC/zone, level and
status, and All / To collect / In your log / Completed filters. Selecting a card
or Route to pickup starts a guide just for that quest and its prerequisites,
ending after acceptance. Start route covers the full suitable collection.
Entrance locations use previously saved corrections, public client map links
or the published Forever dungeon snapshot, in that order. Required missing
offers/locations wait for confirmation; they are not bypassed. Planning uses
known directed travel/flight costs, a prerequisite-aware visit order and bounded
local improvements. This is an efficient heuristic, not a proven global optimum
or a terrain navigation mesh. Ordinary progress reuses the prepared itinerary.
The popup uses your character's highest known minimum pickup level across all
relevant regular quests for that dungeon. Other factions/classes/races, repeatables
and profession quests do not raise it; matching class quests count when enabled.
Unknown level/identity data prevents an "all levels met" prompt. Prerequisites and
actual offers still need checking. The collection route uses your own progress
and works without received party snapshots. A prompt does not replace an active
guide until you choose its collection plan. An unmapped collection opens the full
quest list for review. Next-zone prompts still respect a selected quest-log trip.

**Profession guides** uses recipes from your own opened crafting window,
skill-based batches and material estimates. Public auction prices come
only from searches you make; there is no background AH search, buying or crafting.
Known vendor-listed quest items have a buy list with your own bag counts.
Profession, flight-network and skip data are personal and are not sent to peers.


The quest preview displays a quest-XP estimate from your
level when the route starts. Confirmed completions and skips are excluded.
Observed XP thresholds are saved for this build; remaining thresholds use a
labeled Classic baseline. Quest rewards can change in Forever. Kills, exploration,
rested XP and party effects are excluded; unknown rewards are reported. The
starting estimate is saved across reloads and does not reorder the guide.

Confirmed non-repeatable completion flags are remembered only for this
character/build. Temporary restricted or unavailable quest-log reads preserve
the last public snapshot. Accepting a quest again clears its remembered credit;
manual skips still grant no credit.

**The New Horde** currently needs an actual NPC offer before its pickup is
recommended. Exact race eligibility is under review; the addon does not infer
an exclusion for Orc/Troll or eligibility for another race from that report.

## Data and beta limits

The offline snapshot was captured **October 5, 2026** from public game facts in
[Warcraft DB](https://forever.warcraftdb.com/list/quests) and
[Wowhead Forever](https://www.wowhead.com/forever/quests).

| Coverage | Records |
| --- | ---: |
| Distinct quest records / category lists | 5,230 / 123 |
| Detailed Forever pages | 2,232 |
| Quests with static pickup / objective-area / turn-in coordinates | 4,276 / 2,150 / 4,444 |
| Series / quests with explicit prerequisite facts | 938 / 2,465 |
| Incomplete objective locations / known repeatables | 1,353 / 627 |

Mapped item-drop alternatives retain a single representative farming area near
this quest's published giver. This is a stable geometric choice, not a requirement
to visit every possible mob or proof of the best drop rate. Other source locations
are retained as alternatives. Missing objective flags still mean a real source gap.
For an active fixed-guide step with missing coordinates, your own public native
quest-tracker destination can supply its current location. A catalogue fallback
cannot fill that gap; unavailable/private native data keeps the existing notice.
The fixed step order and saved skips are retained when native coordinates change.
0.8.3 joins explicit NPC/object/item requirements and named drop/vendor relations.
Published Forever event, escort and healing types replace incorrect kill labels.
AND prerequisites require every parent hand-in; OR variants retain their alternatives.
Escorts stay beside their pickups. Community ground-item coordinates retain
source comment IDs and are used only when explicit, consistent and otherwise missing.
Provided quest items do not become farming steps or shopping requirements. Native
Warcraft DB quest-map points fill otherwise missing stages without copying tiles.
Instructions include quantities,
item-use actions and named targets. Two items from the same proven mob can share
its published farming area; step skips remain specific to each item.

Compile-time local search reduces estimated distance while preserving per-quest
stages, known hand-in prerequisites and useful NPC hand-off bundles. It never
reorders an already selected guide because of movement, acceptance or Scan.
This is a bounded heuristic, not a globally optimal XP/terrain solution.

Older-world numeric/name facts are used only when Forever labels the quest
unchanged and its ID, title, level and minimum level agree. Published Forever
and tester corrections take precedence; actual NPC offers can contradict an
explicitly marked older-world prerequisite. No old API/server logic is used.
Published Forever DBC bounds cover 46 outdoor/capital map views. Separate
empirical transforms require five broadly distributed published Forever NPC
anchors and strict residual checks; converted-baseline anchors cannot validate
themselves. Remaining world points can use native
C_Map conversion only after three published Forever anchors agree. Missing,
restricted or contradictory transforms leave the location unknown.

See [QUEST_DATA.md](QUEST_DATA.md), QuestCoverage.json and GuideAudit.json for
per-zone coverage, source pins, remaining gaps and host compilation checks.
These files deliberately distinguish location coverage from quest availability
and live beta validation. GuideSourceQueue.json names every remaining missing
quest/stage/quantity/pickup requirement. The audit's --require-complete check
fails while any guide has missing facts, even when its route invariants pass.
Some individual source pages still return access denials after the environment
rules were applied; those pages remain excluded.

This is a partial catalogue, not every Forever quest or a complete prerequisite
or flight graph. Detailed reads now spread across outdoor categories through
level 60, retaining cached pages. Published legacy facts may differ from the beta. List metadata
does not establish current availability. Live active destinations take precedence;
area-table IDs are mapped to UI map IDs only with unambiguous shared evidence.
Coordinates lacking that join are preserved separately, and can resolve at
runtime only against an unambiguous matching native zone name. Localized or
missing names can leave them unknown. The generic guide engine supports every
zone present in usable catalogue data; it does not imply complete coverage of
all current or future beta zones. Unknown locations do not hide the entire guide.
Ambiguous faction, branch, class and race requirements remain unknown until
live evidence establishes availability.

No third-party quest descriptions, game artwork or addon code are included.
The guide-card landscapes are original generated artwork, with source and
provenance supplied in the release.
[QuestTogether's public description](https://www.curseforge.com/wow/addons/questtogether)
provided broad inspiration about progress clarity; its code/assets/layouts
were not copied. This implementation is independent.

Reported beta build **70205** established the earlier sync APIs in user tests.
**0.8.13 has host validation, not a live-client compatibility certification.**
Retest UI rendering, optional gossip/flight actions, corpse positions and item
hooks on the build in front of you. `/wt probe` lists capabilities and runtime
status. Do not interpret presence as proof that protected actions work.
SavedVariables initialize in ADDON_LOADED; beta persistence failures may belong
to the client. No combat-log processing, secret arithmetic, secure snippets,
combat automation or replacement of Blizzard combat tools is used.

## In-game Lua checks

Open **/wt lua**, paste a short check, click **Run**, then **Select output** and
Ctrl+C. `return` preserves multiple results, including nil/false; `print` writes
to this output pane. Nested tables expand automatically. Syntax errors and failed
`assert` checks are shown there. Results never go to chat or party messages.

The console exposes a read-only subset of quest, gossip, map, taxi, item/spell and
character APIs. `apiType("C_API.Method")` checks actual client presence even for
APIs outside that callable subset. For example:

```lua
return GetBuildInfo()
```

```lua
local quests = C_GossipInfo.GetAvailableQuests()
assert(type(quests) == "table", "No quest list returned")
return quests
```

```lua
return apiType("C_QuestLog.IsPushableQuest"), apiType("loadstring")
```

Run NPC-list checks while its window is open. The console requires public
`loadstring` and `setfenv` capabilities on this build; missing compilation is
reported, with both listed in Diagnostics. Run checks outside combat. Straight-line
snippets support locals/conditionals/assert/print/return; loops and function
definitions are excluded. Table/output limits and cycle detection keep results
readable; secret values appear as `<restricted>` before formatting.
Action APIs, frames, addon state and additional code loaders aren't exposed.
This is for small in-game API tests; the Python host suite runs outside the game.

## Development and release

0.6.9 reduces repeated history reads, party-list rebuilding, unrelated learned-rule
scans, route-planning allocations and repeated coordinate conversions. Reuse stays
within a synchronous read/draw pass; the next update queries fresh data, and the
compiler discards temporary caches when it yields. Guide decisions, prerequisite
rules, fixed/adaptive order, sync behavior, settings and UI remain the same.
See PERFORMANCE.md for measured host results and the repeatable benchmark command.

Host checks load all 49 Lua files in TOC order under Lua 5.1 through `lupa==2.8`:

```sh
python3 -m venv /tmp/wow-together-tests
/tmp/wow-together-tests/bin/python -m pip install lupa==2.8
/tmp/wow-together-tests/bin/python -m unittest discover -s tests -q
```

Mocks cover sync, secrets, snapshots, planner/chain policy, stable routes,
map geometry, party completion, UI controls, skips/scans, observed flights,
corpse directions and guarded actions. Synthetic fixtures are not shipped.
Run the actual-client checklist in `TESTING.md` and label your report as the
main developer or a named friend. Compare all reports before implementing;
resolve contradictory suggestions with the user first, as required by AGENTS.md.

Regenerate accessible source facts outside the game:

```sh
python3 tools/import_warcraftdb.py --refresh
python3 tools/import_wowhead.py --all-categories --world-details --detail-level-max 60 --spread-details --new-detail-limit 120
```

Importers use paced reads and `/tmp` caches without executing site JavaScript.
Repeated detail denials stop new detail requests; `--cached-details` processes
accessible cached facts. No requests run in the addon. `QuestCatalogue.json`
records coverage and `ZoneConnections.lua` keeps known map connections.

Build with `python3 tools/build_release.py`. Each completed addon release is
also posted with its matching changelog and test script:

```sh
python3 tools/build_release.py --post-discord
```

Store `DISCORD_WEBHOOK_URL` securely in environment settings. For an existing
ZIP, use `python3 tools/post_discord_release.py <archive> --prompt` for hidden
input, or `--dry-run` to preview without sending. The uploader extracts both
documents from the ZIP, disables mention pings, confirms all three attachments
and saves a nonsecret receipt. Identical contents are not reposted; changed
contents require a new version. Check channel history before retrying an
ambiguous delivery. Credentials never belong in addon files or archives.
