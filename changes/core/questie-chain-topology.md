# QUEST CHAIN DATA REFRESH

For players:
- Dungeon and outdoor quest guides now recognize 38 additional verified chain predecessors.
- Class quest chains also use the confirmed order, helping the guide avoid presenting later quests too early.
- Unknown and branching prerequisites remain unverified.

Please check:
- In-game, follow the Kroldok Stronghold preparation chain and confirm its three new prerequisite links.
- Check the updated outdoor and class chains with a character eligible for those quests.

Developer notes:
- Used the latest QuestieDB snapshot to identify candidates, then imported only linear immediate predecessors confirmed by captured Wowhead Forever Series pages with title identity checks and page hashes.
- The 38 imported links cover 31 class quests, 4 outdoor quests, and 3 Kroldok Stronghold quests. Captured 204 unique candidate quest pages; branching, conflicting, already represented, and other dungeon facts were left unchanged.
- Needs in-game play-test before merge.
