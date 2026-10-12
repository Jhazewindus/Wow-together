# Silithus guide data review — 2026-10-10

Scope: `level-zone:kalimdor/silithus`, chapter 51–60. The repository audit was regenerated from branch `guides/coverage` at `1528d8c` immediately before data changes. Chapters describe the addon’s existing guide scope; they do not certify gameplay minimums or optimal routing.

## Changes

- Confirmed the provided delivery items for A Terrible Purpose (8287), Unraveling the Mystery (8314), and Secrets of the Colossus (8857–8859). These keep their turn-in token but no longer send players to farm it.
- Added item-source alternatives for Encrypted Twilight Text (20404), Abyssal Crest (20513), and Abyssal Signet (20514), using the item pages for loot relations and linked NPC pages for Silithus locations. Where NPC pages were denied, the previous quest-page location is preserved and identified in `source-facts.json`.
- Kept only the unmapped Regal rubbing target (20456 / object 180453) unresolved for Glyph Chasing. The object page has no locations and its item page has no published source relation.
- Kept the Large Brilliant Shard (14344) requirement for Dukes of the Council (8332) and Lords of the Council (8341) unresolved. No local source relation is published; no farm target is invented.
- Classified A Humble Offering (9248) as Elite from the linked Abyssal Scepter sources and NPC classification facts. The existing group warning and player Skip choice now apply; unresolved objective semantics and offer conditions remain flagged.
- Excluded Ahn’Qiraj raid / class-set / war-effort turn-ins and the Scarab Gong event path from ordinary leveling. Their catalogue records, class/faction facts, dependencies, and source gaps remain intact. Repeatable faction systems remain outside the leveling route under existing guide behavior. Existing fixed order and automatic progress are unchanged.

## Coverage and flow

The refreshed route audit compares before and after data. Alliance chapter coverage moves from 80 selected quest IDs, 323 actions, and 88 unknown-location steps to 44 quest IDs, 145 actions, and 3 unknown-location steps. Horde moves from 80 IDs, 326 actions, and 91 unknown-location steps to 43 IDs, 142 actions, and 3 unknown-location steps. The action reduction is the intentional removal of raid/event content plus correction of supplied-item objective semantics; this is not a claim that the excluded content has complete source mapping.

For route economics, `flow-matched-scope.json` replays the post-correction data with the 41 newly excluded IDs temporarily made eligible, so it compares the same 80 quest IDs per faction. Estimated distance rises by about 3,659 Horde map-units (1.2%) and 2,082 Alliance map-units (0.8%); quest-log peak and XP shortfall are unchanged. Estimated reward XP available before objective work increases by 1,078,210 Horde and 1,110,710 Alliance; uncertain travel legs decrease by 8 and 7 respectively. Distance is a host estimate, not measured play time. This evidence-driven change reflects corrected mapped visit stages and does not modify shared routing code or fixed order.

With endgame content excluded, the complete selected ordinary guide evaluates at 43 Horde quests / 142 actions and 44 Alliance quests / 145 actions. Remaining objective-location gaps are 8309, 8332, and 8341 for both factions. Remaining unverified offer conditions are Horde 1000, 1004, 1018, 8331, 8332, 8341, 8343, 8348, 8349, 9248 and Alliance 1015, 1019, 1047, 8331, 8332, 8341, 8343, 8348, 8349, 9248. Keep these pickup conditions unverified until a source or beta offer confirms them.

Source hashes and exact IDs are in `source-facts.json`. The complete before/after audit and flow outputs are retained alongside it. The scoped source audit still reports gaps by design; do not infer a complete map or safe terrain routes.

## Host validation

Focused tests cover provided-item hand-ins, all captured item alternatives, unresolved Regal/shard objectives, exclusion of endgame/event IDs, retained optional Elite quests, and quest-type correction guards. Lua is loaded by the pinned Lupa Lua 5.1 addon harness using interface 16001 source. Host checks cannot establish beta offer conditions, event triggers, live loot, UI waypoint behavior, safe terrain paths, or actual native map positions.

## Player checklist

1. Fresh Horde and Alliance characters who enter Silithus in this guide range: verify the guide covers the full selected leveling flow and does not offer raid, class-set, war-effort, or Scarab Gong event turn-ins.
2. Mid-zone characters with accepted, completed, and manually skipped work: verify fixed order and automatic progress after objective updates, hand-ins, `/reload`, leaving/re-entering Silithus, and Scan guide.
3. Verify the tablet, prism, and Colossus husk items are hand-in tokens; no step asks you to farm them. Check the cross-zone Colossus hand-ins arrive at the mapped NPC.
4. In a party, test optional Elite warnings and Skip choice for 8306, 8309, 8314, 8332, 8341, and 9248. Confirm ordinary quests are unaffected by Include class quests.
5. Record real offers and objective areas for remaining unknown pickups, Regal crystal, shard source, Natalia event behavior, and world-boss quest 9248. Report faction, race, class, level, client build, accepted/completed state, and coordinates.
6. Confirm unfinished accepted or temporarily unavailable work does not make the guide report complete. A native beta checklist is still required; these host checks cannot establish in-game behavior.
