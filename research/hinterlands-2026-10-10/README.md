# The Hinterlands refresh, 10 October 2026

Refreshed on `guides/coverage`, based on main
`cbd1e7608dc32c2080d8b1d967fb577c10084053` (addon 0.8.65). Prior fact
corrections, source URLs/hashes, cross-zone joins and unresolved dependencies
are documented in [`../hinterlands-2026-10-08/README.md`](../hinterlands-2026-10-08/README.md).
The two previously recorded objective-location gaps remain closed by the
reviewed Rhapsody item-source joins. No newer evidence in the worktree supports
additional quest facts, prerequisite edits or terrain claims.

## Refreshed scope and unknowns

The scoped audit compiles four complete faction/chapter guides, preserving all
50 quest IDs and 183 actions: Horde 93/25 and Alliance 56/9 in chapters 41–50
and 51–60. It checks 64 static points. Missing pickup, objective and hand-in
locations are 0/0/0; no pickup requirement or objective quantity is recorded as
unknown. All four route states are valid in the host model.

The audit still marks all four sections `source_data_gap_free=false` because
the substantial prerequisite/reason review backlog is open: 12, 9, 3 and 6
steps respectively for Alliance 41–50, Alliance 51–60, Horde 41–50 and Horde
51–60. Do not misread zero unmapped stages as complete source or route coverage.
The three useful Zul'Farrak parents remain external: Shadra needs The Spider
God (2936), The Divination needs Nekrum's Medallion (2991), and Ancient Egg
needs Prophecy of Mosh'aru (3527). Their actual giver/return/work facts are in
the prior handoff evidence. The 7816/7815 predecessor conflict also remains
unresolved; retain the established gate pending current offer/completion proof.

## Current full-route estimates

The 0.8.65 capture covers each complete guide. Distance and XP are model
estimates, not observed travel, actual XP pacing or route optimality.

| Faction and chapter | Actions | Distance estimate | Log peak | XP shortfall | Uncertain legs | Reward XP before work |
|---|---:|---:|---:|---:|---:|---:|
| Horde 41–50 | 93 | 240,945 | 11 | 951,200 | 36 | 1,841,670 |
| Horde 51–60 | 25 | 66,988 | 3 | 623,100 | 9 | 102,550 |
| Alliance 41–50 | 56 | 219,315 | 4 | 446,200 | 15 | 503,150 |
| Alliance 51–60 | 9 | 23,020 | 1 | 0 | 2 | 4,200 |

No Hinterlands route/data candidate changed in this refresh. The earlier
same-facts comparison preserved all actions and endpoints in 16 starting
states with unchanged distance, log peak, XP shortfall, early rewards,
uncertain legs, difficulty and blocked-travel estimates. Its PASS means
preservation after the two supported data corrections; it is not an optimization
gain. Current 0.8.65 metrics above are kept separate from that 0.8.61 comparison.

Mapped points at Jintha'alor, Altar of Zul, Skulk Rock and Revantusk still do not
prove a safe lift, ramp, tunnel or hostile-settlement approach. Rhapsody's
Feralas/Tanaris collection also needs a real cross-continent transport/arrival
observation. No shared routing, eligibility, lifecycle or UI code changed.

## Validation and player checklist

- Hinterlands focused regressions: 5/5 passed. Route/session regressions: 18/18
  passed.
- Scoped audit: four guides and 64 source points. Full-flow capture: all four
  complete sequences valid.
- Lua 5.1 host load: all 87 TOC Lua files passed; interface remains 16001. No
  Lua source changed in this refresh.
- Native Forever beta behavior and terrain approaches remain untested.

Player checklist: both factions, fresh and mid-zone characters, Scan/reload,
chapter progress and onward handoffs; Rhapsody's three of each item and actual
Feralas drops/transport; the supplied Venom parcel and real Shadra prerequisite
hand-in; the three Zul'Farrak parent quests and their actual offer/return facts;
Jintha'alor lifts/stairs and faction access; Altar/Skulk Rock entry; OOX and
Rin'ji escort adjacency/recovery; elite/group warnings; current 7815→7816 offer
and completion history. Record manual skips separately from temporary offer
deferrals, and do not mark accepted unfinished work complete.
