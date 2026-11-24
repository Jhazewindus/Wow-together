# GOLD MODULE API V2

For players:
- Let Gold read saved auction quotes and show farm session estimates beside measured gold per hour.
- Start a farm loop from a module and confirm before it replaces an active guide.
- Search current-game farm priors when that data is available.

Please check:
- Use a separate addon namespace to read a quote, search priors, start and stop a loop, and refresh the session card.
- Confirm a running guide stays active until the player accepts replacing it.
- In game, start a loop and follow its arrow back around to the first point.

Developer notes:
- Bump `GoldAPIVersion` to 2 and expose only validated wrappers on `WowTogetherModuleAPI`.
- A loop supplies an `onStop(reason)` callback so its owning module hears why the route ended.
- Farm-prior search is clock-budgeted at approximately 2 ms per slice. The current packaged core has no validated current-game farm-prior dataset, so the API returns an immediate unavailable reason; the existing legacy prior extracts are reference-only and are not routable.
- Needs play-test. Host tests do not verify actual client map/arrow behavior.
