# Quest-flow optimization — 0.8.52

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
