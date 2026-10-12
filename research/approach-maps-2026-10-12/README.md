# Live dungeon approach maps — 12 October 2026

Seven supported outdoor approaches use original client minimap textures and live public map coordinates: Wailing Caverns, Deadmines, Blackfathom Deeps, Gnomeregan, Scarlet Monastery, Razorfen Downs and Uldaman. The client itself supplies every texture; WoW Together ships geometry and file references, no copied map artwork.

Six cave layouts are reconstructed from Blizzard Classic build 1.15.9.70003 WMO group bounds, ADT placements, and the `World/Minimaps/WMO` block files. File IDs, paths, dimensions, SHA-256 hashes, placements and group bounds are captured in `source-facts.json`. Razorfen Downs uses the original outdoor minimap tiles and the 64×64 world tile grid. Entrance markers reuse the addon's already-published Forever dungeon entrance records.

The map opens automatically while the player position falls within a supported approach footprint. The live marker uses `C_Map.GetPlayerMapPosition` and `C_Map.GetWorldPosFromMapPos`; leaving the footprint closes the map. Opening an approach from a dungeon journal works anywhere, but the player marker appears only when public coordinates fall on that map. Entering a matching instance while its automatic approach map is open hands off to the existing static dungeon map.

This is an outdoor approach feature. It does not infer a player's floor or position inside a dungeon. Host geometry checks cannot confirm that a given Forever beta build exposes every referenced client texture or coordinate conversion; testers should check each approach map on the client.
