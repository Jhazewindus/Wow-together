# Dungeon lead-up route and entrance capture

## Why

On 0.8.127, following the Krol'dok Stronghold quest route as Horde at level 36 did nothing, although the character could start quests leading to its level 38 quests. Five Forever dungeons also have no published entrance coordinates.

## What changes

- When all dungeon goals are above level, offer a route through any available lead-up quests and explain when the dungeon quests open; refuse with a reason when nothing can be started.
- Show the action and its outcome on the instance page.
- Learn an entrance from the last outdoor position when entering an uncharted dungeon or raid. Keep observations personal and build-specific and include them in the manual research export.
- Preserve existing attunement actions and only use recorded coordinates.

## Files

- `WowTogether/DungeonCollection.lua`
- `WowTogether/InstancePage.lua`
- `WowTogether/EntranceCapture.lua`
- `WowTogether/Sync.lua`
- `WowTogether/WowTogether.toc`
- `tests/test_dungeon_lead_up.py`
- `tests/test_instance_access.py`
- `research/dungeon-audit-0.8.127.txt`
- `changes/core/dungeon-lead-up-0-8-127.md`

## Tests

- Verify lead-up routes below dungeon quest level, refusal messaging, unchanged eligible routes, entrance capture, and anonymous build-specific research export.
- Run the host suite, syntax check, boundary check, release fragment validation, and release archive build.

## Acceptance

- At level 36, the Krol'dok route starts with actionable lead-up quests and names level 38 as its opening level.
- A refusal is visible on the instance page before the player presses the button.
- Entering an instance with no known entrance records the last outdoor position once per build; known entrances are not replaced.
- The observed entrance is exportable through `/wt research` without character identity.
- State clearly that route behavior needs an in-game play-test.
