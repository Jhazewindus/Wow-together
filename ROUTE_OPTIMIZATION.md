# Quest-flow optimization — 0.8.57

## Terrain-aware comparisons after established flow

The target remains **completing the selected zone guide efficiently**. Version
0.8.56 added visible terrain waypoints to live navigation, but fixed-guide cost
comparisons could still price a cheap walk through those mapped mesas. The
compiler now reuses that visibility graph: reject crossing walking edges,
local chords and point attachments; price the visible bends instead. Directed
ships/zeppelins/trams keep their source costs. A missing lift/ramp approach is
blocked rather than given invented coordinates. Generic compilation never
assumes a personal flight, hearth or mount.

Keep the established geometric, objective-trip, reward-visit and network passes
as the initial complete plan. Repricing the earlier greedy seed can choose a
different trip that loses an established useful reward visit; the full-guide
comparison caught this in Dustwallow Marsh during development. The final pass
starts **after** established flow and uses the existing guarded step/bundle
search. Skip that search when the full plan's leg prices/bases are unchanged.
All comparisons use the same terrain and complete required ending conditions.
No accepted move delays previously collected quest rewards before an unchanged
objective or worsens log peak, acceptance-level XP shortfall, combat pressure,
required-kill lower bounds, reward totals, uncertain/blocked legs or recovery.
Replay bracket bottom/middle/top and a half-filled middle-level XP bar.

The graph snapshot adds no nodes to the imported source table and does not
change default flight-distance lookups. Reuse static polygon visibility and
bounded compilation caches; projection scratch clears at cooperative checkpoints.
The existing planner scheduler batches up to 16 small coroutine resumes within
a public `debugprofilestop` budget of 3 ms. A missing, private, invalid or
backwards timer keeps one resume per callback. No profiling clock is reset.
Cancellation and job errors are checked between resumes; actual native frame
cost can still exceed the budget inside one resume and needs beta testing.
Actual quest progress, unavailable NPC offers, manual skips, abandonment and
same-version reloads keep their established fixed-order recovery behavior.
Installing the update rebuilds a saved plan while applying personal progress.

The comparison without native map geometry retains all **152 sections** and
**12,985 actions**, with **608 additional starting-level/XP replays** and no
order changes. Lack of physical geometry must not manufacture a precise terrain
cost or a routing improvement. A second comparison supplies checksum-verified
published Forever map rectangles to the host. The old modules and candidate
see identical bounds, catalogue, terrain outlines and travel-source facts.
Neither test mode establishes current-beta walkability or actual leveling time.

With the published bounds, **two guarded moves improve two sections**; the other
**150 retain their order**. All **12,985 actions** and **608 bracket/XP replays**
pass. Horde Thousand Needles 21–30 moves Hypercapacitor Gizmo's work from its
earlier isolated placement to follow the Arnak Grimtotem work visit, retaining
the pickup, all objectives and hand-ins. Its complete estimate improves by
215.13 comparison units, with more known rewards already collected before that
objective and unchanged final quest XP/log/kill/difficulty measures. Alliance
Moonglade 51–60 moves The New Frontier's pickup to after the earlier Under the Chitin Was...
work/hand-in, before The New Frontier's own onward chain. The complete estimate
improves by 1,774.23 units, with unchanged reward/progression measures. These
units combine estimated ground distance and ordinary transport weights, not
observed yards walked, minutes or XP/hour. The changed old/new legs use eight
network estimates and two local estimates; no changed leg is blocked/unmapped.

The Thousand Needles route still contains twelve blocked estimates and four
uncovered legs, unchanged by the move. Their unknown costs cancel in this
comparison and cannot justify a changed leg; they remain actual mapping work.
Full named old/new sequences, metrics, endpoints and individual terrain changes
are in `GuideFlowAudit.json`. These are improvements among bounded alternatives,
not proof of a globally fastest or gap-free guide.

`GuideFlowAudit.json` records the published comparison. Terrain changes are
separate from established trip/reward/network traces. Synthetic regression
checks compare visible bends with live routing, reject zero-cost crossing
walks and hidden attachment shortcuts, retain directed transports, keep
unknown approaches blocked, and protect established early rewards. Terrain
coverage remains twelve approximate Thousand Needles footprints: no new road,
lift, spawn or prerequisite facts were added. The source-gap-free count remains
33 sections; 119 still require source facts. Combat/exploration XP, drop/spawn
waits and inventory timings stay unknown rather than becoming invented seconds.

Validation includes 1,417 broad host checks and 272 final targeted checks after
the scheduler update, including 20 new terrain/loading regressions. All 83 Lua
files compile under Lua 5.1. Native APIs, actual terrain and full-trip timings
remain beta-client checks.

The published-bounds 89-action Thousand Needles host fixture used 8,017 raw
cooperative resumes. Starting that guide with the budgeted scheduler completed
in 590 timer callbacks in a separate host run. That scheduled run used 1,072 ms
CPU, with a maximum callback of 29.06 ms; a single resume/collection can exceed
the scheduler budget. These observations support fewer scheduled frames, not
an in-game loading duration, FPS guarantee or universal frame-time bound.

Reproduce the published-bounds comparison using the existing reviewed geometry
report (its source URL/checksum are in `tools/forever_map_geometry.py`):

```sh
git show v0.8.56:WowTogether/FixedGuides.lua > /tmp/fixed-guides-0.8.56.lua
git show v0.8.56:WowTogether/FixedRouteOptimizer.lua > /tmp/fixed-route-0.8.56.lua
git show v0.8.56:WowTogether/FixedTravelCost.lua > /tmp/fixed-cost-0.8.56.lua
git show v0.8.56:WowTogether/TravelNetwork.lua > /tmp/travel-network-0.8.56.lua
python tools/audit_quest_flow.py --optimizer-module /tmp/fixed-route-0.8.56.lua --fixed-guides-module /tmp/fixed-guides-0.8.56.lua --travel-cost-module /tmp/fixed-cost-0.8.56.lua --network-module /tmp/travel-network-0.8.56.lua --forever-geometry conversion.json --label 0.8.56 --output baseline.json
python tools/audit_quest_flow.py --baseline baseline.json --forever-geometry conversion.json --output compared.json --comparison-output comparisons.json
```

## Previous travel ordering — 0.8.54

## Travel ordering after complete quest flow

The target remains **completing the selected zone guide efficiently**. The
earlier compiler improves steps/bundles using geometric distance, then checks
quest trips and ready rewards using the travel graph. This can leave a useful
travel alternative unexplored. Reuse that bounded step/bundle search after
the established flow, pricing the complete journey with published directed
ground and ordinary transport connections. Do not substitute a new router or
make personal flights/hearths available in a generic plan.

Every candidate must preserve the entire action set and fixed first/last steps.
Check each relocation before accepting it, rather than accept a whole shorter
permutation that hides a progression regression. Its complete travel saving
must reach the larger of 50 estimated units or 0.05% of the phase's original
journey. Unchanged legs cancel in a cheap first comparison. Both removed and
added legs need a `network-estimate` or `local-estimate` basis, with a changed
network leg. Unmapped geometry and blocked crossings cannot justify a move.
Attachments remain estimates; a published route does not prove its connecting
terrain is walkable. Short local estimates use the existing 400-yard cutoff.

Replay the viable full candidate, retaining known prerequisites, per-quest
stage order, immediate escorts and existing hub hand-offs. Unknown-location and
review steps divide recovery regions: no action may cross one. Do not increase
the held-quest peak, reward-only minimum-level XP shortfall, combat difficulty
pressure, repeated-kill lower bound, missing XP curve or uncertain/blocked legs.
Total known quest rewards cannot decrease, and no unchanged objective may lose
known rewards previously collected before it. Apply those progression checks
at the bottom, middle and top of the guide's bracket and with a half-filled
middle-level XP bar. Cache state results between accepted moves. Costs for
drops, combat/exploration XP, access waits and inventory remain unknown; they
are not turned into fabricated seconds or XP/hour.

Search limits remain two single-step sweeps within 24 actions and two small
bundle sweeps within 32 actions. Mixed bundles contain two to four close-level
steps; homogeneous nearby pickup/hand-in visits can contain up to eight. This
is a bounded improvement among evaluated alternatives, not a global optimum.
The existing full-trip passes still look farther ahead through dependencies.
Equivalent/uncertain alternatives keep their order. Actual NPC availability,
personal skips/deferrals and progress remain separate from compilation.

The identical-source comparison with **0.8.53** covers all **152 faction/zone/
level sections**, preserving all **12,985 actions**. **142 added travel changes
improve 60 sections**; the other **92 retain exactly their previous order**.
Examples include Barrens 11–20, Ashenvale 21–30, Thousand Needles 21–30 and
Stranglethorn 41–50. All **608 additional starting-level/XP replays** pass.
The complete changed old/new journeys contain **456 changed network legs**
and **280 changed local legs**, with zero changed unmapped/blocked legs.
These counts include both removed and added legs; they are not extra visits
or measured yards/minutes saved. `GuideFlowAudit.json` retains each complete
old/new action sequence, costs, guards, leg bases and individual network changes.
Established trip/reward traces are clearly separate from this release's changes.

Loading remains cooperative. Keep the compilation snapshot's bounded 4,096-leg
and 2,048-attachment caches between loading frames instead of clearing them
at every yield. Explicit reset clears them; graph/projection scratch data stays
separate. Discarded proposal replays use weak keys. Purely local guides skip
the added network search. Started plans remain cached: quest updates/scans/
same-version reloads do not run a new ordering search. Installing this release
rebuilds the saved guide with existing personal progress and skips.

The cooperative 246-action Durotar fixture with mocked 5,000 × 3,500 geometry
used **2,391 / 1,783 resumes** for prior/new compilers. One concurrent host run
used **1.874 / 2.077 seconds of CPU**, with observed maximum resumes of
**8.81 / 117.28 ms**. Fewer scheduled loading frames do not establish a native
frame-time bound; garbage collection and beta APIs need real-client testing.
The source-gap-free gate stays **33 sections**; **119 still need source facts**.
No quest/NPC/transport data was changed to manufacture a routing improvement.

All **1,371 host tests** passed, including **61 targeted flow/cache/recovery
checks**. All **81 Lua files** compile under Lua 5.1. The source audit checks
**11,822 points** and **16,849 action reasons** across all 152 guide sections.

To reproduce, capture the prior project's own modules against the same source
facts, then compare every guide and starting state:

```sh
git show v0.8.53:WowTogether/FixedRouteOptimizer.lua > /tmp/fixed-route-0.8.53.lua
git show v0.8.53:WowTogether/QuestFlow.lua > /tmp/quest-flow-0.8.53.lua
python tools/audit_quest_flow.py --optimizer-module /tmp/fixed-route-0.8.53.lua --flow-module /tmp/quest-flow-0.8.53.lua --label 0.8.53 --output baseline.json
python tools/audit_quest_flow.py --baseline baseline.json --output compared.json --comparison-output comparisons.json
python tools/audit_quest_guides.py --output guide-audit.json
```

The replay uses current source scope/cache maintenance with the prior ordering
modules; synchronous cache maintenance changes no cost/order. The published
release comparison instead uses the retained original 0.8.53 action/state
capture, with its compiler hashes verified from that tag. Transport and
catalogue hashes match exactly. Timed beta comparisons need the same starting
progress, all required actions and identical onward travel.

## Earlier rewards during existing visits — 0.8.53

The target remains **completing the selected zone guide efficiently**. The
previous hub pass could miss a useful ready hand-in when later pickups fixed
the same maximum log occupancy and the known XP/minimum-level checks stayed
equal. The reward was eventually collected, but the player did later work
without its XP despite an earlier visit to its giver.

After the established objective/hub/trip passes, the compiler now compares
ready hand-ins within an estimated 100 yards of an existing mapped stop. It
searches all hand-ins rather than only the next 128 actions. All previous
stages must already precede that visit; only hand-ins move. Compare the complete
ready visit (up to 24 rewards) and up to eight individual alternatives, retaining
the hand-ins' relative order. Two cooperative sweeps are bounded by the guide
size. First/last actions remain fixed. Unmapped/review regions, prerequisites,
immediate escorts and actual pickup availability keep their existing rules.

The new replay records known quest rewards collected before **each objective**.
A candidate cannot give any of those unchanged work actions less previously
collected quest XP. It must improve earlier collection, an existing progression/
log measure, or meaningful complete-route travel. Full-route distance cannot
increase; earlier XP alone never pays for an added detour. Prefer shorter full
travel, then more reward XP available before work. Keep all existing guards on
held quests, level shortfalls, difficulty, total quest rewards, required kills
and uncertain/blocked travel legs. Equivalent visits retain their order.

`rewardXPBeforeWork` is the sum of rewards already collected at the same work
actions. It measures earlier availability over that fixed work set, **not extra
XP**, XP/hour or measured fighting time. For example, making 100 reward XP
available before three more objectives raises the measure by 300 without adding
300 XP to the player. `workRewards` records the per-action values so an aggregate
improvement cannot hide a delay at another objective. Also replay the bottom,
middle and top bracket levels and a half-filled middle-level XP bar. Moving a
reward forward can level a character and reduce XP on another grey quest; those
losses reject the proposed visit, even if the lowest starting level passed.
Cache each state between accepted moves and create those replays only for viable
visits. Only known quest rewards
are included; combat, exploration, drop/spawn delays and inventory preparation
remain unmeasured. Actual starting XP/level can be supplied for replay, but the
generic fixed guide never assumes the current player's combat history.

The regression fixture keeps all 18 actions and the same full travel/log peak:
finish two quests → hand in one at the hub → depart for other work → return for
the other reward. A later independent three-quest loop fixes peak log occupancy
at three, so the old peak/gate checks see no benefit. Collecting the ready reward
during the first hub visit gives the intervening objective its XP sooner.
Separate fixtures cover grouped rewards, a reward more than 128 actions away,
true off-path detours, unknown rewards, incomplete work, review boundaries,
different maps, escorts and reload/scan recovery.

The identical-source comparison against **0.8.52** covers all **152 faction/zone/
level sections**, preserving all **12,985 actions**. It supports **47 earlier-
reward visits in 32 sections**; the other **120 retain exactly their previous
order**. No objective work changes order in the added pass. Examples include
Gold Dust Exchange during the Fargodeep Mine visit in Elwynn, Kolkar Leaders
during the Centaur Bracers visit in the Barrens, and Souvenirs of Death during
the Dangerous! visit in Hillsbrad. These depend on compatible progress and
actual offers; the existing level/identity filters remain.
All **608 additional bracket/starting-XP replays** retain the reward/progression
guards. They supplement the compiler's default reward-only starting state;
actual combat XP and the player's full play history remain unmeasured.

`GuideFlowAudit.json` records source/compiler hashes, complete old/new actions,
reward XP before each work action and the existing state metrics. Prior releases'
comparisons remain in their tags. Quest/NPC/transport facts are unchanged. The
per-move traces include the established candidate passes; `reward-visit`
identifies the added pass, rather than counting earlier trip changes as new.
The small guide explains collecting XP while there; saved plans retain that reason.
Installing a new version rebuilds a saved guide with personal progress/skips;
ordinary quest updates, scans and same-version reloads retain the chosen order.

Reproduce the identical-source comparison with the 0.8.52 capture, or regenerate
it from that tag before changing the optimizer:

```sh
git show v0.8.52:WowTogether/QuestFlow.lua > /tmp/quest-flow-0.8.52.lua
python tools/audit_quest_flow.py --flow-module /tmp/quest-flow-0.8.52.lua --label 0.8.52 --output baseline.json
python tools/audit_quest_flow.py --baseline baseline.json --output compared.json --comparison-output comparisons.json
python tools/audit_quest_guides.py --output guide-audit.json
```

The source-gap-free gate remains **33 sections**, with **119 still needing
facts**. Estimated connections are not a terrain mesh or proof of the globally
fastest route. Personal flight/hearth availability is not invented in the
generic compiler; live confirmed transport navigation stays separate. Timed beta
loops must compare the same starting state, every required action and the same
ending journey.

All 1,360 host tests passed, including 50 targeted checks for these rules and
fixed-guide recovery. All 81
Lua files compile under Lua 5.1. Extra state comparisons run only during loading
and viable reward alternatives. In the cooperative 246-action Durotar fixture
with mocked 5,000 × 3,500 map geometry, the prior/new compilers needed 2,326/2,392
resumes. That run used 2.90/3.49 seconds of host CPU; maximum observed resume CPU
was 44.0/102.6 ms. The search has a loading cost; these host values do not prove
native responsiveness or a universal frame-time bound. Started plans stay cached.

## Previous overlapping trip pass — 0.8.52

## Complete overlapping trips

The target remains **completing the selected zone guide efficiently**. Optional
quests are retained. The compiler now evaluates two or three overlapping later
quests together after the existing single-objective and hub passes. Moving one
quest alone can leave another reason to return to that area; a combined move can
remove the return. The complete dependency closure brings required pickups,
work and unlock hand-ins with it, in their original per-quest order.

The additional search keeps the existing limits: at most three nearby targets,
24 dependency actions, eight viable alternatives per anchor, two passes and
128 actions of lookahead. Each target must be within an estimated 300 yards of
the anchor. All first/last actions and onward travel remain. Unknown locations
and prerequisite-review boundaries prevent crossing. Immediate escorts and
item-use stages retain their order; no item stock or pickup eligibility is
invented. The same whole-route XP, difficulty, log, combat and geography guards
apply. Earlier passes remain the baseline for this additional search.

The two-quest regression has an early work visit, a later return for two pickups,
a second visit to their overlapping area and a separate onward loop. Individual
moves do not remove the second visit. Moving both closures together reduces the
complete estimate from 3,800 to 2,000 synthetic reference units, with the same
maximum three held quests. A three-quest fixture similarly needs the triple
alternative because each pair leaves the third visit necessary. These figures
are logic fixtures, not observed beta walking times or XP/hour. A shorter trip
that increases held-quest pressure or moves needed XP behind a pickup is rejected.

The identical-source comparison against **0.8.51** covers all **152 faction/zone/
level sections** and retains every one of **12,985 actions**. It accepts **nine
additional trip changes in seven sections**; the other 145 keep their earlier
order. Quest/entity/transport source facts are unchanged. `GuideFlowAudit.json`
records hashes, the old/new complete sequences and disambiguated action details,
per-move assumptions and state comparisons. Historical 0.8.50 comparisons remain
in that release tag. Compiler order remains fixed during play; scans, actual NPC
offers, completion, skips and recovery determine which stages are currently ready.

Examples from the complete comparisons:

- Horde Durotar 1–10 combines Ju-Ju Heaps and Zalazane with Forgotten Loa Idols.
- Horde Barrens 11–20 combines Fungal Spores and Kolkar Leaders with The Forgotten
  Pools while retaining their prerequisites and all onward work.
- Alliance Darkshore 11–20 compares several overlapping beach and woodland trips,
  bringing their necessary unlock work along instead of optimizing only the
  attractive objective prefix.

All changed complete routes keep the held-quest peak, reward-only acceptance XP
shortfall, difficulty pressure and uncertain/blocked leg counts from worsening.
They preserve estimated quest rewards and the shared-kill lower bound. No
optional branch is deleted to manufacture a shorter comparison. Generic planning
still uses published directed ground/ordinary transport links and estimated local
attachments; personal flights, mounts and hearths are not assumed. Live confirmed
transport routing is unchanged. Native terrain, combat, drops, failure/recovery
times and inventory preparation remain unmeasured where the sources lack them.

The source audit checks **5,230 quests**, **11,822 static points** and **16,849
catalogue action reasons**. **33 sections** pass its strict source-gap-free gate;
**119 still need facts**. Retaining all compiled actions is not 100% world mapping.
These are improvements among evaluated alternatives, not a global time optimum
or a guarantee of reaching a particular character level. Compare timed beta loops
from equivalent starting progress through the same required ending state.

All **1,349 host tests passed**. The 39 targeted checks cover combined trips, escorts, item-use/unknown drops,
level rewards, log pressure, recovery boundaries and persisted guide reasons.
All 81 Lua files compile under Lua 5.1. In one cooperative Durotar fixture with
246 stages and mocked 5,000 × 3,500 map geometry, the old/new compiler yielded
2,124/2,325 times and used 2.70/2.87 seconds of host CPU. Maximum observed resume
CPU was 43.8/40.8 ms in that run. The extra search has a loading cost; started
guides retain their cached order. These host measurements do not establish beta
frame rate, terrain or a universal timing bound.

Reproduce the comparison with unchanged source data:

```sh
git show v0.8.51:WowTogether/QuestFlow.lua > /tmp/quest-flow-0.8.51.lua
python tools/audit_quest_flow.py --flow-module /tmp/quest-flow-0.8.51.lua --label 0.8.51 --output baseline.json
python tools/audit_quest_flow.py --baseline baseline.json --output compared.json --comparison-output comparisons.json
python tools/audit_quest_guides.py --output guide-audit.json
```

## Previous same-hub pass — 0.8.50

## Same-hub reward and log-space pass

The target remains **completing the selected zone guide efficiently**. A useful
hand-in is not judged only by the walking distance it saves. After the existing
objective-loop search, the same compiler evaluates ready hand-ins and pickup
dependencies within an estimated 100 yards of a hub visit. It retains all valid
quest actions, per-quest order and first/last positions. The added pass never
pulls unfinished objective work forward: those stages must already be before
the proposed visit. Missing geography and prerequisite-review boundaries still
prevent moves.
The hub pass also keeps an existing nearby prerequisite hand-in ahead of
unrelated pickups; pulling a dependency block can still carry its hand-in and
follow-up together. Small walking savings do not override that unlock visit.

At equal complete-route travel, a changed order needs a measured replay benefit:
fewer held guide quests, less known acceptance-level XP shortfall, less difficulty
pressure, higher estimated quest rewards or less shared kill work. Every other
guard from the objective-loop pass still applies. A lower log peak by itself
does not justify additional walking. Estimated travel savings still require the
existing minimum improvement margin; equivalent visits are not reshuffled.

The regression fixture compares pickup A → finish A → pick up B/C → distant B/C
work → hand in A/B/C with pickup A → finish/hand in A → pick up B/C → distant B/C
work → hand in B/C. Both retain all actions and endpoints and travel 1,800
synthetic reference units. The latter reduces peak held quests from three to
two. When B requires level 2 and A supplies the explicit 100-XP threshold in
the fixture, taking A's reward first removes that 100-XP shortfall. These are
logic fixtures, not observed Forever rewards, times or XP/hour.

`NewGuideFlowModel` additionally accepts explicit `startXP` and `initialLog`
(unrelated held slots) for same-state comparisons. Neither value is invented by
the generic compiler, which does not assume a native beta log capacity. If a
known capacity is supplied, reserved unrelated slots count toward overflow and
remain held at the end. Required-item preparation and combat/drop/spawn timings
still need data; their unknown flags do not grant eligibility or stock.

The small guide explains useful reward-first/log-space visits and saves those
facts with its plan. Quest progress, actual NPC offers, skips and reload recovery
still filter the fixed order rather than reoptimizing it during play.

## Corrected scope and fair comparisons

The audit found explicit `<NYI>`/`<TXT>` placeholder quests that the existing
UNUSED/disabled filter missed. Those records remain searchable catalogue facts
but cannot become leveling instructions. This includes quest 4323, Get those
Hyenas!!!, whose source has no quest giver. It is not the real Thousand Needles
introduction: Message to Freewind Post (4542) and Pacify the Centaur (4841) remain
level-25 guide quests. No optional real quest is deleted to manufacture speed.

The `v0.8.50` tag's `GuideFlowAudit.json` comparison replays the **0.8.49 QuestFlow.lua**
against the exact same corrected scope as 0.8.50. Its module checksum and the
unchanged catalogue/travel hashes are recorded in the capture. Quarantining
editorial placeholders is kept separate from route-improvement claims. All
152 sections retain the same 12,985 valid actions between those comparisons.

The 0.8.50 comparison accepts **19 additional hub changes in 13 sections**.
Every changed complete route passes the same action/endpoints, prerequisite,
log, XP/difficulty, kill and geography guards. Two changes lower the held-quest
peak and three lower the reward-only XP shortfall. Alliance Westfall 11–20 keeps
the same full travel estimate while lowering held-quest peak from 14 to 13.
Alliance Hinterlands 41–50 lowers that peak from five to four and the reward-only
XP shortfall from 450,100 to 446,200, with a lower full travel estimate.
Horde Thousand Needles 21–30 keeps its real introduction and all 89 valid actions;
its existing route is retained rather than reordered without a supported benefit.
Old/new named sequences and each accepted move's actual comparison deltas are
in the report. These are estimated route/replay benefits, not timed beta results.

The strict audit now has **33 source-gap-free sections and 119 still needing
facts**. The one-section increase comes from excluding an explicitly unimplemented
record, not acquiring new coordinates. The catalogue's 5,230 records and 11,822
stored points are unchanged. All 152 sections pass route invariants; that does
not make the unresolved source facts complete.

Reproduce the fair baseline without changing a checkout:

```sh
git show v0.8.49:WowTogether/QuestFlow.lua > /tmp/quest-flow-0.8.49.lua
python tools/audit_quest_flow.py --flow-module /tmp/quest-flow-0.8.49.lua --label '0.8.49 with identical placeholder exclusions' --output baseline.json
python tools/audit_quest_flow.py --baseline baseline.json --output compared.json --comparison-output comparisons.json
```

These are improved choices among bounded alternatives. Equal estimated distance
with fewer held quests is a reliability improvement, not a measured time saving.
Incomplete source facts, native terrain, combat/drop delays and Forever timing
still prevent a claim of 100% mapping or globally optimal leveling time.

## Release verification

All **1,334 host tests passed** for the release.
The 35 targeted checks cover equal-distance rewards/log space, nearby unlock
priority, genuine Thousand Needles introductions, explicit placeholders, fixed
order, skips and cooperative recovery. All 81 Lua files compile under Lua 5.1.
The upgrade fixture rebuilds stale saved coordinates from 0.8.49 while retaining
completed and accepted quests and manual skips. Same-version reload retains the
saved plan; installing another version may change step numbers.

The full Mulgore 1–10 guide (200 stages) also compiled cooperatively in the host
fixture with 5,000 × 3,500 mocked map geometry: 1,902 resumes, at most 6.14 ms
CPU per resume in that run. This demonstrates yielding in that scenario, not
actual beta frame rate, terrain accuracy or a universal performance bound.

## Previous objective-loop pass — 0.8.49

The target chosen for this pass is **completing the selected zone guide
efficiently**. Optional quests are not silently removed to reach a level sooner.
This improves the existing fixed-guide compiler; it does not replace routing or
reshuffle a started guide when the player moves, accepts, abandons or hands in a
quest. Scan guide continues to apply current progress to the fixed order.

## What changed

The old compiler already separated pickup, work and turn-in actions, respected
known AND/OR prerequisites, and made local distance-based step/bundle moves.
Its short search could miss a useful whole trip when an unlock hand-in, pickup
and objectives were separated by other steps.

The added bounded pass considers an overlapping later objective and pulls its
necessary earlier actions together: work, required turn-ins and pickups,
including prerequisites elsewhere in the selected guide. It compares the
**entire resulting guide**, including onward travel, against the complete old
sequence with the same first/last action. It can return for an unlock earlier,
collect the follow-up, then do the overlapping objectives together. It retains
all per-quest work, item-use/interactions and immediate escort sequences.

Candidate dependency closures are limited to 24 actions, eight evaluated nearby
alternatives per anchor, two passes and a 128-action lookahead. Objective areas
must be within an estimated 300 yards. Small gains below the larger of 50 travel
units or 0.05% of the complete comparison are ignored, unless counted identical
kill objectives share work without additional travel. These bounds/margins are
heuristics, not measured optimum settings.

## Evidence required before accepting a change

| Check | Rule |
| --- | --- |
| Work and onward position | Same action objects, per-quest order, first action and final action; nothing removed. |
| Prerequisites | Required turn-ins precede pickups. OR branches need one real parent. Unresolved external gates stay marked for review. |
| Recovery | Do not pull actions across missing-location/review boundaries. Manual skips and NPC deferrals remain separate. |
| Quest log | Simulate accepts and hand-ins; do not increase the peak number of held guide quests. Explicit capacity supplied to the simulator rejects overflow. Native beta capacity and unrelated held quests are not inferred. |
| Level progression | Replay known minimum levels and quest-reward XP. Do not increase XP still needed from unmeasured outside work, or the pressure of difficult work ahead of rewards. Do not reduce estimated quest rewards. |
| Shared combat | Share kill credit across identical, counted nearby NPC requirements already accepted when the kills occur, even if their displayed steps are separated. Later pickups get no retroactive credit. Drop quantities do not imply kill counts or drop rates. |
| Geography | Use existing published directed ground links and ordinary transports, with faction/hostile-settlement checks. Do not increase uncovered or blocked estimated legs. |

The XP replay uses the labelled Classic reward/level-curve baseline. It **does
not prove** that a player will reach a future pickup level: kills, exploration,
rested XP, beta changes and unknown rewards remain unmeasured. Shortfalls are
reported, not hidden by fabricated combat XP. Live acceptance-level and actual
NPC-offer checks still gate every pickup. Known item requirements remain part of
their original quest stages/shopping guidance; unavailable stock and preparation
time are not invented. The simulator flags those inventory assumptions.

The generic comparison never assumes personal flights, mounts, hearth bindings
or cooldowns. Published ship/zeppelin/tram/ordinary transition durations are
estimates converted to comparable reference walking units. Live navigation
continues to use the player's confirmed flight connections and measured timing.
Local point-to-road attachments, uncovered geography and settlement margins are
estimates, not a terrain mesh. Cache/state is isolated from flight lookups and
compilation yields during graph/state work.

## Old versus new evidence

The `v0.8.49` tag's `WowTogether/GuideFlowAudit.json` records each meaningful changed guide's
complete old/new action sequences, named quests, alternatives evaluated,
accepted loop changes, assumptions and comparison metrics. Repeated objective
tokens retain their per-quest occurrence order; map/entity facts are checked
unchanged. Baseline: release 0.8.48, commit
`6e9d2f71fe4a1ec29039e1e80af8e0b734fce57b`, identical catalogue and travel data.

All **152 discoverable faction/zone/level sections** pass complete permutation,
prerequisite, escort and non-regression checks. **38 sections** have accepted
changes; the other 114 retain their old compiled order. Examples:

- **Barrens, Horde, levels 11–20:** move the Rilli Greasygob work/hand-in and
  Samophlange Manual pickup/work earlier to join upcoming work. Its prerequisite
  hand-in remains before the follow-up pickup. All 216 actions and endpoints
  remain, held-quest peak stays 15, reward XP stays equal, and the reward-only
  outside-XP shortfall decreases slightly. The published-ground estimate falls;
  actual flight/combat timings need testing.
- **Mulgore, Horde, levels 1–10:** collect/do The Longwalkers in an existing
  overlapping trip instead of a separate later branch. All 191 actions and
  endpoints remain; log peak, reward XP, difficulty and uncovered legs do not
  worsen. The small guide names the related trip when it is still relevant.
- **Redridge, Alliance, levels 11–20:** combine the Return to Verner/A Baying of
  Gnolls hand-off and Redridge Rendezvous/Alther's Mill chain with overlapping
  bridge work. All pickup, objective and hand-in stages remain. This section has
  all locations, counts and prerequisite-read facts needed by the source audit;
  that is factual coverage, not in-game proof of timing or NPC availability.
- **Regression fixture:** compare near work → distant cave → return/unlock →
  cave again with near work → return/unlock/pickup → combined cave work → returns.
  The latter is selected only when full-journey/state checks support it. A
  shorter route that delays necessary XP or makes combat harder is rejected.

No version-matching timed community route was used as proof of optimality.
Bundled quest/entity facts and the attributed published travel snapshot remain
the sources; their capture/identity restrictions are in `QUEST_DATA.md` and
`TRAVEL_DATA.md`. A fresh public Forever quest-789 read confirmed its level,
minimum level and reward, but did not expose complete objective geography. It
was not used to overwrite stronger existing facts or infer a prerequisite.

## Coverage and honest limits

The catalogue still has **5,230 quests** and the audit checks **11,822 static
points**. **32 of 152 guide sections** meet the existing strict source-gap-free
gate; **120** still contain unknown locations, counts, prerequisites or external
gates. This optimization does not turn those gaps into invented coordinates or
claim 100% world coverage. Every existing compiled action is accounted for; that
is distinct from every source fact being verified. Combat/drop/spawn, inventory,
failure/recovery times and real terrain accessibility need further observations.

These routes are **improved among the evaluated alternatives**, under the stated
assumptions. They are not certified globally optimal or guaranteed XP/hour.
Live testing should compare whole completed loops from equivalent character
states, including onward travel, rather than timing only the attractive prefix.

## Reproduce validation

Using the Lua 5.1 test environment:

```sh
python tools/audit_quest_flow.py --output baseline.json
# Run that baseline capture on 0.8.48, then the next command on 0.8.49.
python tools/audit_quest_flow.py --baseline baseline.json --output compared.json --comparison-output comparisons.json
python tools/audit_quest_guides.py --output guide-audit.json
python tools/audit_quest_guides.py --output guide-audit.json --require-complete
```

The last command must fail while any section has source gaps. Passing planner
invariants is not permission to call missing facts complete. Source hashes and
guide scope must match for a same-source old/new comparison.
