# Quest data refresh: verified chain and dungeon context

## Goal

Refresh current dungeon, overworld, and class quest-chain facts using QuestieDB
only to identify candidates, and independently captured Wowhead Forever quest
pages to verify facts before they enter the catalogue. Preserve unknown
prerequisites and source provenance.

## Behavior

- Add a reviewed prerequisite correction only when the captured page's linear
  Series table confirms the immediate predecessor and both quest identities.
- Keep branching or missing Series pages unresolved; do not import Questie-only
  changes or infer dungeon membership from a quest's name.
- Add dungeon prerequisites for one dungeon only, following the guide's
  per-release limit. Cover outdoor and class quest chains.
- Report candidate, captured, confirmed, and imported counts in the release
  fragment.

## Files

- `docs/briefs/quest-data-refresh.md`
- `tools/quest_corrections.json`
- `WowTogether_QuestData/QuestCatalogue.lua`
- `WowTogether/QuestCatalogue.json`
- `WowTogether/QuestCoverage.json`
- `tests/test_quest_data_refresh.py`
- `tests/test_wetlands_coverage.py`
- `tests/memory-data-fingerprints.json`
- `changes/core/quest-data-refresh.md`

## Checks

- Test exact reviewed quest IDs, immediate predecessor IDs, source URL/date/hash,
  and preservation of unresolved branches.
- Run syntax check, host test suite, boundary check, and release build.
- Do not merge or publish; prepare a reviewable PR.
