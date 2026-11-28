# Attunement quest run

## Why

Instance pages show attunement progress, but raid pages have no way to start a
route through the remaining attunement chain. Dungeon pages already use the
quest collection planner for dungeon quests and their prerequisites.

## What changes

- Build a personal questline guide from the selected instance's faction-specific
  access chain, using catalogue prerequisites and series links.
- Add a Start attunement route action to raid pages with a known unfinished
  chain. Keep the existing dungeon quest route for dungeon pages.
- Do not add or change quest facts; the route uses the access chains and quest
  catalogue already shipped.

## Files

- `docs/briefs/attunement-quest-run.md`
- `WowTogether/InstanceAccess.lua`
- `WowTogether/InstancePage.lua`
- `WowTogether/LevelingGuides.lua`
- `tests/test_instance_access.py`
- `changes/core/attunement-quest-run.md`

## Acceptance

- Starting the route includes the character's unfinished faction chain and
  catalogue prerequisites, including quests inside dungeons.
- Character eligibility and completed quest state continue to gate steps.
- Open raids and raids without a known chain do not show the action.
- Existing dungeon quest routes keep their current behavior.
