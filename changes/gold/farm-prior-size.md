# Slim Gold farm priors

For players:
- Filter legacy creature and skinning loot below 0.5% chance from estimates.
- Load creature spawn coordinates only for the zone when starting a farm.

Please check:
- Confirm the installed `WowTogether_GoldSpawnData_<mapID>` addon folders are enabled if farm routes are unavailable.
- Use `/wt probe` and `/wt memory` after searching and starting a farm to inspect optional data state and memory.

Developer notes:
- Keep the cross-zone farm search on a slim index; use the zone package only to construct a route. Host Lua 5.1 measurement: 2.18 MiB after index load and 2.45 MiB after full-level farm search. Disk payloads total 3,051,971 bytes including all spawn packages and gathering data. No in-game measurements are available yet.
