# The Barrens player-facing text audit — 13 October 2026

This text-only review follows the Barrens request on `guides/coverage` at addon 0.8.66. It refreshes the baseline from the current branch rather than reusing the 9 October fact audit. Quest facts, wording required for completion, guide order, prerequisites, automatic progress, and shared rendering were not changed.

## Text sources

`GuideText.lua` builds action instructions from structured quest facts and appends a generic `GuideStepHint`; it composes both into tooltip text. `GuideReasons.lua` creates route/quest reasons and may append another hint to objective reasons. `GuideQuestList.lua`, `Navigation.lua`, and `StandaloneArrow.lua` expose those shared descriptions and reasons in the player UI.

The 111 exact-zone quest records and their start, objective, and hand-in points have no authored `description`, `travelReason`, `forPlayer`, `confirmationReason`, `label`, `objectiveLabel`, `action`, `story`, or `reason` text to edit. Player-facing text comes from quest facts and shared rendering. Removing repetitive generated lines therefore requires the shared policy review; this zone-only pass does not alter UI or renderer behavior.

## Before and proposed after

Current Horde 11–20 `The Hunter's Way` objective tooltip:

```text
Loot 4 × Flatland Prowler Claw from Flatland Prowler
Kill and loot Flatland Prowler.
Flatland Prowler Claw is needed to finish The Hunter's Way.
```

Proposed concise rendering for this ordinary item objective:

```text
Loot 4 × Flatland Prowler Claw from Flatland Prowler
```

The action already says what to loot and from whom; the following hint and generic reason repeat it. This is a shared-rendering proposal, not an applied Barrens text change. Keep genuinely useful context, such as the existing low-level line `Lower-level step: Unlocks Plainstrider Menace (level 12).` when that step is included as an exception.

## Counts and chapter review

- Zone-authored optional flavor/context strings found: **0**.
- Authored strings kept: **0**; rewritten: **0**; removed: **0**.
- Quest action instructions changed: **0**. All 174 objective steps across the five fixed-guide definitions remain intact.
- The refreshed audit compiled all five applicable chapters: Horde 11–20, 21–30, 31–40; Alliance 11–20, 21–30. Fresh and mid-chapter captures cover all five guides (10 views, 880 rendered step descriptions). Every objective action remains visible in its description. Repetitive generated hints/reasons are recorded as shared output, not zone-authored text.
- Representative Orc Mage and Human Mage profiles used class quests off. The host client uses synthetic map APIs, so displayed map names do not establish native map behavior.

The refreshed [current-audit.json](current-audit.json) checks 111 exact-zone records and 332 source points across five guides. [current-flow.json](current-flow.json) records the complete routes and all 440 route actions. [player-view-review.json](player-view-review.json) stores the fresh and mid-level previews, objective action visibility, and representative descriptions.

## Checks

- `tools/audit_quest_guides.py --zone 'The Barrens'`: five guides and 332 source points checked.
- `tools/audit_quest_flow.py --zone 'The Barrens'`: all five complete routes captured.
- `test_barrens_coverage.py`: 5 passed.
- `test_0842.py` (destination purpose/display layout): 18 passed.
- `test_0846.py` (visible reason policy): 19 passed.
- `test_085.py` (instructions and tooltips): 16 passed.

These checks use a Lua 5.1 host fixture and Interface 16001 source. No Lua changed, so no separate compile was needed. Host checks do not verify native beta tooltips, quest offers, map rendering, or safe routes.

## Player checklist and coordination

- In beta, review each listed faction/chapter at a fresh start and mid-zone. Confirm action text remains, generic objective filler is absent after coordinated renderer work, and useful prerequisite/low-level context remains.
- For Horde, verify Samophlange parent quests are actually handed in before their follow-ups; check each valve, key, console, manual assembly and final manual hand-in. Recheck Ishamuhale's carcass use, bait point/timer and completion; do not infer its use point from the mob location.
- Verify Sunscale Feathers are used once at each nest and confirm consumption/re-acquisition. Keep Valuable Vantages vial count and peak placements unknown until supported by current evidence.
- Check faction/race/class gates, elite choice, temporary unavailable pickups, personal skips, and the full chapter endpoints. Confirm roads, caves, Sludge Fen approaches, boats and flight unlocks in native play.
- Main developer: review a shared rule to display the action once, retain one short sentence for useful prerequisites, detours, danger, dungeon preparation, faction choices, or mechanics, and omit generic hints/reasons that restate ordinary work. No shared files were changed in this zone-only task.

No unclear Barrens-authored prose was found; the remaining cleanup is the shared-rendering issue.
