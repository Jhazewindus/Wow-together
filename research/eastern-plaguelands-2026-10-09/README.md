# Eastern Plaguelands guide review — 9 October 2026

Refreshed on branch `guides/coverage` from main `6b9a7885` (addon 0.8.63),
after the previous coverage history through Dustwallow Marsh was merged. The
dated prompt baseline was 8 October / 0.8.59 and is superseded by the saved
`before-audit.json` and `before-flow.json`. The scoped audit compiles the full
51–60 faction guides; chapter labels are not verified gameplay minimums.

## Evidence and data changes

The primary reference is Questie/QuestieDB Forever at commit
`e0a6eaa86f181ac99262e34126bcd2ed1a1712d6`. All 24 downloaded source files
matched `tools/forever_source_manifest.json`. The saved `pinned-facts.json`
retains relevant factual quest/entity fields and field origins, omitting quest
prose. `direct-inventory.json` records all 109 direct Eastern Plaguelands
catalogue entries before corrections, including the compiled inventory's
neighboring-zone dependencies and follow-ups. The source URL for both changed
facts is:

- https://github.com/Questie/QuestieDB/blob/e0a6eaa86f181ac99262e34126bcd2ed1a1712d6/data/Forever/foreverQuestDB.lua

Two records now distinguish final hand-ins from preparation inputs:

| Quest | Final hand-in retained | Preparation stage retained | Still unknown |
| --- | --- | --- | --- |
| 5206 — Marauders of Darrowshire | 5 Resonating Skulls (13155) | 99 Fetid Skulls (13157), current Scourge Champion work area | How the inputs become the Resonating Skulls and where that action occurs |
| 6022 — To Kill With Purpose | 1 Coagulated Rot (15448) | 7 Living Rot (15447), current seven-target work alternatives | Where/how to use the supplied Mortar and Pestle to make the Coagulated Rot |

The prior required-item arrays had incorrectly presented each source input as
an extra final turn-in. Pinned Forever `objectives` lists the final item, and
`requiredSourceItems` identifies the preparation input. The correction changes
only `requiredItems`; existing objective requirements, target sets, quantities,
return NPCs, and locations remain guarded and unchanged. No missing event is
represented by a made-up NPC, object, or coordinate. In particular, 6022 still
has an objective-location gap for the result item and 5206 for the five skulls.
The corrections are appended to `tools/quest_corrections.json`, applied to the
packed catalogue, and covered by focused tests.

Public Forever pages and Warcraft DB Forever were not available through the
current network policy during this pass; no alternate proxy or policy bypass
was attempted. No new native-beta capture was available. The pinned factual
snapshot is therefore the primary evidence; secondary/live confirmation stays
on the player checklist.

The prerequisite review cross-checks current catalogue edges against pinned
`preQuestSingle`, `preQuestGroup` and identity-matched `exclusiveTo` facts.
Useful examples include 5206's AND requirement for 5168 and 5181, 5247 after
5246, 5464 after 5463, 8946 after 8945, and Horde's 6135/6136 AND hand-ins
(6022, 6042 and 6133) before 6144. These edges remain unchanged. 5247's
Alliance/race gate and the Horde-only 6135/6136/6144+ chain remain attached to
their actual records. The Naxxramas access variants remain separate quest IDs;
pinned Forever lists Argent Dawn reputation thresholds of 9,000 / 21,000 /
42,000 for 9121 / 9122 / 9123 and exclusive alternatives. The current guide
eligibility data has no general reputation-tier gate for these offer variants,
so the guide preserves them as visible choices rather than inventing an engine
gate. Confirm the live offer thresholds on the beta client before coordinating
any shared eligibility change.

## Refreshed coverage and full-route comparison

Before and after scoped audits both check 252 static source points and preserve
the same complete action inventory: Alliance 217 actions, Horde 201. Both
faction guides retain 17 unknown-location steps. Missing pickup coordinates
remain 5464 and 8946. Missing objective areas remain Alliance
5149, 5206, 5247, 5513, 5517, 5862, 6026, 8946, 9121, 9122, 9123, 9141 and
Horde 5149, 5206, 5513, 5517, 5862, 6022, 6026, 6146, 8946, 9121, 9122, 9123,
9141. No hand-in coordinate gap is recorded. Neither record changes pickup
eligibility or dependency edges, so all existing lower-level parents, faction
and class choices, same-title access variants, elite choices and onward
handoffs remain in scope.

The fixed-guide flow audit evaluated 48 Alliance and 37 Horde alternatives;
it found no loop reorder. The isolated repricing compares both old and current
complete orders using the same corrected stage facts. All 8 faction/state
checks preserve every action and endpoint, remain valid, and have no delayed
work rewards or regressed metrics. The existing order is retained; this is a
host estimate, not proof of walkable terrain or optimal beta travel. The guide
still has a high estimated reward-only XP shortfall and 62 Alliance / 69 Horde
uncertain travel legs, so it is not a claim of a perfect or fully mapped route.

The Chapel/road and dungeon records that still need evidence include:

- 5464 Menethil's Gift: the source object pickup has no verified position;
  Leonid's chapel dialogue remains the known next stage. Do not substitute the
  dialogue location for the object pickup.
- 8946 Proof of Life: the quest starts from an unknown Ysida Harmon spawn;
  no dungeon or outdoor pickup position is established.
- 5149 Pamela's Doll, 5247 Fragments of the Past, 6026 That's Asking a Lot,
  and 6146 Nathanos' Ruse retain unsourced item/event stages; their current
  mapped items and actors are preserved without asserting the result/use step.
- 5513/5517 keep the distinct Argent Dawn reputation requirements; 9121–9123
  keep their distinct reputation tiers and turn-in requirements. Native offer
  visibility and reputation UI behavior still need confirmation.
- 9141/9142 retain the actual token requirement and current records; published
  facts do not establish a profession-only gate for these quests.

These limits remain visible in the audit. No shared route, eligibility, guide
lifecycle, or UI module changed; the correction introduces no conflict needing
main-developer engine coordination.

## Validation

- `audit_quest_guides.py --zone "Eastern Plaguelands"`: both full faction
  guides pass all host invariants; 252 source points checked.
- `audit_quest_flow.py --zone "Eastern Plaguelands"`: both complete guides
  replay, 201/217 actions.
- `reprice_quest_stage_routes.py`: optimization guard passes, with all existing
  actions and endpoints preserved.
- `test_eastern_plaguelands_coverage.py`: checks the hand-in/source-item
  distinction, correction idempotence and conflict guards, and preserved
  unknown locations.
- All zone coverage regressions: 156 tests passed in 209.778 seconds.
- Fresh full-catalogue audit: 152 guides and 11,833 source points; its report
  matches the existing global audit exactly after JSON parsing.
- Lua uses the repository's Lua 5.1 host runtime and interface 16001 data.
  Host tests cannot establish native beta offer, item-use, map, or route
  behavior.

## Player checklist

- On Horde, accept Marauders of Darrowshire and verify the five Resonating
  Skulls are the actual hand-in. Confirm how the 99 Fetid Skulls are converted
  and whether the in-game quest tracker exposes that preparation accurately.
- On Horde, collect the seven Living Rot, then use the supplied Mortar and
  Pestle as the quest requires. Confirm the Coagulated Rot result and whether
  the quest tracker recognizes the use step before returning to Nathanos.
- On either faction, record build, level, class, faction, previous confirmed
  hand-ins, actual offer givers and item counts for Chapel, road, elite, and
  Scholomance/Naxxramas quest interactions. Keep the two Argent Dawn tiers and
  three Naxxramas reputation variants distinct.
- Walk the Chapel approaches, Tyr's Hand/road travel, Plaguewood and dungeon
  entrances in game. NPC/map points and estimated lines do not prove safe
  approaches, player-unlocked flights, or terrain walkability.
- Fresh and mid-zone characters: Scan guide, reload, zone entry, chapter
  transition, actual prerequisite hand-ins, temporary pickup deferrals, manual
  skips, and accepted unfinished work. Confirm no false Guide complete state.

No native beta behavior is claimed as verified by this review.
