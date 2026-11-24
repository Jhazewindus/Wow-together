# GOLD FARM SUGGESTIONS

For players:
- See the three best nearby farm suggestions with the source and assumptions behind each estimate.
- Start a monster loop or learned gathering loop manually, then compare estimated gold per hour with measured loot.
- Prices use a saved core auction quote when available, otherwise the vendor sell value.

Please check:
- Check the Play page estimates, route stops, arrow guidance, and session card with a character that has auction quotes and vendor prices.
- Confirm replacing an active guide still asks first and that refusing leaves the current guide running.
- Follow one suggested farm for twenty minutes and compare the measured rate with the estimate.

Developer notes:
- Gold uses only the public WowTogetherModuleAPI: `AuctionQuote`, `FarmPriorSearch`, `GatheringFarmSearch`, `RegisterGatheringObserver`, `StartModuleLoop`, `SetFarmSession`, and the session refresh request.
- The price calculation uses auction quote before vendor fallback; it does not use TSM. Estimates state loot chance/yield, price source, kills or harvests per hour, and whether pace is assumed or observed.
- Host tests and Lua syntax checks pass. No in-game flow or 20-minute plausibility test is claimed; those still need a WoW client.
