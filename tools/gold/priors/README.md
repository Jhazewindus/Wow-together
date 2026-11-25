# Legacy farm priors

`build_legacy_priors.py` converts selected numeric/name fields from the pinned
CMaNGOS classic-db SQL snapshot into JSON. The source pins, permitted columns,
Questie change-list hashes, and copyright notice are recorded in
`source_manifest.json` and repeated in each generated file's provenance.

Run from the repository root with local source files:

```sh
python3 tools/gold/priors/build_legacy_priors.py \
  --snapshot /path/to/ClassicDB_1_12_1_z2815.sql.gz \
  --questie-root /path/to/QuestieDB
```

The script verifies the CMaNGOS snapshot checksum and the two pinned Questie
fix-list checksums. Questie is read only to collect top-level NPC/item ID keys;
those IDs set `changed` booleans and no other Questie values are copied. NPC
and object spawn coordinates use the source's world-coordinate system. Spawn
time values are minimum/maximum seconds from the snapshot schema, not an
observed Forever respawn guarantee. Loot `minCountOrReference` can be a
negative reference entry and must not be treated as a literal item count.

The JSON outputs are audit inputs. `build_farm_prior_package.py --geometry
/path/to/conversion.json` produces the separate `WowTogether_GoldData` load-on-
demand package: one majority-spawn-zone record per NPC with the NPC ID, name,
level range, up to 24 converted legacy positions, supported literal loot rows,
and any skinning eligibility/yields from `SkinningLootId` and
`skinning_loot_template`. Border creatures are assigned to the map containing
the most converted points; ties use the smaller map ID. Reference
loot links (`minCountOrReference < 0`) are omitted because they cannot safely
be treated as item counts. Coordinates are transformed using the pinned
Forever 1.60.1.69893 map bounds. The game resolves the map name from its own
map API. These records are marked `legacy, unconfirmed`: they do not establish
that an NPC, object, loot row, or respawn timer exists in current Forever.
Play observations must correct them. Respect the GPL-3.0 attribution and
complete notice in `LEGACY_DATA_COPYRIGHT.md` and `LEGACY_DATA_LICENSE.txt`.

The package also includes zone-keyed gathering loot priors for named legacy
veins, deposits, herbs, and fish catches. Fishing rows come from
`fishing_loot_template` by area ID; direct references are expanded from
`reference_loot_template`, and non-fish rows are omitted. Every yield includes
its recorded chance and minimum quantity. These are legacy, unconfirmed
reference values, not measured Forever rates.

The separate `WowTogether_GatheringPositionData` load-on-demand package ships
herb/ore coordinates from GatherMate2_Data and fishing-pool positions from
GatherLite. The source revisions, checksums, licence and credits, and the
owner's written redistribution permission for GatherMate2_Data are recorded
in that package's `PRIOR_DATA.md`. GatherLite's public API is also read at
runtime when installed. The position package is 669,435 bytes on disk; its
packed table is decoded lazily by zone when accessed.

`tools/import_vanilla_loot.py` is a separate Wowhead drop-page parser used by
the dungeon-loot audit. It has no output pipeline and does not produce these
priors. QuestieDB contributes only pinned NPC/item ID membership flags to the
JSON audit inputs; its other facts are not copied.
