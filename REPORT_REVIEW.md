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
