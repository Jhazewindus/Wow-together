# INSTANCES AND GOLD FARM TRACKER

For players:
- Browse dungeons and raids with entry requirements, chain progress, next steps and quests for a run.
- Track loot, coins, XP, farm estimates and top earners on the Gold page and tracker window.
- Start suggested routes manually, scan candidate prices at the auction house and review past sessions.

Please check:
- Open dungeon and raid pages, verify entry chains and quests, and start a quest route.
- Start a farm route, loot, gather, skin and fish; verify only your own loot is counted and the arrow follows the loop.
- Scan prices at an auction house and verify prices, ages, tracker values and session pauses.

Developer notes:
- Instances access and page modules show dungeon access requirements, relevant chain steps, quests and raid entries. The old viewer has not been removed in this change.
- GoldTracker adds an item, coin, XP and session tracker, price scan window, price revaluation, farm suggestions, activity timeout and session history. Gold page and tracker-window controls use the public module API.
- TrailLoop orders points by travel-distance estimates instead of calculating all pairwise paths synchronously. Legs are marked estimates; modules can request real pathing per leg.
- The overlay release notes list 19 instance-access tests, 43 tracker tests and 4 loop tests. They report no in-game verification; loot chat-line formats, uncached item information, auction scanning, entry chains and route-arrow behavior still need a WoW client check.
