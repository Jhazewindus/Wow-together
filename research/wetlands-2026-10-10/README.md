# Wetlands refresh, 10 October 2026

Refreshed on `guides/coverage`, based on main
`cbd1e7608dc32c2080d8b1d967fb577c10084053` (addon 0.8.65). The 9 October
review retains the source evidence, corrections, ship graph, and explicit
unknowns in [`../wetlands-2026-10-09/README.md`](../wetlands-2026-10-09/README.md).
No new source capture or native-beta observation in this refresh supports
additional quest facts.

## Current scope and source gaps

The scoped audit compiles three Alliance chapters, checks 167 source points and
retains 6 / 180 / 77 actions in chapters 11–20, 21–30 and 31–40. No Horde
Wetlands leveling chapter is discovered. Current recorded gaps remain
pickup/objective/hand-in **5/11/5**, uncertain pickup requirements **6**, and
unknown objective quantities **3**. The gaps are:

- Quests 87318, 87491, 88756, 88757 and 88758: pickup, objective and return
  locations remain unverified; usable pinned quest records are absent.
- Quests 94497, 94499, 94500, 98208, 98246 and 98293: objective work areas or
  source/use joins remain incomplete. The three Call of Water output counts
  remain unknown; the supplied empty inputs are distinct from those outputs.
- Quest 484 retains uncertain pickup requirements. Existing conflicting count
  evidence for 484 and 303 remains unresolved in the prior review.

The 9 October corrections remain in place: actual crate/barrel/corpse
interactions; supplied tinder used on the catapult without a false farm or
count; separate Dun Algaz traversal work; and distinct Call of Water inputs.
They explain the already-integrated action changes from 6/179/76 to 6/180/77.
No further stage locations, counts, eligibility gates or prerequisites were
inferred. The prior evidence retains current-source conflicts, 24 pinned-file
hashes, source tiers, before/after records and actual ship endpoint facts.

Menethil–Theramore and Menethil–Auberdine keep explicit boarding and arrival
endpoints. They are directed Alliance ship links, not walkable water crossings.
NPC destinations remain distinct from docks, live ship availability and
personal flight connections. Elevation, docks, road approaches, and current
offers still need in-game observation.

## Current full-route estimates

The 0.8.65 flow capture validates all three complete Alliance sequences.
Distances and XP values are host estimates, not observed travel, native XP
pacing or terrain certification.

| Chapter | Actions | Distance estimate | Log peak | XP shortfall | Uncertain legs | Reward XP before work |
|---|---:|---:|---:|---:|---:|---:|
| 11–20 | 6 | 14,736 | 1 | 0 | 0 | 780 |
| 21–30 | 180 | 203,449 | 9 | 211,540 | 44 | 2,674,005 |
| 31–40 | 77 | 292,109 | 8 | 326,555 | 30 | 547,780 |

The earlier same-scope 0.8.61 replay reconciles the added Algaz traversal in
both complete orders and checks 12 starting states. All endpoints and old
actions survive, and each route state is valid. For 21–30, distance improves
200,056.34 → 195,957.74, but uncertain legs increase 41 → 42 and rewards are
delayed before quests 275, 295, 299, 305, 471, 472 and 98072. The strict guard
remains **REVIEW REQUIRED**; early reward sums do not erase individual delays.
These historical 0.8.61 candidate metrics are separate from the current 0.8.65
route estimates above. This refresh makes no route candidate change and claims
no optimization gain.

## Validation and player checklist

- Wetlands focused regressions: 9/9 passed. Route/session regressions: 18/18
  passed.
- Scoped audit: three guides and 167 source points. Full-flow capture: all three
  complete sequences valid.
- Lua 5.1 host load: all 87 TOC Lua files passed; interface remains 16001. No
  Lua source changed in this refresh.
- Native Forever behavior, ships, approaches and terrain remain untested.

Player checklist: both fresh and mid-zone Alliance characters; Menethil and
Greenwarden/road hub offers, chapter transitions, Scan/reload/re-entry; verify
the actual hand-ins before follow-up offers; interact with the exact three
crate/barrel objects and Rustlocke's corpse; traverse Dun Algaz and confirm
both kill goals plus traversal credit; use the supplied tinder on the real
catapult; test each distinct Call of Water input, actual water-use location,
output count and return; toggle the Shaman class setting without excluding
ordinary quests; check the Menethil docks and both actual ship arrival points;
record cave/elevation approaches, timed Moonshine duration, Stormwind/Darkshore
handoffs and personal flight access. Unknown or accepted unfinished work must
not finish a guide. Unavailable pickups remain temporary deferrals; personal
skips remain separate.

Existing prerequisite, water-use text, reputation/count, and optional dungeon
handoff proposals affect shared eligibility or guide behavior and remain
unapplied pending coordination with the main developer. No shared routing,
eligibility, lifecycle or UI code changed in this refresh.
