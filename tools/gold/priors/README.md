# Reference-only legacy priors

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

These are non-routable, reference-only priors. In particular, they do not
establish that an NPC, object, loot row, or respawn timer exists in current
Forever. Respect the GPL-3.0 attribution and the complete notice embedded in
each JSON output and in `LEGACY_DATA_COPYRIGHT.md`.
