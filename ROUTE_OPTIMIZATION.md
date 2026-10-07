# Quest-flow optimization — 0.8.49

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

`WowTogether/GuideFlowAudit.json` records each meaningful changed guide's
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
