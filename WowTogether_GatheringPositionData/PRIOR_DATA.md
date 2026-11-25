# Gathering position data

Herb and ore node coordinates come from GatherMate2_Data's Forever data files at commit `29fe725eb9ab1c71d08025f47f94bb10043ed1cf`:

- `forever/HerbalismData.lua`, SHA-256 `dd2adc8bccc6aedf5e461fbe6bcde7330d841e102da9b5ffe16d2f9d5c957c9a`
- `forever/MiningData.lua`, SHA-256 `32875fd2c4856861045efcb75d025cfb7c11867bc499f4b2e4f4087906fe9c02`
- Project and credits: https://github.com/Nevcairiel/GatherMate2_Data

The project is marked All Rights Reserved and does not publish a redistribution licence. The repository owner has confirmed written permission for redistribution of these extracted coordinates. The importer copies numeric node IDs and coordinates only; it includes no upstream addon code.

Fishing-pool positions come from GatherLite's Forever data at commit `4ace5b625a1ee724ca912262509f641b4f35992a`, `plugins/database/data/forever.lua`, SHA-256 `6bca890f7dbb66117512f68ca4d09d6990bdf48a3d65dc37e302ed262c366f4d`. Project and credits: https://github.com/Wuild/GatherLite. The coordinate data is distributed under GPL-3.0-or-later as described by GatherLite's repository license; no GatherLite code is included.

All locations are marked `legacy, unconfirmed` and should be corrected by live
play observations.

The generated Lua package is 669,435 bytes on disk. Host Lua 5.1 tests observed
about 1.43 MiB of additional Lua heap after loading it; that is a host estimate,
not a measurement from the WoW client. The data is packed by zone and decoded
on access.
