# Stranglethorn Vale research refresh — 10 October 2026

This refresh targets `guides/coverage` at `b704b23f0189cc1fc681d15edbc1a5c113edf580` (current addon catalogue). The supplied 8 October/0.8.59 baseline is stale. The prior detailed review at [`../stranglethorn-vale-2026-10-08/README.md`](../stranglethorn-vale-2026-10-08/README.md) was already integrated into this branch history; all eight records it corrected (592, 3511, 3621, 8551–8554, 97331) still exactly match its reviewed `after` records. This refresh does not repeat or alter those corrections.

## Current scope and evidence

The exact-zone host audit compiles six fixed guides across both factions and the 31–40, 41–50 and 51–60 chapters. It checks 36 Stranglethorn Vale catalogue records and 103 static source points. All six guide flows are internally valid and retain 885 actions total (Horde 155/194/84; Alliance 196/169/87). The full current captures are [`audit-current.json`](audit-current.json) and [`flow-current.json`](flow-current.json); exact stage gaps are in [`remaining-gaps.json`](remaining-gaps.json).

The pinned and captured factual evidence remains in the October 8 review directory: 132 quest pages, 123 linked entity pages, a 129-row category list, seven entity searches, and checksums for 24 QuestieDB Forever files. The source policy and map-conversion limits are documented in `QUEST_DATA.md`; attribution is in `THIRD_PARTY_NOTICES.md`; travel evidence is described in `TRAVEL_DATA.md`. Existing captures and URLs are retained rather than duplicated. The prior Wowhead capture encountered three HTTP 403 responses; no new web capture was attempted after that denial. No new source fact was established in this refresh, so no catalogue data was changed.

## Remaining source gaps

Against the 8 October review's after-state, the current exact-zone audit still reports 11 unique quest IDs missing pickup coordinates, 11 missing objective areas, 11 missing hand-in coordinates, 12 uncertain pickup requirements and zero unknown quantities. The 8 October supplied starting list had 13/15/14/12/2 respectively; the prior eight evidence-based corrections reduced the location gap totals and resolved both unknown quantities. These are source gaps, not a complete inventory of all Forever offers, terrain or beta route safety.

Green Hills of Stranglethorn (338) remains deliberately unmapped for chapter-reward acquisition. The retained four-chapter candidate would put the page collection work before the hand-ins that award those pages in the fixed flow. Do not apply it until the main developer coordinates acceptance/completion dependency semantics. For Negolash, keep the item and lifeboat lure facts distinct; the lure location is still unknown. Old Captain quest IDs 614/615/618/620 remain distinct from 8551–8554 because title-level transfer is not supported by the conflicting identity/gate evidence. Arena Master item evidence points to quest 7810, not missing quest 7908. Quest 1036 has unmodeled reputation work; Warlock quest 1796 needs supported trade/craft acquisition rather than an invented work point. Tablets, keys, the caged cook and stolen shipments retain unknown work points where the available evidence does not locate the work.

The current six full-route flows validate their guide state, but their estimated distances are geometric estimates and do not establish walkable terrain, native map behavior or optimal reward timing. No shared routing, eligibility, lifecycle or UI code was changed. The Green Hills dependency question remains a coordination issue with the main developer.

## Validation

- `tools/audit_quest_guides.py --zone 'Stranglethorn Vale' --output ...`: six guides, 36 records, 103 static points; all six flow states valid; source completeness remains open as listed above.
- `tools/audit_quest_flow.py --zone 'Stranglethorn Vale' --output ...`: full six-guide captures, 885 actions, no shortened-prefix comparison.
- `python -m unittest discover -s tests -p 'test_stv_coverage.py' -v`: 10 passed.
- `python -m unittest discover -s tests -p 'test_routes.py' -v`: 18 passed (existing shared route behavior check).
- No Lua catalogue/runtime source changed, so TOC compilation was not rerun. Host checks cannot verify native WoW Forever beta API, map or route behavior.

## Player checklist

Record addon commit, beta build, faction/race/class, level/chapter, party state and class-quest setting. On fresh and mid-zone characters, check Scan guide, reload, pause/resume and zone re-entry; confirm fixed progress and chapter handoffs. Verify Green Hills item rewards arrive only on actual chapter hand-in; supplied Blood/Shipment deliveries do not trigger farming; use the filled Soul Gem on Yenniku; test each Captain quest identity separately; confirm Negolash's cutlass and lure; and escort Zimmix only after the real parent hand-in, recording pickup, route and return. Also check elite/group skip choice, class quest setting, unknown-offer retry, personal skip, and actual Booty Bay/Grom'gol boat/zeppelin access. Mark Pass/Fail/Skip with observed offers and completion events; accepting a quest or finishing objectives alone is not proof of hand-in.
