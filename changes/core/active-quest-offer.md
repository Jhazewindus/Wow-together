# Active quest offer check

## For players
- Keep following a quest after accepting it, even when an earlier NPC scan recorded no pickup offer.

## Please check
- Accept a Drowned City quest, then scan or reopen the dungeon quest route.
- Confirm the accepted quest is not reported as unavailable from its quest giver.

## Developer notes
- Active quest-log state now takes precedence over pickup-only offer evidence.
- Host tests cover accepted and unaccepted quest behavior. Needs in-game play-test.
