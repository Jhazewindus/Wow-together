# Dungeon prerequisite route evidence — 2026-11-06

This note records the public facts used by the dungeon preparation route. It
contains IDs, locations at the entrance level, and source references only; no
website prose, artwork, layout, or map was copied into the addon.

## Stockade chain: 373 → 389 → 391

- Wowhead Forever's quest page for [The Unsent Letter (373)](https://www.wowhead.com/forever/quest=373)
  lists the sequence **373 → 389 → 391**. Captured HTML SHA-256:
  `7a114eddb8274b0fd00249ab81ea221272faf7109f6db0926332c0de338d4999`.
- The [item page for An Unsent Letter (2874)](https://www.wowhead.com/forever/item=2874)
  identifies Edwin VanCleef as its source. Captured HTML SHA-256:
  `1bbd0da2ac3da9b79cda98eab94c6af7c0f745fb25047314b701785ae4d0862c`.
- The [Edwin VanCleef page (639)](https://www.wowhead.com/forever/npc=639)
  identifies him as the Deadmines encounter; the NPC's Forever instance area
  has no usable coordinates. Captured HTML SHA-256:
  `ee064aa797c3cf144bd4468433f37a04db66f496dc015ae3012c93b0269583ea`.
- QuestieDB Forever at commit
  [`21be34023b72cf2ec3027cb9a61a8b72a1910857`](https://github.com/Questie/QuestieDB/tree/21be34023b72cf2ec3027cb9a61a8b72a1910857)
  records item 2874 as a starter for quest 373, Baros Alexston (1646) as the
  turn-in, and quest 389 as the continuation. It records 389 → 391, with
  Warden Thelwater (1719) as the Stockade quest giver.

The addon therefore uses the published Deadmines entrance as a travel anchor,
labels the item/boss task, and returns to the mapped Baros location. It does
not invent a boss coordinate inside the instance.

## Cross-instance quest work with missing interior NPC pins

- [Going, Going, Guano! (1109)](https://www.wowhead.com/forever/quest=1109) is
  the recorded prerequisite for [Hearts of Zeal (1113)](https://www.wowhead.com/forever/quest=1113).
  QuestieDB also records 1109 → 1113. The route places the Razorfen Kraul
  entrance between the known pickup and turn-in, before the later Scarlet
  Monastery pickup.
- QuestieDB Forever records [Dead Man's Plea (8945)](https://www.wowhead.com/forever/quest=8945)
  → [Proof of Life (8946)](https://www.wowhead.com/forever/quest=8946)
  → [Anthion's Strange Request (8947)](https://www.wowhead.com/forever/quest=8947).
  The start/return NPC facts include Ysida Harmon (16031) and Anthion Harmon
  (16016), but Ysida's Stratholme interior coordinate is absent. The route uses
  the Stratholme entrance as a transparent checklist anchor, then keeps the
  known Anthion return before the next mapped pickup.
- For [Lorax's Tale (5126)](https://www.wowhead.com/forever/quest=5126), the
  quest giver is mapped, but the addon has no confirmed offer for every
  character. The route explicitly asks the player to check Lorax rather than
  silently treating an unverified condition as satisfied.

Captured Wowhead pages for quests 5126 and 5127 have SHA-256 values
`886bfc0518cdfd38fbfb99683d24a300ba88adaf92ef5de45430b1591bf33d67` and
`1737d6863c662703f818ff6ea1eb0b571190ceb4df8db593e81111d79dcf9b1a`.
