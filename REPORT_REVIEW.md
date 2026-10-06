# Follow-up review for 0.8.19

Mikmans asks to make the current guide quest active in Blizzard's quest log for
native map highlights. The accompanying report says Our Ancient Enemy and The
High Chieftain are repeatedly recommended without NPC offers. The supplied
probe belongs to Pachu Bloodwind; its author is not explicitly labeled as the
main developer. It records 0.8.16, client 1.60.1/build 70235/interface 16001,
level 8 Horde Tauren warrior, solo, with the Mulgore fixed guide plus current
quests, auto-accept/turn-in on, full preview and standalone arrow. There are
10 deferred pickups and one manual skip. Keep this separate from older travel
feedback and do not infer a new party-sync problem.

Both supplied exports are truncated pasted copies: their final markers say
29 KB left and 23 KB left. Recover only 94 complete, identical event objects,
deduplicated once; the probe says 127 observations, so later evidence is absent.
Headers say 0.8.16; events span older addon versions/build 70205 and a final
partial session on build 70235. Complete offers at NPC 3222 omit quest 99101
(sequence 63), followed by its automatic deferral (64). Quest 99082 is deferred
(69); complete Baine Bloodhoof/2993 offers contain 745/746 rather than 99082.
Neither named quest has a positive offer in the recovered events. This proves
missing-offer observations, not an exact unlock/prerequisite or a new race gate.
Acceptance snapshots can briefly omit newly accepted quests before log reads
catch up; do not learn false unlocks or completion from that timing.

Inspection confirms that InvalidateNPCOffers deletes all giver observations on
turn-ins/reputation events, while the context changes on active quests/level.
With no published parent, these new Forever quests become eligible again.
Retain complete negative snapshots separately, scoped to character/build, while
fresh positive availability still expires. A new real full/partial offer restores
its own quest; partial lists do not establish other absences. All alternative
starters must be checked before declaring absence, and active work bypasses the
pickup deferral. Keep fixed order and manual skips. Add reviewed offer-required
flags for the two reported quests, without inventing gates from neighboring IDs.

Use capability-probed native quest selection/tracking for the accepted current
guide quest, independent of arrow visibility. Match the native quest-log details
helper when exposed, without opening the map/log. Do not add a user waypoint,
reselect on movement ticks, select an unaccepted/peer-only quest or act in combat.
The shared regen handler rechecks the latest target. An opt-out is under Arrow
and map. Published Mainline API/UI references establish names/signatures only:
https://raw.githubusercontent.com/Gethe/wow-ui-source/live/Interface/AddOns/Blizzard_APIDocumentationGenerated/QuestLogDocumentation.lua
https://raw.githubusercontent.com/Gethe/wow-ui-source/live/Interface/AddOns/Blizzard_UIPanels_Game/Mainline/QuestMapFrame.lua
Native beta behavior still requires the included testing checklist. No conflicts
with the user's fixed guide, clean UI or removed automatic user-pin preferences.

## Additional report received during 0.8.19 verification

The user adds an unlabeled Dutch report: Darn Talongrip has no Report to Kadrak
quest, followed by the correction that the character already had that quest.
Treat this as an accepted/alternative-ID symptom, not proof of a missing Mulgore
prerequisite or a new learned gate. Its export header says 0.8.17, but the
recoverable 77 events are 0.8.12–0.8.14, build 70235, Horde Undead priest levels
21–22 in Stonetalon/Barrens. It ends at a 50 KB left marker. No recovered event
records Darn/11821, active/completed/offered 6541 or 6542. Preserve the user's
correction as reported evidence; the capture cannot establish the live quest ID.

Source inspection independently confirms explicit reciprocal exclusiveTo lists
for 6541 (Thork) and 6542 (Darn), both Report to Kadrak, in the existing pinned
QuestieDB Forever factual table. Source SHA-256 and commit are retained in the
reviewed corrections; titles, levels, starters and turn-ins match the shipped
unchanged records. The pinned generated/beta-review/trace quest deltas do not
change this pair. We read literal facts only; no provider/other-addon code runs.

Add a generic explicit-alternative check used by pickup eligibility and fixed
guide applicability/completion counts, with this reviewed pair in the generator
and catalogue. Do not merge by title, change parent chains or bulk import other
unreviewed baseline exclusions. An accepted version continues real work; its
alternative is inapplicable for that player, without completion/skip credit.
Peers use their own fresh state. If both IDs are genuinely accepted in a changed
beta, neither real quest is discarded. Exact beta handling remains a checklist
item. This complements persistent NPC rechecks without changing fixed order.

## Manual quest-item request received during verification

The user explicitly requests `UseQuestLogSpecialItem(questLogIndex)` for quest
items. Published Blizzard UI definitions show an ordinary objective-item button
calling that API from its click handler. API presence on Forever still needs a
capability check and hardware-click test; the host cannot establish native action
permission or effects. Reference signatures/usage only, not other-addon code:
https://raw.githubusercontent.com/Gethe/wow-ui-source/live/Interface/AddOns/Blizzard_ObjectiveTracker/Blizzard_ObjectiveTrackerShared.lua
https://raw.githubusercontent.com/Gethe/wow-ui-source/live/Interface/AddOns/Blizzard_ObjectiveTracker/Blizzard_ObjectiveTrackerShared.xml

Add an owned compact item button for accepted current objective steps. Read
special item metadata on progress/bag/item-data refresh, never movement ticks.
Verify the public log entry and resolve its index again on the user's click;
headers, removals, other quests, stale previews and changed item links cannot
use a stale index. Missing/restricted APIs/data hide the button. Use is outside
combat for this beta, never automatic, queued or targeted by the addon. Document
the limitation, probe capabilities and include native testing instructions.
No change to pickup eligibility, fixed order or objective completion inference.

# Follow-up review for 0.7.5

The user asks why The Battleboars location could not be found and requests that
it work in the addon. This is a main user follow-up question without a new version,
character or probe capture; it is not another friend's flight report. No conflict
with fixed ordering, source validation or the leveling focus.

Inspecting cached quest-780.html proves that the mapper has Mulgore (area 215,
joined to UI map 1412) points at Battleboar 57.6/85.2 and Bristleback Battleboar
63.4/78.2, both for Battleboar Flank. The mapper also flags one missing objective.
Our importer discarded any item group with multiple source entities. That was a
confirmed parsing policy error; the previous answer saying coordinates were absent
was incomplete. Keep mapped alternatives, choose a deterministic representative
near the published quest giver and leave real missing flags intact. Do not infer
that the known Flank sources also prove Snout drops. Reprocess existing cache only.

Add an active fixed-step location bridge using our own guarded public quest-log
reads. Native coordinates decorate a copy of the placeholder; they do not mutate
its saved fixed order. Catalogue fallbacks cannot fill the missing stage, and peer
packets do not carry sufficient provenance for this bridge. Maintain the placeholder's
stable skip key across position changes. Completion remains objective/history-driven.

Coverage changes from 196 to 319 quests with mapped objective areas; incomplete
location flags fall from 950 to 840. All 5,230 quest identities and non-location
fields compare unchanged against 0.7.4, including level/prerequisite/faction data.
Synthetic checks exercise alternatives, map-ID joins, native/private/unavailable
positions, skips and hand-ins. Native beta waypoint behavior and source locations
still need live verification.

# Follow-up review for 0.7.4

The user reports successful automatic flight to Orgrimmar while Dijkstra still
suggested walking, and asks for a calculating loop on Scan guide. No character,
version, build, selected goal, settings or exact direction text is supplied for
this observation; its live cause remains unconfirmed. This is one unlabeled
report, not a new capture from the earlier level-23 friend. No preference conflicts.

Inspection confirms that flight-map reads reset the travel graph and update the
arrow but do not immediately repaint map geometry. The personal city guide can
retain a gate chosen before learning a faster flight. A terminal graph walking
leg returns no intermediate waypoint, allowing a separate legacy flight solver
to replace its decision. Directions can also call a walking approach leg a generic
crossing without explaining the flight next. Ground quest lines remain drawn
while actually on a taxi. Fix these shared paths, not a specific flight or quest.

Recompute the personal city's gate before refreshing navigation/actions; repaint
owned geometry with the existing combat guard. A connected graph path is authoritative
for flight choice; the fallback remains available without a path or with graph off.
Describe walking to the flight master and the upcoming flight. During actual
UnitOnTaxi state hide ground lines; restore them on landing. Flight ownership and
native reachable slots still gate automatic travel. Times and walk links are estimates.

User scans yield to the UI before work and between bounded history batches. Both
owned arrow displays use the existing update cadence to animate a loop. Internal
history reads remain synchronous; fixed guide order stays fixed. Cancel pending
scans on guide changes/clear, preserve skip settings and restore geometry after
success/failure. Diagnostics retain failures; no extra popup or UI provenance text.
Synthetic host tests verify state/action agreement and cancellation, not native
beta behavior. The synthetic flight fixture now has isolated geography: its node
IDs collided with unrelated real published locations, previously masked by the
legacy fallback. Keep the published city-gate guard and test it separately.

# Follow-up review for 0.7.3

The user asks for immediate map updates after Skip quest and a close level band
across every leveling guide. Their friend (unnamed) was directed to pick up
Centaur Bracers at level 23; it was NOT accepted. The user's separate observation
also reports it appearing, without supplying their level/version/party/route state.
No probe was available because the friend had left. Do not attribute the previous
Elianus report to this friend or claim a proven cause for this specific run.
The accepted-quest bypass initially suggested does not explain that new pickup.
The user explicitly chose to apply the level filter to unfinished current quests
too, superseding the older Include current quests exception. They also request
a simple Path to Orgrimmar travel guide for levels 1–60. These requests agree with
fixed ordering, useful prerequisite exceptions and optional party invitations.

Inspection finds three real gaps: SkipGuide relies on dashboard rendering, which
is delayed during resizing; fixed/adaptive bundled work admits any accepted quest;
and retained normal/circuit route construction does not reapply LevelingValue.
Those gaps do not establish which path the absent friend's client used. The
shipped Bracers record is level 14 with no known useful follower and is rejected
by the normal level-23 policy. Test both unaccepted and accepted variants through
all leveling route modes; use general gates, not a quest-specific blacklist.
Apply a three-level lower/upper band, preserve ready hand-ins per character and
known useful/class exceptions, and exclude unsynced stale levels from the floor.
Expose that floor in diagnostics for the next real capture. Catalogue levels/
base XP are known metadata, not proof of Forever's exact XP reduction formula.

Make explicit skip actions update route state, cached travel target, navigation
and owned geometry directly; protected actions retain their combat checks.
Fixed sequence and saved skips remain separate from completion/prerequisites.
The city journey uses original search and the existing licensed geographic data,
compares both published gates, saves a personal descriptor with no fake quests,
and completes on city entry. Missing connections retain explanatory controls.
It is fastest in the known weighted graph, not a terrain/time guarantee. Host
checks cover logic; native beta map/flight/arrival behavior still needs retesting.

# Follow-up review for 0.7.2

The user reports that unlocked flight paths are not recognized. Their supplied
capture is Elianus Bronchilius, addon 0.7.0, build 70205, level-23 Horde Warrior/
Orc, solo in the Barrens, with a fixed Barrens guide and automation disabled.
It is not explicitly labeled as the main developer's own character report.
GetAllTaxiNodes is present, C_TaxiMap.GetTaxiMapID is missing, and Travel says
flight APIs/state enums are unavailable. There is no new contradictory request
or second flight report. This is consistent with the earlier captures' missing
namespaced getter; 0.7.1 still contains that query.

Blizzard's current UI source uses the global GetTaxiMapID(); API documentation
requires a non-nil uiMapID for GetAllTaxiNodes. The old reader can silently fail
by passing nil, and the old host fixture accepted any arguments, masking this.
Use the guarded global getter, then the visible native frame if necessary.
Do not mistake TAXIMAP_OPENED's taxi-system payload for a map or invent one from
the player's zone. Bound late-data retries and cancel them when the map closes.
The corrected fixture requires the exact map ID and tests native slot selection.

Documented GetTaxiNodesForMap returns MapTaxiNodeInfo with isUndiscovered and
faction metadata. Capability-probe the API and inspect public flags for the
current zone/parents on login, zone and unlock events. Unknown/private flags do
not infer unlocks; source reachability is distinct from ownership. Save evidence
per character and keep it out of party sync. Only current-master Reachable states
create graph connections. Explicit Unreachable states remove that source's
stale connection while retaining prior unlock evidence. Diagnostics distinguish
getter/API failure, known paths, missing positions and observed connections.
These are read-only data/API references, not copied addon code. Actual Forever
getter/flag behavior still requires a beta capture after updating.

Sources inspected (2026-10-05):
- https://github.com/Gethe/wow-ui-source/blob/live/Interface/AddOns/Blizzard_FlightMap/Blizzard_FlightMap.lua
- https://github.com/Gethe/wow-ui-source/blob/live/Interface/AddOns/Blizzard_APIDocumentationGenerated/TaxiMapDocumentation.lua

# Follow-up review for 0.7.1

The user requests cosmetic stars above quest pickup givers and a complete solo
leveling mode that disables party features. A quoted, unlabeled report identifies
Welcome! as a Collector's Edition reward; it is not attributed to a named tester.
Follow-up user requests replace leveling-card Show route with an ordered quest
list and show actual leveling areas for brackets. Their screenshot is a level-12
character in Durotar with 21–30 selected, recommending Mulgore, Orgrimmar and
Silverpine. The screenshot alone does not establish class/build/active quests.
The latest user report also names Carry Your Weight being recommended at level
12; whether it was active or a new pickup was not supplied. No friend diagnostic
is attached to this batch. These requests are compatible; fixed order and optional
party-follow acceptance remain in effect.

Inspection: solo guides already work but shared state/transport/UI need a master
gate. Clear queued transport and peer state on toggles; stale callbacks cannot
send into a new party session. Personal events/research continue. Stars use owned
overlays on visible friendly nameplates, never real raid marks or secure attributes.
All seven Welcome! catalogue variants receive a reviewed leveling exclusion,
retained through regeneration; raw catalogue records remain browsable.

Bracket qualification previously could rely on lower-level work after discovering
a later outlier. Match qualifying work to both bracket and actual level. Known
remote-only objectives do not qualify their pickup zone; exclude capital hubs,
and derive a main level band from the catalogue to avoid sparse handoff outliers.
Unknown objective geography still uses the published zone category. This is a
data-informed estimate, not complete terrain/zone knowledge. Preview all ordered
stages in a virtualized scroll window without changing the selected route.

Carry Your Weight (791) is level 7 with no known follow-up in the shipped data.
At level 12 the old five-level allowance admitted it, and fixed-guide advancement
bypassed LevelingValue entirely. Tighten the preferred band and apply eligibility
to fixed steps without completion/skip credit or reordering. Preserve useful
chains/class progression, ready hand-ins and explicitly included current quests.
Fixed guides now honor the previously requested Start selected guide / Include
current quests popup as adaptive guides do. Test both choices, fresh scans and
context changes. Host fixtures cannot establish native beta star/UI behavior.

# Follow-up review for 0.7.0

King Kai requests an optional standalone next-step arrow (18:07). The user
requests Dijkstra routing over travel points/transport links and stresses that
we must not steal code. These requests agree with fixed quest ordering: change
travel between quest steps, not the compiled guide sequence. Our search/arrow
code is original. A pinned Mapzeroth Forever 0.6.0 geographic snapshot is adapted
with source hashes and the project's MIT notice. It is a point graph with
estimated walking costs, not a terrain navigation mesh. Exclude Retail data,
ability/race portals and unconfirmed flight links. Add flights only from this
character's public reachable observations. No new transport automation.

The user's own follow-up captures 0.6.9/build 70205: Barry Batsman, level 12,
Horde Mage/Troll, solo in Durotar. They report switching from Mulgore back to
Durotar failing; the captured selection is Orgrimmar with an <UNUSED> step.
Diagnostics identify Planner.lua:340, arithmetic on nil x, during generation.
This is separate from King's UI request. An unmapped turn-in used as the first
operand in follow-up distance checks explains the crash. Handle both operands'
missing geometry; reject malformed/restricted coordinates at distance helpers.
Retired placeholders are not playable leveling content. Exclude them across
automatic guides, including old retained plans. Keep genuine missing-location
steps explicit; do not invent positions. Test with synthetic parent/child gaps
and repeated shipped-catalogue Mulgore/Durotar switches at level 12.

Friend report: Gladiator Eliaapje, 0.6.9/build 70205, solo level-5 Horde Warrior/
Orc in Durotar. Seven active quests, ten completed history flags and no selected
route. The failure is the identical Planner.lua:340 arithmetic on nil x. The
overlap is a compiler error, with different consequences: first-start failure
for the friend versus retaining a previous guide after a failed switch for the
main developer. Fixed compilation is independent of current location/logs; cover
both level/class fixtures. Friend auto-accept/turn-in are off; the main report has
them on. No evidence connects those settings to this read-only compiler error.

No conflicting preferences in this batch. Host tests cover shortest time paths,
one-way/faction links, restricted positions, character flight access, city-gate
isolation, detours/zone changes, boarding, line gaps, standalone polling/position
and guide switching. Live Forever geometry, transport endpoints and frame
rendering remain unverified here. Source limitations are in TRAVEL_DATA.md.

# Follow-up review for 0.6.9

The user requests a broad optimization/speed pass and explicitly asks to preserve
fundamentals and working behavior. No new gameplay report, build or preference
conflict accompanies this request. Profile first; avoid changes to level policy,
chain gates, route priorities/order, UI/settings and message protocol/timing.

The 5,230-record host fixture showed repeated completion/history reads, party-list
allocation, guide records constructed for irrelevant brackets, learned-rule/build
queries with no matching rule, compiler scale reads and coincident map projections.
Reuse read-only results within synchronous passes and reset compiler caches at
cooperative yields; retain fresh reads on the next update. Index learned followers
with the existing saved-data revision, retaining contradictory-rule safeguards.
Skip empty flight-network comparisons because they cannot yield a flight plan.

Baseline guide lists, fixed step sequence and map geometry fingerprints agree
after optimization. Pre-optimization synthetic fixtures cover fixed ordering,
alternative prerequisites, missing locations/external parents and adaptive cost
ties. Added tests cover unknown/private history freshness, abandonment, level-up,
rule revisions/contradictions, redraw privacy and compiler yields. PERFORMANCE.md
separates host call-count/time improvements from unmeasured beta FPS.

# Follow-up review for 0.6.8

The user's own character is level 12 and sees Ashenvale suggested despite a
level-20 requirement. They identify it as an example and request the same actual
level rule across all zones. No exact addon version/build, class or route capture
accompanies this report. Their second request is a live-position starting line,
including travel to a new zone. These requests agree with the chosen fixed-order
guides: drawing can move without replanning the guide.

Inspection established that browser discovery only tested membership in the
ten-level bracket, while the renderer only connected points with the viewed map's
ID. Filter zones with useful actual-level work and known pickup/prerequisite
levels, without hiding unfinished eligible parent chains. A shipped-catalogue
host fixture excludes Ashenvale for level-12 Horde and includes it at level 20;
generic fixtures cover other zones, alternative parents and selected-order stability.

Cross-zone rendering uses guarded public world-coordinate projection and clipped
viewport geometry; raw coordinates never transfer between different zone maps.
The live origin and navigation direction update without changing the guide.
Missing/private positions, degenerate mapping and different continents leave gaps;
they do not create an invented transport/road connection. Synthetic host maps test
border/continent projection and movement. Native projection behavior, map layout
and real walking paths still require beta testing; lines remain straight directions.

# Follow-up review for 0.6.6

After the 0.6.6 release, the user asked what Questline / Alternative meant and
preferred recommended zones plus alternative zone guides. 0.6.7 removes the
duplicate chain cards from Leveling guides while retaining chains in planning,
saved selections and invitations. This is a browser simplification, not a
change to fixed ordering or prerequisite gates.

This batch combines an unlabeled request for current-zone party catch-up and
prerequisite-aware bundling with King Kai's report (17:08): distant nameplate
crosses and losing the selected guide after reload. No version/build/character
context was supplied for King Kai, so the earlier solo Mulgore diagnostic below
is not treated as proof of his party or marker state.

The user resolved the preference conflict with fixed guides: offer **Catch up
party**, preserve the current guide until accepted, and keep friends' Follow /
Keep choice. The route checks fresh active/completion/history snapshots rather
than inferring progression from unknown history. Known prerequisite closure and
nearby hand-in/unlock bundling are generic across catalogue zone guides.

Three later user requests concern playing UI: remove observer attribution, keep
the navigation arrow and guide controls visible during unrelated questing, and
move the world-map controls below the viewport. The user confirmed the window
means navigation, not the party tracker. This overrides the older preference
for observer labels in steps; optional export provenance remains intact.

Inspection established that no selected-guide checkpoint was saved, nameplate
markers used the root plate anchor, and automatic completion called ClearRoute.
The implementation saves a primitive per-character guide descriptor/fixed plan,
restores fresh progress without invitations or opening the map, uses a public
name/health-bar anchor for smaller markers, and retains completed/waiting guide
controls until explicit clearing. Nameplate hints have a separate toggle and a
Quest ! style, preserving existing marker choices and item tooltip settings.

Host regressions cover these state transitions, catch-up consent/known history,
cross-zone behavior, prerequisite alternatives and bounded history requests.
Actual beta nameplate/map-footer layout and SavedVariables persistence still
need live testing. Known prerequisite facts and straight visiting-order lines
remain partial; this release does not provide terrain-aware walking paths.

# Follow-up review for 0.6.5

The user reports that The Hunt Continues unlocked at its NPC but did not return
to their guide, and explicitly confirms they did not press Skip. The supplied
Mike Codemen diagnostic is 0.6.4/build70205, solo, level2 Horde Hunter/Tauren in
Mulgore. It confirms quest750 is offered and allowed, selected full Mulgore guide
has60quests/223steps and176 missing-location steps. It does not identify the
current arrow's quest. Do not relabel this capture as a friend's report.

Reproducing the full compiled sequence shows 750 retained at step34. A missing
747 objective gets an arbitrary distant cost, pushing its hand-in and follow-up
behind unrelated travel. Fix the compiler generically using a published same-quest
place for ordering only; missing steps keep no fake coordinates. Existing fixed
order stays stable; restarting compiles the corrected order. No new example-only
quest gate is needed in this release.

The user then clarifies that confirmed unavailable pickups should automatically
defer and return, with data saved for learning. Preserve fixed sequence but allow
its progress pass to bypass known temporarily blocked quests and reconsider them
on progress/NPC events. Keep manual skips separate. Missing-data uncertainty is
not negative proof. Record observed deferral/restoration alongside actual offers;
reuse only clean learned unlock requirements for other matching-build/faction
characters, using their own progress, not shared permanent skips. Research retains
300 observations per character; learned patterns are separately stored. Exports
are manual, never automatically delivered to the developer.

Overlapping priorities: focus personal leveling now, prompt for dungeons at the
highest known pickup level across the character's relevant regular collection,
and record exact guide/step/version/level for reviewing independent tester skips.
Unknown levels/identity prevent a full-collection-level claim; prerequisite checks
still apply. Party sync need not block a personal collection. Repeated skips do
not automatically alter a shared baseline; compare labeled exports first.

Mapzeroth's public MIT source uses Dijkstra with a travel graph/transport nodes,
and coordinate-distance walking costs. It targets Mainline interface120100 and
modern maps. It cannot be dropped into Forever16001 or assumed mountain-safe.
No third-party code was imported. Verified Forever roads/terrain remain needed;
this update does not claim to resolve walking through mountains.

# Follow-up review for 0.6.4

The user reports a fresh Tauren in Mulgore being asked to pick up The Hunt
Continues while The Hunt Begins is still active, then seeing the same problem
on another Tauren. Exact addon version, class and build were not supplied.
The user clarifies that ordinary findings should apply by faction across classes
and races, retaining those dimensions only for restricted quests. This supersedes
0.6.3's blanket class/race scope. Code inspection confirms quest 750 lacks the
reported 747 prerequisite in the imported facts. Add that explicit tester-reported
data correction with provenance, using the generic prerequisite gate/planner.

Skipping alone is a saved local choice, not evidence of an unlock. Record skips
as distinct research events and explain this in controls/diagnostics. Preserve
the full-NPC-list/one-hand-in/new-offer evidence requirement. Account-local learning
remains local, uses each character's own history, and never rewrites running fixed
order or silently narrows published alternative branches. Migrate old ordinary
findings across classes/races; merge sources, flag conflicting predecessors for
review, retain class/race scope when either quest is restricted. Host checks cannot
verify the user's actual NPC offer list; include a live Mulgore test.

The previous Zephras/objective task was explicitly stopped by the user; do not
resume it as part of this correction. No additional friend's report was supplied
for this batch. The request to explain learning was followed by these concrete
scope/data corrections, and the user asks whether the general learner covers
other quests too. Apply the broader scope generally rather than only to Mulgore.

# Follow-up review for 0.6.3

The user supplied an anonymous 0.6.2 JSON export from build 70205/interface16001,
level2 Horde Shaman/Orc in Durotar. It contains reputation notifications and one
partial Zureetha list offering Vile Familiars. completeList=false proves no
absence of Medallion, and there is no before/after turn-in pair. It does not
justify inventing Cutting Teeth → Scorpid or any new prerequisite from that payload.

The user chose one clear observation as sufficient for tentative account-local
learning, with source-character attribution on affected steps. Everyone needs a
manual findings export so joint review can improve bundled leveling guide data.
Keep raw exports anonymous, make finding attribution optional, and never treat
one local pattern as permission to rewrite published branching requirements.

The next requests overlap: full-route counts did not match the bounded trip,
other zones had thin coordinate coverage, and abandoning/scanning/moving reshuffled
the guide. The user explicitly selected currently eligible quests for full map
preview and then requested generic fixed zone routes with automatic progress.
This supersedes automatic route reordering for default zone guides, not automatic
completion checks or party sync. Keep adaptive trips available as an explicit
setting; compile fixed order independently of position, active quests and history.
Scanning checks progress in that existing order. Completed steps can advance,
but unavailable/missing-location steps must remain explicit rather than fabricated.

Refresh accessible source detail pages across zones, distinguish metadata from
pickup/objective/turn-in coverage, preserve denied-request limits. Add native
questline inspection for the user's C_QuestLine question. Mainline documentation
establishes the table shape and optional membership query, not Forever coverage
or an arbitrary-ID pickup contract. Empty tables cannot prove negative availability;
questline membership does not prove prerequisite order. No other tester reports
were added to this batch or silently attributed to the main developer.

# Report review for 0.6.0

## Follow-up correction for 0.6.2

The supplied Tt Tte capture reports 0.6.1, client 70205/interface 16001, solo at
capture, level 2 Horde Shaman in Durotar. Do not relabel it as the earlier
user-labeled main developer's report or infer a current party from old peer
traffic. The namespaced sharing API is present; the global is missing. The
aggregate 140 true/147 false results do not prove any individual pickup's state.
Medallion (794) is absent from the captured trip; Vile Familiars (792) is present.
That does not disprove an earlier recommendation or a future guide entry.

Code inspection reproduces a shared cause: a positive native result, and some
actual-offer route paths, bypass known prerequisite history. The user authorized
a generic fix for all quests and then corrected the API interpretation:
IsPushableQuest describes sharing; IsQuestCompletable describes completion of
the currently opened dialog. Mainline QuestFrame uses the latter with no argument
to enable the progress panel's Complete button. No arbitrary-ID pickup contract
is established. This correction supersedes the 0.6.1 beta-gate assumption below.

Apply one prerequisite/identity/level rule before every new pickup. Actual NPC
offers can fill missing published evidence but cannot bypass a known unfinished
prerequisite. Keep locked future quests in full guides; normal progress rechecks
them. Remove the incorrect gate, setting and packet stream, retain optional
opened-dialog turn-in, and add per-character diagnostic reasons. Host tests
cover all route modes, secret/unknown history, alternative prerequisites, NPC
offers, party independence and stale markers. Unknown hidden gates still need
NPC evidence on the beta build; no fixed example-only prerequisite is invented.

During implementation the user also requested data collected during their and
friends' leveling sessions, mainly to improve prerequisite evidence. Capture
bounded per-character public NPC offers and acceptance/hand-in events with
relevant history and build/level/reputation-change context. Export locally via
settings or /wt research, with no names/chat/automatic transmission. Identify
missing planned pickups only against a complete list at a known giver and only
for that character. Preserve evidence rather than silently learning a dependency;
before/after differences can have other causes. A partial detail dialog must
not erase an earlier complete list's absence evidence in unchanged context.

## Follow-up batch for 0.6.1

The user reports missing non-Barrens guides, single-quest tiles, blocked Start
route, slow/weak optimization and differing Durotar stop counts. A friend in
Ashenvale sees a guide but cannot start it; another friend is asked to pick up
an unavailable scorpion quest. Names, exact builds, levels and selected guides
were not supplied for this batch; do not infer them from the older captures.

Overlap: guide discovery depended on mapped points and a local catalogue scope;
the map action depended on native waypoint acceptance. The old guide list also
mixed single-NPC recommendations with actual plans. Quest greeting lists were
not read, so an NPC's missing offer could be missed. Eighteen versus three stops
alone does not establish a shared cause: compare selected scope, progress and
source locations, since each quest supplies several stages.

Resolved preferences: remove only the extra Blizzard waypoint, keep numbered
route markers; remove the Scan footer; apply guide generation to all catalogue
zones. The user further requests full guides with known cross-zone chains and
optional next-zone guide switching driven by levels/progress. This complements
the existing Follow route / Keep my route choice and useful-chain catch-up policy.

Implementation uses catalogue-wide zone/chain plans, bracket/search pagination,
retained full scope, cooperative bounded trips, explicit guide identity in
invitations and optional next-zone prompts. The NPC greeting reader follows
Mainline's native public format but must be retested on Forever. No unpublished
Cutting Teeth-to-scorpion dependency is asserted without evidence. Source data
remains partial; unknown locations or offers are explicit rather than fabricated.
The 0.6.1 checklist covers each player's own NPC offers and full guide/trip counts.

The user then explicitly asked to use IsPushableQuest as a pickup gate and said
they had tested the true/false interpretation. This is their beta evidence and
authorization, not a verified universal Mainline contract. The user also asks
for automatic refresh when a quest such as the scorpion follow-up unlocks.
Implement an enabled-by-default compatibility setting, own-character read-only
queries, guarded public booleans, revision-matched peer snapshots and event
invalidation. Public true confirms a candidate; false blocks new pickups;
restricted/nil/error results remain unknown. Missing/disabled APIs use the
existing offer/history gates. Preserve accepted quests and the current unfinished
objective, and add newly unlocked nearby pickups without discarding the trip.
No fixed scorpion prerequisite is needed for this native check. The older
IsPushableQuest caution below describes 0.6.0 and is superseded for this tested
beta compatibility option by the user's explicit latest instruction.

## Evidence and labels

| Source | Captured character/context | Observations |
| --- | --- | --- |
| Main developer (user-labeled) | Gavin Bavin; solo, level 4, Horde, Durotar; 3 active quests; no selected route | Settings/instructions/scan need improvement. The level-25 Barrens example is a proposed case, not this diagnostic's character. |
| Friend's written Barrens report and Kobiee diagnostic | Written level 25; diagnostic level 26 Shaman, Horde, Barrens; solo, 6 active quests, 12 objectives | Early-zone recommendations, a selected step changing after acceptance, cross-zone objective detours, travel/corpse requests. Preserve the written/diagnostic level difference. |
| Additional supplied diagnostic | Vaiana Motonui; solo, level 22 Druid, Horde, Undercity; 3 active quests, 4 objectives; selected Barrens route | Supports checking retained routes across zones; no additional authored feedback inferred from the diagnostic. |

All captures report addon 0.5.7 and client 70205/interface 16001. Their captured
solo state cannot prove a party catch-up or last-player completion defect.

## Agreement and resolved conflicts

Overlapping requests: level-appropriate useful chains, focus on lagging party
progress, stable selected steps, an actual progress replan, clear Kill/Pick up/
Talk instructions, flight suggestions, Classic-style organized controls.

The user resolved the early-chain priority conflict: **catch up through useful
chains and explain low-level exceptions**, rather than always replaying a zone.
The repeated repeatable-quest feedback was explicitly withdrawn as already fixed;
retain the existing filter without claiming a new repeatable correction.

Other requests covered: previous/next previews; selectable distance units;
current-quest inclusion choice at guide start; NPC offer evidence; item/NPC
crosses; panel visibility for party/solo/raid; renamed quest views; dungeon
Start route; quest-log review suggestions; corpse directions. Professions stay
personal. Route invitations retain Follow route / Keep my route.

## Causes and limits

Code inspection established that recommendation refresh could replace a selected
route with the current-log bundle, and Scan retained its old selection while
showing counts. Both paths changed. Low-level discovery now needs a known useful
follow-up, while explicit active work remains selectable. Public NPC gossip is
availability evidence; IsPushableQuest is sharing support and cannot establish
pickup eligibility or hidden prerequisites.

Host tests use synthetic Lua 5.1 APIs; they establish regression behavior rather
than live beta compatibility. New flight-network data, optional native actions,
corpse coordinates, tooltip hooks and visual layout need the 0.6.0 checklist on
the actual client. Complete prerequisite, objective and flight graphs are not
available in this snapshot. Flight suggestions use observed public networks and
labeled straight-line/timed estimates, not obstacle-aware routing.
