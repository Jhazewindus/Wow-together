# Alterac Mountains quest guide review — 2026-10-10

This review refreshes the supplied 0.8.59 / 8 October lead list. Its before
audit uses the existing `guides/coverage` branch at `53d5e12` (addon 0.8.65);
the final data and audit are regenerated on main’s merged 0.8.66 base
`eba4f29`. The scope is the existing Eastern Kingdoms Alterac Mountains
chapter, levels 31–40; chapter labels are not verified minimum gameplay
levels. The refreshed Lua 5.1 audit checks 2 faction guides and 60 stage
points (44 Alliance, 16 Horde). It is not a complete terrain map or a claim that every quest in the
zone is suitable for this leveling band.

## Changes

- **Strahnbrad Mystery (95534)** is Horde-only. Its Forever quest page reports
  Horde, level 36 / minimum 25, with no class or race restriction. This removes
  the four false Alliance actions and their false pickup gap. The Horde pickup
  NPC is still unknown; the mapped work is one Ancient Fire Elemental and one
  Singed Note from Argus Shadow Mages or Syndicate Wizards, then hand in to
  Shara Blazen in Hillsbrad Foothills.
- **Key to the City (93680)** now maps its one Grimy Key objective to Warden’s
  Footlocker (object 670427) at map 1416, 0.164, 0.893. Wowhead Forever’s item
  page links the key to that object, and its object page supplies the location.
  Blood in the Streets (92434) also supplies the same key. The guide’s item
  progress accepts a key already in the player’s bags, so that reward does not
  cause an extra footlocker farm. The two ways to get the item are not modeled
  as an exclusive prerequisite chain.
- **Shrewd Negotiations (97287)** now has its Wordeen pickup in Hillsbrad
  Foothills (map 1424, 0.616, 0.208) and Archmage Celindra hand-in in Alterac
  Mountains (map 1416, 0.142, 0.600). Its existing predecessor remains Heart
  of Disruption (96984).
- The refreshed quest-page evidence lists the two local Drunken Footpad (2440)
  locations for Valik (535), and records the mapped local Shade of the Archmage
  source for Heart of Disruption. The dungeon quest’s alternate source,
  Rath’maël (250657), still has no usable location and remains flagged
  incomplete.
- Both factions’ existing fixed guide orders and automatic progress behavior
  remain. No routing, eligibility, lifecycle, or UI code was changed.

## Before / after audit

| Guide | Before scope / actions | After scope / actions | Before recorded stage gaps | After recorded stage gaps | Other review |
| --- | ---: | ---: | --- | --- | --- |
| Alliance | 15 quests / 48 actions | 14 / 44 | pickup 95534 | none | 95534 removed by its Horde gate |
| Horde | 5 quests / 16 actions | 5 / 16 | pickup 95534, 97287; objective 92434, 93680, 97287; hand-in 97287 | pickup 95534; objective 92434 | pickup requirement for 535 remains unverified |

Across the two guides, the audit’s recorded guide-stage gaps go from 7 to 2.
Two 97287 endpoint gaps and the 93680 objective-area gap are resolved; the
Alliance 95534 pickup disappears because that quest is not Alliance-eligible.
The remaining zone gaps are the 95534 pickup NPC and the 92434 objective area.
The capture of Heart of Disruption also identifies a separate unmapped dungeon
alternative, outside the ordinary leveling-guide stage-gap count.
The regenerated global source queue has 363 records remaining (down from the pre-zone 365): 93680 and
97287 no longer need stage locations, while 95534 remains queued for Horde’s
pickup NPC and 535 remains queued for its pickup requirement.

## Full-route comparison

The flow audit preserves the whole action sequence and reports valid host-side
state transitions for both guides. The Horde scope is unchanged at 5 quests / 16
actions: estimated distance is 90,722.62 → 89,512.56; peak quest log remains 3;
reward XP available before objective work is 4,420 → 7,490; reward-only XP
shortfall remains 226,430; uncertain travel legs fall 10 → 8. These estimates
use mapped points and do not establish a walkable or safe path.

The Alliance scope changes because 95534 is removed: 15 / 48 → 14 / 44. Its
current 115,307.03 distance, log peak 7, reward-before-work 166,530, and
shortfall 161,000 describe the corrected scope and are not a same-quest-set
optimization comparison. The routed order itself was not rewritten.

The complete host flow reports retain the route stops and all metrics in
[`flow-before.json`](flow-before.json) and [`flow-after.json`](flow-after.json).
The freshly generated scoped guide audits are in
[`audit-before.json`](audit-before.json) and [`audit-after.json`](audit-after.json).

## Dependencies and unresolved facts

- QuestieDB’s pinned `foreverQuestDB.lua` defines `parentQuest` as the active
  parent quest needed for an offer. Quest 535 has `parentQuest=533` (Infiltration)
  at commit `e0a6eaa86f181ac99262e34126bcd2ed1a1712d6`. The current engine models
  completed prerequisites and observed NPC offers, but not a prerequisite that
  only needs to be active. Treating 533 as completed would overstate the gate;
  this needs main-developer coordination before any shared eligibility change.
- Quest 92434 starts at Wordeen in Hillsbrad and turns in to Image of Archmage
  Modera in Silverpine; it supplies Grimy Key. Quest 93680 requires the key and
  returns to Wordeen. The mapped Footlocker provides another source, so no
  strict 92434-completion edge was added.
- Captured pages report the series 92434 → 96984 → 97287. Quest 96984 is marked
  as a dungeon quest and remains excluded from ordinary leveling routes. Its
  local Shade source is mapped; Rath’maël’s alternate source remains unlocated.
- Quest 95534 has no mapped start. Shara Blazen is its return NPC, not evidence
  of its giver. Quest 92434’s mapper still has no supported objective area; the
  NPC hand-in location is not substituted for its work.
- Quest 535’s public page has no usable prerequisite list; the QuestieDB active
  parent fact and the actual beta offer still need to be reconciled. We did not
  turn the parent relation into a completion prerequisite.
- The current capture HTML includes comment controls, not comment bodies. No
  comment-derived claim was made. Exact quest/entity URLs and SHA-256 values,
  parsed facts, pinned revision and prior entity hashes are retained in
  [`source-facts.json`](source-facts.json).
- Map points do not verify borders, elevation, cave approaches, patrol safety,
  live offers, quest completion, or a character’s unlocked travel. No terrain
  shortcuts were added.

## Validation

- `test_alterac_coverage`, `test_routes`, `test_importers`, `test_lua_console`,
  `test_addon`, and `test_0866`: 109 tests passed under the Lua 5.1 host
  (`lupa` 2.8, interface 16001) against main 0.8.66 plus the Alterac corrections.
- Scoped guide and flow audits pass for both factions; the complete sequences
  remain valid. Audit artifacts above distinguish missing locations from the
  remaining 535 prerequisite review.
- Packed catalogue was regenerated with `tools/supplement_quest_data.py`; the
  supplemental capture history and entity-page hash evidence were retained.
- A host check cannot establish native beta behavior. Before treating these
  facts as verified gameplay, use this player checklist:

  1. On a fresh Horde character in the 31–40 Alterac guide, confirm the guide
     excludes 95534 for Alliance and offers it to Horde only. Record the actual
     95534 giver if available.
  2. Confirm 535’s offer while quest 533 is active, incomplete, completed, and
     absent from the log. Capture the exact NPC offer and hand-in state.
  3. Accept 92434, complete and hand it in; check whether the Grimy Key reward
     completes 93680’s item objective. Separately test Warden’s Footlocker and
     the mapped chest location.
  4. Check the Strahnbrad Fire Elemental / Singed Note targets and Shara Blazen
     return, then verify the Hillsbrad and Silverpine handoffs in the 92434 /
     96984 / 97287 series. Record the actual Rath’maël room if it is offered.
  5. Reload, use Scan guide, enter the zone mid-guide, and verify pickup
     deferrals restore only after a real offer; accepted unfinished work must
     not display false completion. Confirm full-zone progress and chapter
     transition without skipping required stages.
  6. Check the Alterac–Hillsbrad and Silverpine approaches in the beta client.
     The flow estimate is not route-safety evidence.

## Shared behavior coordination

The active-parent rule for 535 cannot be represented accurately by the current
completed-prerequisite edge. No shared behavior was changed. Main development
should decide whether an explicit active-parent eligibility condition belongs
in the engine before that fact is made an automatic gate.
