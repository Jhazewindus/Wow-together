# GOLD MODULE API V2

For players:
- Let Gold search nearby gathering areas and legacy creature farm priors, with estimates and measured session details.
- Restore the guide window with `/wt show`, `/wt glance`, or `/wt hud reset` after closing it.
- Record observed ore, herb, skinning and fishing yields with position and source.

Please check:
- In a separate addon namespace, search gathering facts and legacy creature priors and subscribe to gather observations.
- Close the guide window, then reopen it with each listed command; verify it is never resized or re-anchored during combat.
- In game, verify observer events, external GatherLite locations, prices, route guidance, and a plausible 20-minute actual rate.

Developer notes:
- Bump `GoldAPIVersion` to 2 and expose only validated wrappers on `WowTogetherModuleAPI`.
- Module loops retain their stops through refresh and time their OnUpdate callback. The owner receives a stop reason after declining guide replacement or accepting during combat.
- `FarmPriorSearch` lazily loads 6,118 creature/map records generated from the pinned CMaNGOS ClassicDB snapshot and QuestieDB Forever map bounds, including literal loot chance and minimum count. It omits negative loot-reference rows; each result says `legacy, unconfirmed`. `tools/import_vanilla_loot.py` remains a separate Wowhead drop-page parser used by the dungeon audit and does not generate these priors. The package includes the full GPL and CMaNGOS copyright notices.
- GatherMate2_Data (All Rights Reserved) and GatherLite's generated node/fish tables (no separate data license found) are not redistributed. The core can read mining/herbalism nodes through GatherLite's public instance methods when installed. Fishing pool and treasure seed locations remain open.
- The API loop-start callback fires only after activation; farm-session estimates and actuals carry separate basis text. Host tests and release-package validation passed. Everything changed still needs a WoW client play-test; no in-game verification is claimed.
