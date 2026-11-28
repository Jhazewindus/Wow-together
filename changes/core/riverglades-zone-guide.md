# RIVERGLADES ZONE GUIDE

For players:
- Riverglades now has a faction-aware zone guide with its published quest list and available route points.
- Quest objectives without source-backed locations remain unmarked rather than guessed.

Please check:
- In game, open the Riverglades guide as Alliance and Horde characters and confirm the offered quest steps.
- Follow at least one quest chain and confirm the guide advances at the giver and turn-in.

Developer notes:
- Imported 175 quests from Warcraft DB Forever; the full zone index has 161 pickup points, 163 turn-ins, and 54 located objective sets. Another 63 objective sets still lack positions. Reconciled 10 Wowhead Forever Series chains; 32 pages remain unresolved and 49 were inaccessible.
- Used pinned QuestieDB literal position facts with the owner's permission; the audit records its commit and licensing note.
- The generated package grew by 241,487 bytes on latest main (12,814,124 to 13,055,611 bytes). Runtime heap growth was not measured.
- Host-side package generation and Python syntax compilation were completed. The game UI and route have not been tested in game; needs play-test.
