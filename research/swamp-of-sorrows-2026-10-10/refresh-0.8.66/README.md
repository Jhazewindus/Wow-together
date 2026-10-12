# Swamp of Sorrows branch-head refresh — 10 October 2026

This is a current-branch follow-up to the [`0.8.65 Swamp refresh`](../README.md), which already followed the supplied 8 October / 0.8.59 prompt baseline and the detailed source review in [`../../swamp-of-sorrows-2026-10-08/README.md`](../../swamp-of-sorrows-2026-10-08/README.md). Current branch is `guides/coverage` at `c4ffb9c945aea3ef6a139b899a91311e65bee8ff`, addon 0.8.66. This pass refreshes the zone after unrelated branch updates; it does not duplicate web research or alter the catalogue.

## Refreshed scope and remaining gaps

The scoped audit compiles all six faction/chapter guides and checks 22 direct zone records / 59 static source points. All six flows remain valid; two are gap-free. The 8 October starting snapshot and current scoped audit still agree on the source-gap union: three missing pickup locations (93429, 93430, 93464), six missing objective areas (3374, 93176, 93429, 93464, 93585, 93663), four missing hand-ins (93429, 93430, 93464, 93585), no uncertain pickup requirements and one unknown objective quantity for 3374. Full faction-specific gaps are in `audit-current.json`.

All 32 compiled quest IDs and 180 full-guide actions remain represented. Horde chapter action counts are 51/43/21; Alliance counts are 42/14/9. The current six-flow capture is `flow-current.json`. Its ordered stops and all flow metrics match the 0.8.65 refresh's saved `current-flow.json`; the scoped audit output is byte-for-byte data-equivalent when parsed. The whole-catalogue fingerprint differs due to unrelated zone changes, so this is a direct structural comparison, not a strict identical-catalogue hash replay. No route improvement or newly optimized order is claimed.

The unresolved facts and source limitations remain those in the prior reports: current specimen acquisition and work points for 93176; the 3374 Chained Essence source/count; 93429 credit method and giver/return; 93430 chain/giver/return; 93464 giver/destination; 93585 event mechanics and return; and 93663 shipment source. Existing pinned Forever and reviewed older-world evidence does not establish contemporary acquisition/event facts. The 8 October review preserves URLs, field provenance and hashes. Earlier live-page attempts were denied; no new web capture was attempted in this branch-head refresh.

Retain the supplied Oathstone, Chained Essence work, prerequisite 3373 and Itharius return for 3374. Do not infer the item count from singular wording or substitute Itharius's cave location for acquisition. Keep the Galen escort, faction hubs, temple hand-ins, revised high-ID Forever quest records, class-quest setting and cross-zone offers as reviewed. No coordinates, prerequisites, IDs, counts or source relations were inferred. Chapel/temple, underwater, cave, instance and escort approaches require native observation.

## Current host metrics

| Faction and chapter | Actions | Distance estimate | Log peak | Quest-reward XP shortfall | Uncertain legs |
|---|---:|---:|---:|---:|---:|
| Horde 31–40 | 51 | 159,807 | 3 | 455,050 | 32 |
| Horde 41–50 | 43 | 70,367 | 2 | 860,150 | 16 |
| Horde 51–60 | 21 | 53,418 | 1 | 2,416,180 | 7 |
| Alliance 31–40 | 42 | 136,861 | 2 | 195,000 | 33 |
| Alliance 41–50 | 14 | 28,574 | 1 | 0 | 6 |
| Alliance 51–60 | 9 | 45,000 | 1 | 2,054,900 | 5 |

Distances are geometric host estimates, not measured travel or proof of safe terrain, underwater access, entrance approach or taxi unlock state. The fixed guide order and automatic progress remain unchanged.

## Validation and player checklist

- Scoped host audit: 6 guides, 59 source points, 2 gap-free guides.
- Full-flow capture: all 6 chapters, 180 actions, all flow states valid.
- `tests/test_swamp_coverage.py`: 1 passed; `tests/test_routes.py`: 18 passed.
- No Lua source or catalogue data changed; no additional TOC compile was necessary.

On both factions and fresh/mid-zone characters, record offers separately for revised quest IDs; confirm prerequisite quests are handed in before follow-ups. Check the 3374 essence acquisition/count, three specimen sources and counts for 93176, 93429 credit method, 93430 chain, mage destination, 93585 event/return and 93663 shipment source. Test Stonard/Alliance hubs, Galen escort recovery, temple and cave approaches, underwater routes, faction transitions, Scan/reload/zone entry, class-quest opt-out, elite/group choices, and actual transport unlocks. Record offer, objective completion and hand-in as separate observations. Unavailable pickups remain temporary deferrals; personal skips remain distinct.

No shared routing, eligibility, lifecycle or UI change was needed. Native beta behavior is not validated by host checks.
