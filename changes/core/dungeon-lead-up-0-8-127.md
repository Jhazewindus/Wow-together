# Dungeon lead-up routes

## For players
- Start the quests that lead to a dungeon even when its own quests open at a higher level.
- See why a route cannot start and the level when those quests open.
- The addon can learn a missing dungeon entrance when you walk in.

## Please check
- At level 36, open Krol'dok Stronghold and start the lead-up route; check that it names level 38.
- Enter a dungeon without a known entrance, then check its route to the learned door.
- Export `/wt research` after an entrance is learned and confirm the `dungeon-entrance` event appears without character information.

## Developer notes
- Preserves published entrances and the first personal route anchor; stores new observations by client build and instance key.
- The supplied 0.8.127 audit records the remaining dungeon quest-list, pickup-position, and entrance gaps.
- Host tests are pending. The game route and automatic entrance capture need play-testing.
