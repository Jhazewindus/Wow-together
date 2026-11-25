# Gold farm priors

This LoadOnDemand package contains legacy, unconfirmed reference facts. It is
not proof that the rows, spawns, yields, or respawn times still apply to
Forever. Players' observations should correct them.

## Creature farms and skinning

- Names, levels, creature loot, skinning loot IDs, skinning yields, and spawn
  coordinates are selected from CMaNGOS ClassicDB commit
  `ec4f596146be6467ea93c57397858e329e2db852`, snapshot
  `Full_DB/ClassicDB_1_12_1_z2815.sql.gz` (SHA-256
  `4f92db520868ab4e566726f68b5b2e380ae781209beaf22237b4f7f04600d0c0`).
  The snapshot is GPL-3.0. See `GPL-3.0.txt` and
  `LEGACY_DATA_COPYRIGHT.md` for the full licence and copyright notice.
- Map bounds and target map names are from QuestieDB Forever 1.60.1.69893
  commit `e0a6eaa86f181ac99262e34126bcd2ed1a1712d6`, conversion report SHA-256
  `0229566017126c2577e77d2bcc7c9f995648fb27ed32a7918fa44ace0664fb22`.
  Only its published map transforms are used.
- Creature IDs present in QuestieDB's Forever correction lists are marked
  `changed`; no Questie names, loot, or coordinates are copied.
- Each creature is assigned to the zone with the most converted spawn points;
  ties use the smaller map ID. At most 24 points are retained per creature.
- Skinning loot is appended to the same creature farm only for characters
  whose Skinning skill meets that creature's required skill.

## Gathering yields and fish

- Ore, herb, and pool template facts and literal yields come from the same
  pinned CMaNGOS snapshot. Fish are selected from
  `fishing_loot_template` by source area, with direct reference rows expanded
  from `reference_loot_template`; non-fish entries are omitted.
- Yields retain source chance and minimum quantity. These values are legacy
  priors, not measured Forever rates.

## Size and loading

At this revision, `FarmPriorData.lua` is 5,370,556 bytes and
`GatheringPriorData.lua` is 154,143 bytes on disk. Host Lua 5.1 tests observed
about 10.68 MiB of additional Lua heap after loading the package; this is a
host estimate, not a WoW client measurement. The 94,950 creature loot rows
that reach the package currently divide by positive drop chance as follows:

| Chance range | Rows |
| --- | ---: |
| Under 0.1% | 67,824 |
| 0.1% to under 0.5% | 7,001 |
| 0.5% to 5% | 11,948 |
| Over 5% | 8,177 |

Filtering out loot below 0.5% retains 20,125 rows. A host-side regenerated
payload shrinks `FarmPriorData.lua` to 2,866,553 bytes, saving 2,504,003 bytes
(2.39 MiB) on disk. The same host load measured 5.22 MiB of Lua heap, saving
5.46 MiB but remaining above the 4 MiB target. The follow-up should put the
slim creature/loot index in the always-loaded data and load spawn coordinates
per zone only when starting a farm; no zone-only search restriction is needed.

`tools/import_vanilla_loot.py` is a separate parser for dungeon-loot audit
pages. It does not produce this package. `tools/gold/priors/build_legacy_priors.py`
produces the audited JSON inputs from the pinned CMaNGOS dump;
`tools/gold/priors/build_farm_prior_package.py` produces the two Lua payloads.
