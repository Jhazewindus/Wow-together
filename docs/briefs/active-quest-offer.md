# Active quests and NPC offer evidence

## Why

A remembered negative NPC offer can outlive the interaction that produced it.
When the quest is already in the character's log, that pickup-only evidence
must not reject the accepted quest or stop its route.

## What changes

- `CataloguePickupCheck` treats a quest in the requested character's active log
  as available for continued work before applying pickup, level, identity, or
  prerequisite checks.
- Keep negative offer evidence as a gate for quests that are not active.

## Files

- `docs/briefs/active-quest-offer.md`
- `WowTogether/Catalogue.lua`
- `tests/test_0830.py`
- `changes/core/active-quest-offer.md`

## Acceptance

- A quest in the active log remains eligible when NPC offer evidence is false.
- The Drowned City style dungeon route continues past an already accepted goal.
- An unaccepted quest with confirmed negative offer evidence stays gated.
