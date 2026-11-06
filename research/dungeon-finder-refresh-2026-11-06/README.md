# Dungeon finder quest-list comparison — 2026-11-06

The current finder merges 23 captured Wowhead Forever dungeon category pages
with explicit quest rows from the four available Method.gg Forever dungeon
pages. The Wowhead categories contain 341 memberships; Method's lists add seven
City of Dalaran quests and one Hall of Thanes quest, producing 349 memberships.
No quest descriptions or website prose are copied.

## Confirmed additions

- City of Dalaran: 544, 545, 556, 557, 92432, 92434, 93680.
- Hall of Thanes: 98423, The Treaty of Understanding.
- Method's City of Dalaran, Wetlands, Hall of Thanes and Ruins of Lordaeron
  tables contain 15, 9, 5 and 9 quest IDs. Wetlands and Ruins have no
  supplemental IDs beyond the current Wowhead lists.
- The Hall prerequisite Underground Map (96391) is already linked to Old
  Ironforge Incursion (96393) in QuestieDB-derived dependencies and routed before
  its pickup. It is a prerequisite, not a dungeon membership row.

## Captured sources

- Wowhead overview:
  https://www.wowhead.com/forever/guide/dungeons-overview-locations-details
  SHA-256 `67019143ecd9a025233f87f39b7f8d002798629ea86df03aab719c761df29a83`.
- Method index: https://www.method.gg/wow-forever/dungeons
  SHA-256 `3c572a7101fa28b93c9b41cf4157aa16e50454a16f5764befef04c74056b6151`.
- City of Dalaran:
  https://www.method.gg/wow-forever/dungeons/city-of-dalaran
  SHA-256 `b9ec8fefb9ac276ab79bc0cacce52b5022c3e23240d0f169de0e3832c0fb9df0`.
- Hall of Thanes:
  https://www.method.gg/wow-forever/dungeons/hall-of-thanes
  SHA-256 `c2b343eb381128e887c37de8424d0ead5394cc2f2a8b07266bcaf669ea1748f5`.
- Ruins of Lordaeron:
  https://www.method.gg/wow-forever/dungeons/ruins-of-lordaeron
  SHA-256 `7d41b2b0833e4d17b2f2f2a6a4f5282287ab67502503b0b4d96782283c11e714d1b1`.
- Excavation Site: Wetlands:
  https://www.method.gg/wow-forever/dungeons/excavation-site-wetlands
  SHA-256 `9444c07118b03eff5a946b46ccfafb6b152483a5b64a387185ef143b63fbd1a4`.

Method's index lists all nine newer dungeons, but the other five currently have
no dedicated guide pages. Wowhead's overview chart levels are retained where
Method guide levels differ; this remains a source discrepancy, not a change to
pickup requirements. No category rows are invented for the five dungeons.
