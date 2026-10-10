# Tanaris refresh, 10 October 2026

Refreshed on `guides/coverage`, based on main
`cbd1e7608dc32c2080d8b1d967fb577c10084053` (addon 0.8.65). The detailed
8 October evidence, source provenance, fact corrections and scope decisions
remain in [`../tanaris-2026-10-08/README.md`](../tanaris-2026-10-08/README.md).
The supplied starting inventory is older than that review; all six stage
corrections and the 43-record endgame quarantine have already been integrated.
No newer Tanaris source capture or native-beta observation was available for
this refresh, so no additional quest fact or gate is inferred.

## Refreshed inventory and source gaps

The current ordinary guides compile all four faction/chapter sections, 60
quest IDs and 338 action occurrences (Horde 129/61; Alliance 108/40). The
scoped audit checks 77 source points and finds no gap-free guide section. In
ordinary scope, the remaining missing pickup locations are 654 and 2876; the
remaining objective-location gap is 654; no ordinary hand-in location or
uncertain pickup gate is recorded. Quest 654 still needs actual sample-testing
work areas and acquisition semantics. Quest 2876 still needs its item source
and confirmed pickup. No count is invented for the raw 654 input items.

The prompt's larger catalogue-level gaps (4 pickup / 30 objective / 1 hand-in
locations and 39 uncertain pickup requirements) are not silently marked solved.
The previously reviewed 43 level-60 scepter and Brood of Nozdormu records remain
excluded from ordinary leveling based on their literal raid, reputation and
chain evidence, while their catalogue facts and gaps remain. The 8286 raid-head
introduction, distinct quest IDs, actual prerequisite hand-ins and ordinary
elite/dungeon work are retained as documented in the 8 October review. The
exclusion is scoped to the evidenced endgame campaign; it does not suppress all
high-level work.

## Current full-route estimates

The 0.8.65 flow capture checks complete ordinary sequences, not a shortened
prefix. Each route state is valid in the host model. Estimates and quest-reward-
only XP shortfalls are not observed travel or live leveling outcomes.

| Faction and chapter | Actions | Distance estimate | Log peak | XP shortfall | Uncertain legs | Reward XP before work |
|---|---:|---:|---:|---:|---:|---:|
| Horde 41–50 | 129 | 271,465 | 7 | 604,685 | 26 | 2,972,735 |
| Horde 51–60 | 61 | 212,104 | 2 | 2,617,350 | 10 | 622,420 |
| Alliance 41–50 | 108 | 232,122 | 6 | 615,365 | 19 | 2,036,840 |
| Alliance 51–60 | 40 | 176,687 | 1 | 2,640,250 | 13 | 254,890 |

There is no new Tanaris candidate change to compare against these same-source
flows. The earlier 16-state, same-facts review remains the before/after route
comparison: it retained all 338 ordinary actions and endpoints, but the Horde
51–60 candidate increased estimated distance 204,295 → 212,104 and reduced
aggregate reward XP available before work 487,456 → 482,906, with reward timing
delayed before quests 992, 82, 10, 110, 113 and 32. Its guard remains **REVIEW
REQUIRED** for main-developer consideration. This refresh does not alter shared
routing, eligibility, lifecycle or UI code.

## Validation and player checklist

- Tanaris regressions: 6/6 passed. Route/session regressions: 18/18 passed.
- Scoped audit: four guides and 77 source points. Full-flow capture: all four
  complete sequences valid.
- Lua 5.1 host load: all 87 TOC Lua files passed; interface remains 16001. No
  Lua source changed in this refresh.
- Native Forever beta behavior remains untested.

Player checklist: test both factions with fresh and mid-zone characters; verify
Scan, reload, chapter transitions and no false completion; confirm the 654 kit,
raw samples, actual test interaction and acceptable outputs; confirm each
faction-specific supplied report and both true Zukk'ash prerequisite hand-ins;
verify ordinary guides omit the evidenced endgame campaign while preserving
ordinary elites, dungeon preparation, escorts and class settings; record real
Gadgetzan, Steamwheedle, Zul'Farrak, Uldum, boat/sea, mountain and flight access.
Temporary pickup deferrals must return after a confirmed offer; accepted or
deferred unfinished work must not mark the guide complete.

Exact unknowns and source URLs/hashes are retained in the earlier review. No
new shared-engine conflict was introduced; the existing Horde route tradeoff
still needs the main developer's review.
