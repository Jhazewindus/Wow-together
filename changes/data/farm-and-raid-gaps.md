# Farm data coverage

For players

- Farm estimates now use zone-specific fish drops, seeded herb, ore, and fishing-pool locations, and creature skinning yields when Skinning is learned.
- Border creatures appear in the zone with the most seeded spawns.

Please check

- Compare suggested gathering spots and creature drops with your live play and report corrections.
- Hover a skinnable creature farm and confirm its leather yields appear in the item breakdown.

Developer notes

- Added credited, source-pinned GatheringPositionData and zone-keyed fish loot. Creature records now combine skinning loot and are assigned to one majority-spawn zone. Rare loot pruning and the slim index / on-demand spawn layer will follow separately.
- Host tests only; no live-game verification was performed.
