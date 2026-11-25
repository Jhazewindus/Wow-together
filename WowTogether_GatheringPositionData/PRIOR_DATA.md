# Gathering position data

Herb and ore node coordinates come from GatherMate2_Data's Forever data files at commit `29fe725eb9ab1c71d08025f47f94bb10043ed1cf`:

- `forever/HerbalismData.lua`, SHA-256 `dd2adc8bccc6aedf5e461fbe6bcde7330d841e102da9b5ffe16d2f9d5c957c9a`
- `forever/MiningData.lua`, SHA-256 `32875fd2c4856861045efcb75d025cfb7c11867bc499f4b2e4f4087906fe9c02`
- Project and credits: https://github.com/Nevcairiel/GatherMate2_Data

The project is marked All Rights Reserved and does not publish a redistribution licence. The repository owner has confirmed written permission for redistribution of these extracted coordinates. The importer copies numeric node IDs and coordinates only; it includes no upstream addon code.

Fishing-pool positions come from GatherLite's Forever data at commit `4ace5b625a1ee724ca912262509f641b4f35992a`, `plugins/database/data/forever.lua`, SHA-256 `6bca890f7dbb66117512f68ca4d09d6990bdf48a3d65dc37e302ed262c366f4d`. Project and credits: https://github.com/Wuild/GatherLite. The coordinate data is distributed under GPL-3.0-or-later as described by GatherLite's repository license; no GatherLite code is included.

GatherLite's file stores numeric object IDs, map IDs, and normalized coordinate
arrays; it contains no written pool-kind labels. The importer maps the four
present fishing IDs to separate keys and node names: 180655 Floating Debris,
180656 Sagefish School, 180685 Floating Wreckage, and 180750 Oily Blackmouth
School. The kinds are mapped from the object IDs; those labels are not written
in GatherLite’s Lua file. Wowhead's Forever object pages identify the first
four kinds but mark their locations unknown:
https://www.wowhead.com/forever/object=180655/floating-debris,
https://www.wowhead.com/forever/object=180656/sagefish-school,
https://www.wowhead.com/forever/object=180685/floating-wreckage, and
https://www.wowhead.com/forever/object=180750/oily-blackmouth-school. Its
Watertight Trunk item page
shows catch-location counts and that multiple kinds can yield the same item;
it does not publish pool coordinates:
https://www.wowhead.com/forever/item=21113/watertight-trunk

The pinned file contains 539 coordinates for these four kinds across 38
kind-and-zone records. Object ID 180902 also occurs in the source, but is
excluded because its pool kind has not been verified. The retail
GatherMate2_Data FishData.lua is not used: the pinned upstream Forever tree has
no Forever fishing data file. The checked master TOC lists only Forever
herbalism and mining files: https://raw.githubusercontent.com/Nevcairiel/GatherMate2_Data/master/GatherMate2_Data.toc

All locations are marked `legacy, unconfirmed` and should be corrected by live
play observations.

The generated Lua package is 681,918 bytes on disk. Host Lua 5.1 tests observed
about 1.43 MiB of additional Lua heap after loading it; that is a host estimate,
not a measurement from the WoW client. The data is packed by zone and decoded
on access.
