# Brief: Public farm scan and Gold function hooks

## Why
The optional Gold module needs paced public auction quotes and three controlled ways to contribute data to core UI and price handling. It must not reach into private core state or replace core functions.

## What changes
- Add `WowTogetherModuleAPI.StartFarmCandidateScan(itemIDs, onQuote) -> accepted, reason`. Validate and bound item IDs, share the existing auction-scan pacing and cancellation rules, and invoke `onQuote` exactly once per requested item with `{itemID, minBuyout, median, count, time, complete}`. Accepted scans report every remaining item when canceled by auction-house close/browse, manual stop, or busy timeout, using `{itemID, minBuyout=nil, median=nil, count=0, time=nil, complete=false}`. Failed item requests use the same empty row even if an earlier page returned partial results. Normal completion at the three-page limit returns the observed partial quote with `complete=false`. `count` is the number of item units represented in the saved offer book; `median` is its quantity-weighted unit-price median. A stale cached quote is never reused; callback reentrancy cannot duplicate an item or start an overlapping scan.
- Add `WowTogetherModuleAPI.PublishGoldFunction(name, fn)` for exactly `Price`, `Suggestions`, and `SessionCard`. `Price(itemID, quantity)` may return a positive unit price and completeness flag; core falls back to its native quote when absent, invalid, or failing. `Suggestions()` returns up to five card records (`key`, `title`, `detail`, `priority`, and exactly one `action` function); core validates them and renders its own cards. `SessionCard(summary)` receives a copied, validated summary of the current guide session and may return one bounded card record (`title`, `detail`, and exactly one `action` function); core renders its own card. Route these through explicit `ns.hooks` call sites; preserve native behavior when a function is absent, invalid, or fails. Re-publishing a supported name replaces that name's previous callback. Keep `GoldAPIVersion == 1`.
- Specify and test callback inputs, output validation, replacement behavior, scan rejection, quote completion, and the unchanged pre-existing API keys.
- Bump the TOC and add the matching changelog entry.

## Files
`WowTogether/Core.lua`, `WowTogether/AuctionScan.lua`, `WowTogether/AuctionMarket.lua`, `WowTogether/Recommended.lua`, `WowTogether/RecommendedUI.lua`, `WowTogether/ModuleAPI.lua`, `tests/test_module_api.py`, `tests/test_0840.py`, `CHANGELOG.md`, `WowTogether/WowTogether.toc`, and this brief.

## Tests
Add host tests for valid/rejected scans, one callback per item, paced completion and auction quote shape; test all three published function hook points, invalid names/functions, protected errors, and that the public API version remains 1 with additive keys. Run Lua 5.1 syntax, the host suite, boundary check and release build.

## Acceptance
A module can request a bounded farm quote scan and publish the three named functions without assigning any core `ns.*` function. Existing auction guide scans and API registrations continue to work.
