# GOLD MODULE API V2 AND FARM SUGGESTIONS

For players:
- See three nearby farm suggestions with price source and estimate assumptions; compare estimated and measured gold per hour.
- Start a suggested monster loop or a gathering loop learned from your own node observations.
- Restore the guide window with `/wt show`, `/wt glance`, or `/wt hud reset` after closing it.

Please check:
- In a separate addon namespace, search gathering facts and legacy creature priors; verify the observer reports position and yield.
- Check price selection, suggestion cards, route stops and arrow, and the session card in game.
- Follow a suggested farm for twenty minutes and compare the measured rate with the estimate; check window commands outside combat.

Developer notes:
- Bump `GoldAPIVersion` to 2 and expose only validated wrappers on `WowTogetherModuleAPI`. Gold uses `AuctionQuote`, `FarmPriorSearch`, `GatheringFarmSearch`, `RegisterGatheringObserver`, `StartModuleLoop`, `SetFarmSession`, and the session refresh request.
- Gold prices use a saved core auction quote when available, then vendor sell value; no TSM dependency. Suggestion estimates state chance, yield, price source, and assumed or observed pace. Measured yield samples take precedence over legacy values; legacy minimum counts are labeled as lower bounds.
- Module loops retain their stops through refresh and time their OnUpdate callback. The owner receives a stop reason after declining guide replacement or accepting during combat.
- `FarmPriorSearch` lazily loads 6,118 creature/map records generated from the pinned CMaNGOS ClassicDB snapshot and QuestieDB Forever map bounds, including literal loot chance and minimum count. It omits negative loot-reference rows; each result says `legacy, unconfirmed`. `tools/import_vanilla_loot.py` remains a separate Wowhead drop-page parser used by the dungeon audit and does not generate these priors. The package includes the full GPL and CMaNGOS copyright notices.
- GatherMate2_Data (All Rights Reserved) and GatherLite generated datasets (no separate data license found) are not redistributed. The core reads GatherLite mining, herbalism and fishing locations at runtime when installed. Zone-level legacy ore/herb yields are packaged; fishing-pool yields and treasure positions remain unavailable. Gathering routes use the player's learned positions.
- The loop-start callback fires only after activation; farm-session estimates and actuals carry separate basis text. No in-game verification is claimed; all changed flows and the twenty-minute plausibility check need a WoW client play-test.
