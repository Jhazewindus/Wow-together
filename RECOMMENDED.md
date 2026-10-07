# Recommended home

Opening WoW Together from its minimap button or `/wt` starts on **Recommended**.
The screen offers a next adventure; it never starts or replaces a guide without
a click. The other browsers remain available from the main dropdown.

- **Leveling:** one suitable, unfinished zone section from the existing zone
  ranking. Its selection checks level value, useful prerequisite exceptions,
  faction/class/race, class-quest settings, skipped/completed quests and mapped
  starts. Current-zone preference and the lowest synced party level remain in
  effect when party features are enabled. The card explains its fit and shows
  progress for the character-compatible, non-skipped quests in that section.
  It does not claim that a quest giver has confirmed every pickup. **Quest list**
  previews the existing guide order; **Start guide** uses the existing consent
  and guide-start flow.
- **Professions:** cards for known Alchemy, Blacksmithing, Enchanting, Engineering,
  Leatherworking or Tailoring. Skill, rank cap, saved goal, live recipe information
  and materials feed the existing crafting planner. Missing recipe knowledge asks
  for the crafting window rather than inventing a batch. Reached goals offer the
  profession viewer so the player can choose a later goal.
- **Continue:** returns to the shared guide window for an active, unfinished
  guide. An active crafting card uses its actual remaining batch rather than
  constructing a replacement. A recommended new guide is optional.

Saved browsing searches and level brackets are deliberately independent of the
home screen. Unknown character context, no suitable zone or no known crafting
profession has an honest empty state. At level 60 the leveling area directs the
player towards other activities.

Quest and profession events invalidate cached recommendations. Opening the home
screen rereads public profession skills. Resizing changes only card geometry;
it cannot rebuild a route or query recipes. The cache retains cards, not a
per-pass quest query or its party snapshots. Provider failures do not suppress
other recommendation types. Only known professions unpack their detailed facts.

`RegisterRecommendationProvider(key, function(query) ... end)` allows future
activity types to return cards. The UI already supports additional categories,
but this release contains only leveling and crafting recommendations. It does
not add daily, mount-run or gathering guides, a new route planner or a claim of
globally optimal routes.

Host checks cover selection, progress, buttons, cache invalidation, profession
updates and resizing. Native rendering, icons and beta event delivery still need
the live checklist in TESTING.md. Published previews use real layout code with
example characters and approximated fonts/icons.
