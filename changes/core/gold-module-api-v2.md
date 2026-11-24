# GOLD MODULE API V2

For players:
- Let Gold search gathering zones for Mining, Herbalism, Skinning and Fishing, and show its session card on Play.
- Keep farm loop stops after refresh, lead the guide arrow around the loop, and report when a requested loop cannot start.
- Record confirmed gathering and fishing yields with the player's real map position; no node coordinates or NPC farm priors are included.

Please check:
- In a separate addon namespace, search gathering facts and subscribe to gathered item observations.
- Refresh while a module farm loop is active; confirm its stops and guide arrow remain visible.
- Verify the session card appears on Play and confirms both estimated and measured rates.

Developer notes:
- Bump `GoldAPIVersion` to 2 and expose only validated wrappers on `WowTogetherModuleAPI`.
- Module loops retain their stops through refresh and time their OnUpdate callback. The owner receives a stop reason after declining guide replacement or accepting during combat.
- `GatheringFarmSearch` returns only learnable nodes/water tiers that meet current skill, faction and zone-level filters, with zone map IDs and provenance. The observer reports local loot-confirmed item quantities and positions; coordinates are learned from play.
- Farm-prior search is clock-budgeted at approximately 2 ms per slice. No validated current-game NPC spawn/loot prior dataset is packaged, so the API returns an immediate unavailable reason. Legacy extracts are reference-only and are not routable.
- Host tests passed; all changed in-game flows still need play-test. No client verification is claimed.
