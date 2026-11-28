# Dungeon prerequisite source sweep

## Why

Dungeon collection routes stop or leave quests under Later when a prerequisite
is absent or mislabeled. The existing audit covered selected unresolved pages,
not every current dungeon membership, and had two disputed records.

## What changes

- Capture current Wowhead Forever quest pages for every listed dungeon quest,
  record page hashes and source availability, and compare each linear series
  with current prerequisite facts.
- Add only immediate predecessor edges supported by the current published
  series and corroborating evidence where the page marks a breadcrumb.
- Add the missing outdoor parent quest Passing the Blame (93601) with its
  source-backed start and turn-in so the Razorfen Downs chain can route.
- Clear the false Tiara of the Deep gate, keep the known false 6562 → 6563
  edge rejected, and report any current pages that Wowhead refused.

## Files

- `docs/briefs/dungeon-prerequisite-sweep.md`
- `tools/quest_corrections.json`
- `tools/import_warcraftdb.py`
- `tools/apply_quest_stage_corrections.py`
- `WowTogether_QuestData/QuestCatalogue.lua`
- `WowTogether/QuestCatalogue.json`
- `WowTogether/QuestCoverage.json`
- `research/dungeon-prerequisite-sweep-2026-11-28.json`
- `research/dungeon-prerequisite-level-audit-2026-11-28.json`
- `DUNGEONS.md`
- `tests/test_0829_dungeons.py`
- `tests/test_092_dungeon_level_gates.py`
- `tests/test_094_dungeon_prerequisite_review.py`
- `tests/test_095_dungeon_prerequisite_sweep.py`
- `changes/core/dungeon-prerequisite-sweep.md`

## Acceptance

- The two former disputed gates have a source-backed disposition: Open the Maw
  follows Dragonmaw Rumors; Tiara of the Deep has no required predecessor.
- The additional linear-series predecessor links are present in the generated
  catalogue and each parent quest record is available.
- The false Blackfathom link remains absent and the full membership audit reports
  no unverified prerequisite gates.
- Host tests cover the data relations and routeable parent record. In-game route
  behavior remains a play-test item.
