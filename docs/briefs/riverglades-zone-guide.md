# Riverglades whole-zone quest guide

## Why

Riverglades is a live Forever zone (map 2548) with Alliance and Horde quest
lines, but the shipped quest catalogue only contains a small partial slice.
The dungeon prerequisite work does not make a zone guide.

## What changes

- Capture the complete current Riverglades quest inventory from Warcraft DB
  Forever and each quest's public route facts: faction, level, giver,
  turn-in, objective targets, and published map points.
- Use the pinned QuestieDB factual positions only under the owner's explicit
  permission; retain its commit, license note, and field provenance.
- Preserve quest variants as distinct quests; filter only records confirmed
  to be placeholders or retired. Do not infer quest prerequisites from ID
  order or neighboring titles. Import chain facts only from QuestieDB Forever
  or another published, explicit relation.
- Add source-backed records and map/category assignment to the generated
  quest catalogue so the normal zone guide can route all eligible Riverglades
  quest lines for either faction.
- Report the complete source inventory, records added, routeable steps, and
  unresolved source gaps. Unknown objectives or locations remain explicit.

## Files

- `docs/briefs/riverglades-zone-guide.md`
- `tools/import_riverglades_zone.py`
- `tools/riverglades_zone_quests.json`
- `tools/riverglades_quest_series.json`
- `tools/import_warcraftdb.py`
- `tools/forever_beta_facts.py`
- `tools/quest_enrichment.py`
- `tools/build_quest_dataset.py`
- `tools/apply_quest_stage_corrections.py`
- `tools/quest_corrections.json` (only explicit, corroborated chain edges)
- `tools/quest_exclusions.json` (source-confirmed placeholders only)
- `WowTogether/Catalogue.lua`
- `WowTogether/DataStore.lua`
- `WowTogether/LevelingGuides.lua`
- `WowTogether_QuestData/QuestCatalogue.lua`
- `WowTogether/QuestCatalogue.json`
- `WowTogether/QuestCoverage.json`
- `tests/test_0817.py`
- `tests/test_082.py`
- `tests/test_0829.py`
- `tests/test_optional_data.py`
- `tests/test_elwynn_coverage.py`
- `tests/memory-data-fingerprints.json`
- `research/riverglades-zone-quest-audit-2026-11-28.json`
- `changes/core/riverglades-zone-guide.md`

## Acceptance

- The source inventory is reconciled quest by quest, including same-name
  faction variants and non-routable placeholder records.
- Both factions receive the normal Riverglades zone guide, ordered by the
  existing guide builder and gated by the character's quest state and
  prerequisites.
- No location, prerequisite, objective, or level is guessed. The audit lists
  every item still missing source evidence.
- The normal guide index exposes Riverglades and keeps all work gated by the
  character's faction, level, accepted quest state, and verified prerequisites.
- In-game route behavior remains a play-test item.
