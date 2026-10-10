# Azshara quest guide review — 2026-10-10

## Scope and evidence

Refreshed the `level-zone:kalimdor/azshara` audit from the current packed data and recaptured current Forever quest/entity pages. The full evidence index, page URLs, capture dates and SHA-256 hashes are in [source-facts.json](source-facts.json). The pinned QuestieDB Forever facts used for the Hydraxian chain are recorded there with the exact revision and QuestDB hash. Page captures support quest identity, handoffs, item delivery, mob/item relations and positions; they do not establish safe routes or native beta offer behavior.

The regular route keeps both factions, both chapters, all elite/group work and existing class-quest settings. The AQ campaign quests 8288, 8305 and 8729 stay excluded from ordinary leveling. The level-60 6821–6824 Hydraxian raid chain remains visible.

## Changes

- Added mapped start, objective and hand-in data for the reviewed zone and cross-zone quest pages through the refreshed supplemental catalogue.
- For 3381, retained unknown pickup and hand-in stages, and added the 57 captured Azshara drop locations for all seven listed Feather source NPCs.
- Recorded 6804 and 6805 as AND prerequisites for 6821, then the explicit 6821 → 6822 → 6823 → 6824 sequence. Marked 6823 for offer confirmation because its pinned facts specify 9,000 Hydraxian Waterlords reputation.
- Corrected 8575's supplied Magical Ledger into a delivery token to Narain, rather than an item to farm. The importer only clears the incomplete-objective flag when no independent missing work remains.
- Preserved the existing reviewed 3511 and 3621 provided-delivery corrections.

## Coverage comparison

Fresh source-location audit before → after:

| Chapter/faction | Unknown location steps | Outstanding stages after |
|---|---:|---|
| 41–50, Alliance | 2 → 2 | 3381 pickup and hand-in |
| 41–50, Horde | 2 → 2 | 3381 pickup and hand-in |
| 51–60, Alliance | 15 → 9 | 6821, 6822 and 6824 raid objectives |
| 51–60, Horde | 15 → 9 | 6821, 6822 and 6824 raid objectives |

The 51–60 route now includes two additional prerequisite quests, 6804 and 6805, for a full 32 Horde and 24 Alliance quest IDs. The previous route had 30 and 22 respectively. Therefore the full-route before/after estimates below differ in scope; the quest-ID-matched replay is also reported separately.

| Route | Distance before → matched replay → full chain | Peak log | Uncertain legs | Reward XP before work | XP deficit |
|---|---:|---:|---:|---:|---:|
| 41–50, either faction | 28,050 → 28,050 → 28,050 | 2 | 3 | 21,000 | 0 |
| 51–60, Horde | 403,828 → 232,182 → 296,596 | 5 → 4 → 6 | 42 → 40 → 46 | 2,833,650 → 3,204,750 → 3,735,600 | 1,405,300 → 1,405,300 → 1,424,350 |
| 51–60, Alliance | 276,472 → 103,423 → 177,150 | 5 → 2 → 3 | 33 → 31 → 37 | 1,958,800 → 2,146,900 → 2,522,150 | 1,435,800 → 1,435,800 → 1,435,800 |

Distance is an estimate. The matched replay holds the quest-ID set constant while using refreshed stage/location facts; its action count rises from 101 to 107 for Horde and 74 to 80 for Alliance as previously unmapped stages become explicit. The full chain includes 6804 and 6805 and has its own metrics. All four final host flow validations pass. None of these measures verifies terrain walkability or beta gameplay.

## Remaining facts to verify

- 3381 pickup and hand-in locations are unavailable in the current quest evidence.
- The 6821 Emberseer, 6822 Molten Core encounter, and 6824 boss objective map points remain unknown. The item/boss relations and dungeon areas are known; no outdoor map pins were invented.
- 6823's reputation offer condition must be checked on a character at the required reputation in the beta. 7486's pickup offer rule remains unverified; no prerequisite was inferred from its coffer reward.
- Newly mapped drops, the chain offers, faction/class/race applicability, and native map behavior need player-side confirmation using the checklist below.

## Player checklist

- On fresh Alliance and Horde characters, inspect Azshara's 41–50 and 51–60 guides; confirm Scan guide, reload, and zone entry retain the correct chapter and faction route.
- On a character with class quests enabled and disabled, confirm ordinary Azshara work remains available and class-specific work follows the setting.
- Confirm 3381 is not shown as completable without its unknown pickup/turn-in, and that its feather targets include the captured local variants.
- Complete 6804 and 6805, then confirm 6821 becomes available; finish each prerequisite hand-in before checking the next offer through 6824.
- Confirm 6823's 9,000 reputation gate and 7486's actual pickup condition. Record character level, faction, race, reputation and beta build.
- Verify the MC/UBRS objectives in the actual instances and confirm elite/group choices do not prevent unrelated guide progress.
- Confirm accepted unfinished or temporarily unavailable quests do not falsely mark the guide complete; distinguish temporary deferrals from personal skips.

## Validation

Host audits use Lua 5.1 and the project's interface-16001 addon checks. Native beta behavior and terrain are not available to host validation. Focused Azshara and importer regression tests are recorded in the task result.

Recorded host checks: `test_azshara_coverage`, `test_importers`, `test_routes`, `test_addon` (81 tests, passed); `test_zone_coverage`, `test_0866` (25 tests, passed). The full zone guide audit and source queue were regenerated after the final data corrections. Final raw before/after audit and flow JSON captures are stored alongside this report.
