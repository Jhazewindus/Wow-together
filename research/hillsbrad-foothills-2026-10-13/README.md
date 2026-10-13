# Hillsbrad Foothills player-facing text audit — 13 October 2026

This text-only review follows the Hillsbrad request on `guides/coverage` at addon 0.8.66. It refreshes the zone baseline from the current branch instead of relying on the 9 October audit. Quest catalogue, route, prerequisites, order, automatic progress, and shared rendering were not changed.

## Where the visible text comes from

`GuideText.lua` creates action instructions from structured quest facts, adds a generic `GuideStepHint`, and composes the step description. `GuideReasons.lua` supplies quest/route reasons and adds another hint to objective reasons. The quest-list tooltip, navigation context, and standalone arrow consume these shared functions. The raw quest catalogue contains no Hillsbrad-authored `description`, `travelReason`, `forPlayer`, `confirmationReason`, `label`, `objectiveLabel`, or `action` prose fields on its 53 exact-zone records or their start/objective/hand-in points.

The repeated lines therefore have no zone-local text field to edit. Changing their display requires the shared rendering policy, which is outside this zone-only request and needs coordination with the main developer. No rendering or guide behavior was changed here.

## Before and proposed after

Current Alliance 31–40 objective tooltip, `Down the Coast`:

```text
Kill 10 × Torn Fin Oracle
Finish this quest objective in the marked area.
Required for Farren's Proof later in this guide; finish and turn in Down the Coast first.
```

The action and prerequisite wording are useful and remain intact. The generic middle sentence repeats the action and is the candidate for removal by a shared policy. This is a proposed shared-rendering outcome, not an applied Hillsbrad edit; current behavior remains unchanged in this audit.

For an unusual low-level step, retain the useful exception context. The Horde 31–40 `The Rescue` sample correctly keeps `Lower-level step: Unlocks Infiltration (level 34).` beside its `Use the quest item on Locked ball and chain` action. Do not apply a blanket removal to prerequisite or eligibility context.

## Editorial counts and guide review

- Hillsbrad-authored optional flavor/context strings found: **0**.
- Authored strings kept: **0**; rewritten: **0**; removed: **0**.
- Quest action instructions changed: **0**. All 117 objective steps across the five guide definitions remain available; their facts, wording, order, prerequisites, and automatic progress are unchanged.
- The refreshed audit compiles all five applicable guide chapters: Horde 21–30, 31–40, 41–50; Alliance 21–30, 31–40. The host review captures fresh and mid-chapter levels for every guide (10 views, 494 step descriptions). Every objective action remains present in its displayed description. The capture also records generated duplicate hints and reasons; these are shared output, not zone-authored strings.
- Review used representative Orc Mage/Human Mage profiles with class quests disabled, then inspected the complete fixed route through the same `GuideStepDescription` path used by tooltips. Host map names are synthetic and do not verify native map rendering.

The refreshed baseline is [current-audit.json](current-audit.json): 53 exact-zone quest records, 178 source points, five guides checked, and two recorded gap-free sections. The [current-flow.json](current-flow.json) capture preserves complete routes and action counts. The [player-view-review.json](player-view-review.json) records every faction/chapter fresh and mid-level preview, action visibility, and representative rendered text.

## Checks

- `tools/audit_quest_guides.py --zone 'Hillsbrad Foothills'`: five guides and 178 source points checked.
- `tools/audit_quest_flow.py --zone 'Hillsbrad Foothills'`: all five complete guides captured.
- `test_hillsbrad_coverage.py`: 5 passed.
- `test_0842.py` (destination purpose/display layout): 18 passed.
- `test_0846.py` (visible reason policy): 19 passed.
- `test_085.py` (instructions and tooltips): 16 passed.

These run in a Lua 5.1 host fixture with Interface 16001 source. No Lua source changed, so a separate compile was unnecessary. Host checks cannot establish native beta tooltip display, map positioning, offers, or travel behavior.

## Player checklist and coordination

- On a native beta client, inspect each listed faction/chapter at a fresh start and mid-zone. Confirm the action remains visible, prerequisite/low-level context is useful, and generic objective filler does not distract from it.
- Recheck prerequisites and hand-ins in the Battle of Hillsbrad, Elixir of Agony, Down the Coast/Farren's Proof, and The Rescue/Infiltration chains. Confirm guide order and automatic progress remain correct.
- Main developer: review a shared policy that keeps the action once, retains short context for useful prerequisites, unusual travel, danger, dungeon preparation, faction choice, or special mechanics, and suppresses generic hints/reasons that merely restate ordinary objective steps. No shared files were edited before that coordination.

No known Hillsbrad-authored prose was unclear or left for manual review; the remaining cleanup is a shared-rendering issue.
