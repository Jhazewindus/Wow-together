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
