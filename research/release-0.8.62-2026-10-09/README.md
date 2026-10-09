# 0.8.62 reviewed zone integration — 9 October 2026

This release integrates the quest-guide branch through c45ebd7, including all
reviewed data corrections and zone evidence. The reviewed areas are Durotar,
Mulgore, Dun Morogh, Elwynn, Teldrassil, Tirisfal, Westfall, Barrens, Hillsbrad,
Duskwood, Dustwallow, Stranglethorn, Swamp of Sorrows, Tanaris, Un'Goro,
Western Plaguelands, Wetlands, Winterspring, Hinterlands, Thousand Needles,
Thoradin's Wall and Zephras Isle. Swamp is an audit refresh without new positions.

**201 quest records changed; 148 stage-correction rules; 22 zone reviews.**

## Scope and facts

Retain each zone's capture, source joins, full before/after action inventories,
tradeoff reports and native checklist under its research directory. Quest facts
use exact IDs, identity-checked correction rules and source attribution; 24
pinned factual files are checksum-verified and parsed without executing provider
code. Preserve current capture precedence and conflicting class/race/offer facts.
Entities, world-completion checks, XP baseline and the travel graph are unchanged.

The zone branch's raw old/new comparisons remain honest historical evidence.
Some old routes are invalid under newly supported prerequisites; other corrected
records add real work or remove explicit non-leveling placeholders. Those are
scope/fact changes, not measured journey savings. Do not rewrite REVIEW results
or present an inaccurate old route as a valid completed-route optimum.

## Shared compiler correction

The initial geometric relocation pass previously ran without the full journey
XP/log safeguards. Later guarded passes protected the route they received,
which could preserve harmful rearrangements from this first pass.

ImproveFixedGeometry now treats geometry as a proposal generator. Before
committing a move, re-evaluate the complete journey against identical current
quest facts and priced travel. Preserve every action, endpoints, actual hand-in
gates, escort adjacency, recovery boundaries, reward XP before each objective,
quest-log pressure, level deficits, kill lower bounds, difficulty and uncertain
or blocked legs. Replay chapter low/middle/high and partial-XP starts when given.
Safe shorter single-step and bundle moves remain. Long searches yield to the
existing loading UI. Later flow/network/terrain/connection passes remain.

These are bounded improvements with explicit guardrails, not a proof of global
optimality. The compiler's original greedy seed can still have quest-log capacity
or source-coverage problems. Missing map points, hidden offers, preparation/use
lifecycles, useful remote handoffs and unverified terrain remain research issues.
No new roads or travel graph are claimed by this source-data release.

## Validation

The final zone suite passes 153 checks; 118 routing regression checks and six
new geometric guard checks pass. All 152 compiled sections pass invariants and
11,833 source-point checks, including 608 starting-state guard replays. The
optional broad suite was interrupted after about 30 minutes after these checks
completed; no new full-suite pass is claimed. The pre-existing historical
catalogue digest mismatch remains documented, without changing its fixture.

See validation.json and source-review.json alongside this document for exact
final test totals, hashes, source changes and invariant results. Host checks use
Lua 5.1/interface 16001 and cannot prove native beta API behavior, pickup offers,
drop mechanics or walkable approaches. The historical pre-packing catalogue
fingerprint fixture is documented separately rather than rewriting its digest.

Installing a new version rebuilds saved blueprints with the corrected facts;
current quest progress, manual skips and checkpoints are reapplied. Subsequent
same-version reloads keep order. See root TESTING.md and each zone's player
checklist for native testing.
