# GOLD FARM ROUTES AND MARKET TOOLS

## For players

- Keep farm sessions through reloads, compare learned rates with estimates, and route from known and observed gathering spots.
- Scan the full auction house and use TradeSkillMaster or Auctionator prices when available.
- Route fishing schools by kind, and use zone-specific fishing yield estimates with clear partial-coverage notes.

## Please check

- Stop and reload a farm session, then confirm it returns under Past sessions and in suggestions.
- At the auction house, scan everything, verify market price sources, and close a second scan early to check that collected prices remain.
- In game, start fishing, herb, ore, and creature farms; check route loops and the optional data state.

## Developer notes

- Add persistent Gold sessions, activity/zone breakdowns, measured farming rates, full auction-house browse scanning, and optional TradeSkillMaster/Auctionator price sources.
- Keep fishing pool positions keyed by kind and map; aggregate and deduplicate for generic zone routes. Do not import retail FishData into Forever.
- Load creature spawn coordinates from one optional addon with per-zone files. Legacy source coverage and pricing remain unconfirmed and must be presented as estimates.
