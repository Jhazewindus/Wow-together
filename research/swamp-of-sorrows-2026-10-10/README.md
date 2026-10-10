# Swamp of Sorrows refresh, 10 October 2026

Refreshed on `guides/coverage`, based on main
`cbd1e7608dc32c2080d8b1d967fb577c10084053` (addon 0.8.65), after the supplied
prompt's 8 October baseline. The older zone review
and its retained source evidence remain in
[`../swamp-of-sorrows-2026-10-08/README.md`](../swamp-of-sorrows-2026-10-08/README.md).
The current audit and full-flow capture are retained here. No zone facts changed:
the branch has no newer Swamp source capture, and the pinned source plus
reviewed ClassicDB/wiki evidence still do not establish the missing contemporary
Forever acquisition/event facts. The 8 October review's explicit source
limitations and URL/hash records therefore remain the supporting provenance.

## Refreshed scope and gaps

The case-insensitive scoped audit compiles all six faction/chapter guides and
checks 59 source points. It reports two gap-free guides. The source-gap union is
unchanged: three missing pickup locations (93429, 93430, 93464), six missing
objective locations (3374, 93176, 93429, 93464, 93585, 93663), four missing
hand-ins (93429, 93430, 93464, 93585), no recorded uncertain pickup
requirements, and the unknown 3374 objective count. Chapter labels are not
verified minimum levels. No coordinates, counts, relations, restrictions or
route instructions were inferred from names or older-world data.

All 32 compiled quest IDs and 180 actions remain represented across Horde
51/43/21 and Alliance 42/14/9 actions in chapters 31–40, 41–50 and 51–60.
All six full-flow sequences are valid in the host model. Current 0.8.65
estimated distance / quest-log peak / quest-reward-only level shortfall /
uncertain legs are:

| Faction and chapter | Distance estimate | Log peak | XP shortfall | Uncertain legs |
|---|---:|---:|---:|---:|
| Horde 31–40 | 159,807 | 3 | 455,050 | 32 |
| Horde 41–50 | 70,367 | 2 | 860,150 | 16 |
| Horde 51–60 | 53,418 | 1 | 2,416,180 | 7 |
| Alliance 31–40 | 136,861 | 2 | 195,000 | 33 |
| Alliance 41–50 | 28,574 | 1 | 0 | 6 |
| Alliance 51–60 | 45,000 | 1 | 2,054,900 | 5 |

These are current compiler estimates, not measurements or improvements over an
identical 0.8.65 before-state. The branch makes no Swamp quest or route change,
so no optimization gain is claimed. The older review's identical-source 24
starting-state comparison remains tied to its 0.8.61 source baseline; metrics
from that baseline are not mixed with this refresh.

## Validation and remaining work

- `audit_quest_guides.py --zone "Swamp of Sorrows"`: six guides, 59 points;
  expected recorded gaps remain.
- `audit_quest_flow.py --zone "Swamp Of Sorrows"`: six complete sequences;
  all flow states valid. The flow tool uses the chapter's capitalization.
- `tests/test_swamp_coverage.py`: pass (1 test). `tests/test_routes.py`: pass
  (18 tests).
- Lua 5.1 host load passed for all 87 TOC Lua files; TOC interface target is
  16001. No Lua source was changed in this refresh.

Native Forever beta checks remain required. Use the existing player checklist
in the 8 October review for both factions, fresh/mid-zone progress, offers and
hand-ins, item/event acquisition, cave/temple/underwater approaches, class
setting, Scan/reload/re-entry and escort behavior. In particular, confirm
separate revised quest IDs at the NPCs; a finished objective is not proof of a
prerequisite hand-in, and an unconfirmed offer remains a temporary deferral.

**Unresolved:** specimen sources for 93176; the current acquisition/count for
3374's Chained Essence; 93429's actual credit method and giver/return; 93430's
giver/return and chain relation; 93464's giver/destination; 93585's event
mechanic and return; and 93663's shipment source. Cave, temple and underwater
approaches still need player observation. No shared-engine issue was introduced.
