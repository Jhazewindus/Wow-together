# Wow Together — friend test script

For **0.8.21**, World of Warcraft: Forever beta, interface **16001**.
Allow **45–60 minutes**. Each tester reports Pass / Fail / Skip with a reason.
Keep tester names and reports separate; label the main developer's report.
The expanded-guide checks below take about **15–25 minutes**.
## Install and capture context

1. Replace the complete WowTogether folder, including **all 54 Lua files** and
   the **Media folder**, in
   `World of Warcraft\_classic_beta_\Interface\AddOns\WowTogether\`.
   `/reload`; restart fully if a new addon folder does not appear.
2. Enable `/console scriptErrors 1`. Record version, build, level, faction, class,
   race, zone, party size and relevant settings. Update every party member.
3. Leave **Follow fixed zone guides**, **Record NPC offers and quest progression**
   and **Use observed prerequisite patterns** on. Source names in exports are
   optional and off by default. Recording never uploads automatically.

## Optional class training — about 10 minutes

1. Enable **Leveling guides → Include convenient class training**. At an even
   level, approach a friendly trainer for your class while doing a nearby pickup /
   turn-in or leaving a hub for distant quest work. Expect **Optional class
   training**, the trainer destination and a **T** map marker. No long detour or
   interruption of nearby killing/gathering should occur. Locations are published
   estimates; report incorrect NPCs, faction or training caps with map coordinates.
2. Train yourself and click **Done training**. Expect the same quest sequence to
   resume, with no quest completed or skipped. At another reminder, use **Skip
   training**: only this character's training check is postponed. Neither choice
   should change a friend's route or buy a skill. An even level does not guarantee
   that this trainer offers a new skill; the instruction is to check.
3. `/reload` during a pending visit, then again after Done/Skip. The pending visit
   or saved choice should survive. The next odd level should not repeat a completed
   check; the next even level makes another check due when a trainer is convenient.
   Switching guides must not drag the old guide's trainer visit into the new one.
4. Turn the training setting off/on. Quests should resume immediately when off;
   turning it back on can restore a pending visit. **Include class quests** is
   independent. Test another class/faction and a trainer across a city-map boundary
   if nearby; missing/private positions or ownership should not invent a visit.
5. Show only the standalone arrow. During training its compact **Done / Skip**
   buttons should work; they disappear for ordinary quest steps. With both panels
   shown, use the guide controls instead. Full-route map previews keep the original
   quests and their numbers, adding T for the active service visit only.
6. Check an NPC confirmation, flight, corpse run, scan and combat. These must not
   create a new training detour; death/flight must retain a previously pending
   visit. Capture errors and `/wt probe` Class training / Training stop lines.

## Enemy settlements and travel lines — about 10 minutes

1. On Horde, follow an Ashenvale step whose direct map line crosses Astranaar.
   The crossing ground segment should not draw. Existing quest markers and your
   selected guide's order/progress/skips must remain. Zoom/pan, change zones,
   Scan and /reload; capture errors and `/wt probe` Travel leg/goal lines.
2. When existing published connections permit a bypass, expect travel waypoints
   through those connections. When none is mapped, expect **Route around
   Astranaar (Alliance)** and an explanation to follow roads around the town;
   no straight direction arrow should point through it. Manually go around:
   normal directions should return after the crossing is no longer ahead.
3. Test Alliance visiting Astranaar, and Alliance near a Horde settlement.
   Own-faction and neutral hubs should remain usable. An intentional quest
   destination inside an enemy location must retain its quest work/marker;
   neither reaching a travel waypoint nor the caution grants quest completion.
4. Open a friendly flight master's map with a known reachable route. The graph
   and legacy flight fallback should still recommend useful friendly flights.
   An enemy flight point must not become usable from old cached data. Flying
   over an enemy town is allowed; ground approach/exit checks remain active.
5. Compare the highlighted area with actual guards and roads. Footprints bound
   published service/settlement locations with an **estimated 100-yard margin**;
   they are not measured guard ranges or a terrain mesh. Report missed crossings
   or overbroad suppression with faction, map coordinates, final quest, screenshot
   and `/wt probe`. Include the complete export if research data is relevant.

## Manual quest-item use — about 5 minutes

1. Start a guide with an accepted objective that has a native special quest item
   (for example, Lazy Peons' Foreman's Blackjack if the beta exposes it). Keep the
   main guide panel visible. Expect its icon/name and **Use item** button; quests
   without a special item should have no button. Tips/objective lists stay separate.
2. Select a valid target yourself and click outside combat. Check the native item
   effect, objective progress, cooldown/error messages and any addon-action failure.
   Waiting, moving, scanning, accepting or bag updates must never use the item.
3. Accept/remove another quest so log indices change, then click again. The correct
   item must still be used. Switch/skip the guide objective and check that its old
   item disappears. Cached/restricted/missing data must never use another quest item.
4. In combat the button is disabled; after combat it can be clicked again. It must
   not replay a blocked click automatically. Browsing earlier steps, flight, corpse
   travel and route loading should hide it. Capture `/wt probe` and native errors if
   `UseQuestLogSpecialItem` is missing, blocked, or behaves differently on this build.

## Mikmans' quest highlights and Mulgore pickups — about 10 minutes

1. With an accepted quest as the current objective or turn-in, open Blizzard's
   quest log/map. It should select that quest and show its native highlights.
   Skip or finish the step: the next accepted quest becomes selected. A future
   pickup you have not accepted cannot be selected in the log. The addon should
   not open the map itself or add a user waypoint pin. Check with arrow panels
   hidden too. Native highlights require the client to have quest-location data.
2. Toggle **Arrow and map → Highlight the current guide quest** off. Guide
   changes should stop selecting native quests; turn it on to follow again.
   While the guide's current quest stays unchanged, a manual log selection
   should not be repeatedly overwritten by movement/arrow updates.
3. Change/skip steps in combat. Native quest selection waits until combat ends
   and then uses the latest accepted current quest. Capture any Lua/protected-
   action error and the Native quest highlights/capability lines from /wt probe.
4. In Mulgore, confirm whether Baine Bloodhoof offers **The High Chieftain** and
   Brave Wildrunner offers **Our Ancient Enemy**. If absent, the guide must not
   require their pickup. Complete another quest, change reputation/level and
   /reload: they must remain pending rather than being recommended again merely
   because another event occurred. Do not use manual skips for this test.
5. Once an NPC actually offers a deferred quest, reopen the NPC. Its existing
   pickup/objective/turn-in stages should return in fixed guide order, without
   clearing your manual skips or granting completion. Test another unavailable
   quest outside Mulgore too; the retention logic applies across all guides.
6. An opened single-quest dialog proves that quest's offer only. It must not
   imply other quests at that NPC are absent. Accepted quests continue their
   work/turn-in steps even if they no longer appear in the NPC's available list.
7. Export before/after NPC observations with **/wt research** when either named
   quest unlocks. The supplied exports were truncated; save/copy the entire
   export including its final closing braces. Exact unlocks still need evidence.

## Report to Kadrak alternatives — about 5 minutes

1. Accept Report to Kadrak from Thork at the Crossroads, or from Darn Talongrip
   in Stonetalon. Follow a guide containing the other pickup: it should not ask
   you to collect the second version. The accepted quest must still send you
   to Kadrak. Test the reverse direction on another character if possible.
2. Turn in the chosen version. The unchosen pickup must stay excluded without
   pretending its quest ID is completed or saving a manual skip. /reload and
   Scan should preserve the chosen version's real progress and fixed order.
3. A separate chain quest with the same title must remain available unless an
   explicit alternative-ID relationship is documented. Only your own version
   blocks your alternative; it does not apply your choice to a party member.
4. If the pickup is still wrong, capture the current step, /wt probe and the
   quest ID from the native log. The supplied truncated export does not contain
   the reported Darn visit, so its exact active quest ID remains unconfirmed.

## Romits' travel and collection reports — about 10–15 minutes

1. Record your version/build, current guide/step, walking/mount speed and travel
   settings. Enable Suggest faster known flights; open Orgrimmar's flight master
   with Crossroads unlocked. Capture Flight paths, Flight unlock scan and Flight
   map read from `/wt probe` while the native map is open. A known route should
   use the flight if its estimated flight/approach beats walking. If it still
   suggests walking, include those lines and Travel leg/goal; unlock flags alone
   do not prove a reachable connection. Do not assume Joker's cache explanation.
2. Test Crossroads → Camp Taurajo. Before boarding, the description distinguishes
   flight time from whole-journey time, which includes walking. Enable standalone
   arrow: the countdown appears above it, matches the guide panel, and decreases
   during the ride. Untimed flights say Est. flight; after a completed ride,
   repeat and compare the personally timed estimate with real duration. If an
   estimate runs out early, elapsed time appears instead of a stuck zero timer.
3. Open the world map while flying. Selected quest markers remain; Show full
   route keeps its eligible previews. Ground lines stay hidden during the ride
   and resume after landing. Guide order and quest completion must not change.
4. Walk, then mount towards a waypoint. Distance units follow settings and the
   travel ETA should shorten with faster public running speed. These are next-
   waypoint estimates; terrain, waiting and stops can make the actual trip longer.
5. Use a cross-continent guide requiring a boat or zeppelin. At its transport
   step, confirm the instruction names the boarding place and coordinates,
   points to the departure location and keeps the correct destination direction.
6. With both arrow panels enabled, the large panel keeps instructions, progress
   and step controls, with no duplicate direction arrow. Toggle standalone off:
   the large arrow returns. Check Scan guide still shows its loading spinner.
7. On Ishamuhale, loot Fresh Zhevra Carcass while its collection step is current.
   It should advance to Ishamuhale's Fang after the bag update, without requiring
   Skip. The quest must remain incomplete. Test another item collection with a
   partial stack: only the requested count should finish that stage. Merely
   owning a use-item must not complete its use/kill objective.
8. A new settings profile should have Include class quests checked. A saved
   explicit off choice must stay off; other classes' quests remain excluded.

## Combined dungeon data for 0.8.17 — about 5–10 minutes

1. Open **Dungeon guides**. Check Ragefire Chasm, Wailing Caverns and a dungeon
   on the other continent. Cards should show dungeon run levels and the separate
   pickup level for your character's full quest set. There should be one card
   per dungeon complex, rather than Mage, Orgrimmar or duplicate Lordaeron cards.
2. Open **Quest list**. Check known pickup NPCs, entrance map/coordinates and
   Scarlet Monastery/Maraudon/Blackrock Spire wing ranges. Wrong-faction quests
   must stay excluded; class quests follow Include class quests. A run range
   must not permit a pickup whose own level/prerequisites are unmet.
3. Start a collection route. Current-zone pickups come first; a known entrance
   remains its final destination, including across zones. After accepting local
   pickups, the arrow should say Go to the dungeon entrance/entrance area.
   Reaching it must not grant quest completion. Distant pickups are still optional
   and shown as excluded detours, not claimed collected.
4. Published entrance areas should work without a native map link. Keep your
   prior manually recorded entrance if you have one. Public native links take
   precedence over published data. For a correction, stand outside the portal
   and use **Record entrance here** inside Quest list; verify it persists.
5. The Hall of Thanes, Ruins of Lordaeron, Excavation Site and City of Dalaran
   have published areas. The other five new dungeon entries must keep missing
   coordinates/quest sets explicit. No made-up map marker should appear.
6. Check published points on the beta and report any wrong map, cave approach
   or portal location with dungeon name, version/build, screenshot and `/wt probe`.
   The sources supply entrance areas; this release does not map dungeon interiors.

## Waypoint directions for 0.8.16 — about 3–5 minutes

Reports reviewed: Romits flagged `Head to Convergence C1413 540 266` as a
possible pathing issue; Mikmans reported the same text and requested waypoint
or place names, plus a strict -3/+3 start. No probe, final destination, version,
build or character context was available. The main developer's earlier choice
keeps explained useful prerequisite exceptions. The raw label is confirmed in
the travel snapshot; a bad terrain path is not yet established.

1. Keep SavedVariables, resume a guide and follow a cross-zone journey. An
   anonymous junction should read **Go to waypoint — Zone (x, y)**, including
   **The Barrens (54.0, 26.6)** if that particular point is on the journey.
   The map marker's tooltip should show the same text. Check another zone too.
2. Named city gates, docks, crossings and flight masters should retain their
   names. The context should say where the journey is headed. Reaching a travel
   waypoint advances directions without marking a quest picked up or completed.
3. Confirm Scan still uses -3/+3 for ordinary unfinished work. Any lower-level
   prerequisite must explain its useful unlock; ready hand-ins can remain.
   This update does not change that policy or create saved skips.
4. If an arrow or line crosses impassable terrain, capture `/wt probe` while the
   step is visible, plus the screenshot, current location and intended quest.
   **Travel leg / Travel goal** now record the exact connection and destination.
   Lines between travel points are estimates; follow roads and terrain.

## Scan guide regression for 0.8.15 — about 5–10 minutes

Reports reviewed: the unlabeled level-21 Barrens tester described level-16 work
and a short stutter after quest changes. Mikmans requested a strict -3/+3 start.
The main developer chose to keep useful prerequisite exceptions and explain
them clearly. The unnamed level-16 quest and old version/build were not supplied;
do not treat the example below as a confirmed diagnosis of that tester's route.

1. Keep SavedVariables and start/resume a fixed guide. Accept a planned quest,
   update a kill/item objective, abandon a quest if desired, and Scan. The arrow,
   objective counts and map should reflect the actual log/history without
   changing the compiled order. Ready hand-ins remain until turned in.
2. Repeat Scan with the main dashboard closed, then while resizing it. The
   guide panel must still advance. During Scan, expect the rotating loop and
   disabled scan button; once done, directions return. Progress changes during
   a larger scan should be reconsidered. Clearing/switching the guide cancels it.
3. At level 21, the normal work band is 18–24. Check any recommended level-16
   quest: the panel should label **Lower-level prerequisite** and name a useful
   unlock with its level or dungeon purpose. Harpy Lieutenants can qualify
   through level-20 Serena Bloodfeather; ordinary low-level Stolen Booty cannot.
   Apply the same check in another zone. Ready low-level returns can stay.
4. Check `/wt probe`: the leveling band, scan summary and personal-update counts
   should be present. Note any short freeze after a quest accept/completion,
   whether the dashboard was visible and which guide/step was active. Event
   batching is host-tested; report actual beta smoothness separately.
5. Temporarily unreadable quest logs should show waiting/retry status and retain
   the guide, rather than claiming completion. Scan retries briefly. If needed,
   retry after zone loading settles. With **Reconsider skips when scanning** on,
   only a successful scan clears selected-guide skips; a cancelled scan must not.
6. With **Suggest the next nearby zone** enabled, level until your selected guide
   has no useful work ready and a mapped adjacent zone has suitable pickups.
   Expect **Start zone guide / Keep my guide**. Keep preserves the guide and
   suppresses that repeated offer; Start selects the full next-zone guide.
   Current useful work or an unresolved NPC/location step must not be displaced.
   Higher-level, wrong-faction and remote zones must not be milestone suggestions.
7. Report first Lua error, version/build, character level, zone, guide, current
   quest/step, settings and `/wt probe`. Party transport is unchanged; this release
   focuses on the player's Scan guide, not shared party route synchronization.

## Guide background regression for 0.8.14 — about 2–3 minutes

1. Start/resume a guide. Click the small **BG** button at the top-right of its
   arrow/instruction panel: the opaque fill should become see-through. Click
   again for solid. Hover for help; check long guide titles do not overlap it.
   Instructions, arrow and buttons should remain fully visible in both modes.
2. Check Settings → Arrow and map → **Opaque guide background** reflects the
   button's state. Change the checkbox and check the panel immediately updates.
   Nearby-objective and travel/inn-tip panels should use the same background.
3. Leave it see-through, `/reload` and resume: the choice should persist. Change
   it while in combat and while Scan runs. Progress, guide order, skipped steps,
   map lines and flight directions should not change from this toggle.
4. If it clips or fades text, report version/build, UI scale and a screenshot.
   Host checks cover background-only styling, persistence, both controls and
   route isolation; actual beta appearance still needs this test.

## Reviewed Durotar research

The supplied export contains 23 observations across addon 0.8.8/0.8.12/0.8.13
on build 70235. Positive offers already match our starter NPC data. Its stale
quest history and changing lists do not justify a new prerequisite or coordinate.
Keep recording before/after NPC offers and export more sessions using `/wt research`
or Export guide findings. Label each tester separately; research is not uploaded
automatically. This review does not change leveling order or mapping coverage.

## Guide-completion regression for 0.8.13 — about 5–10 minutes

1. Update the complete folder while keeping SavedVariables. `/reload`, resume
   the affected zone guide and click **Scan guide**. Report the selected guide,
   version/build, level, faction/class/race, skips and `/wt probe`.
2. In Hillsbrad at level 24, unfinished **Battle of Hillsbrad** and **Elixir of
   Agony** level 28 are outside the 21–27 leveling band; this must not complete
   the guide. **Souvenirs of Death** level 25 should retain its unfinished work
   when included and unskipped. If still missing, send the probe, quest ID and
   skip settings; the earlier report did not identify that quest's skip state.
3. Finish the currently eligible work while later quests remain. Expect a
   paused explanation, preserved guide controls/order and nonzero unfinished
   quest counts, rather than “Guide complete.” Later-level work should return
   at a suitable level. Repeat on another zone guide. Unknown locations or
   prerequisite gates must keep their existing waiting instructions.
4. Skip all remaining quests/steps in a small guide: skips must not give quest
   completion credit or mark it complete. `/reload` must preserve those skips.
   Reset guide skips only when desired; this restores skips for this character
   across guides. Ready hand-ins remain until actually turned in.
5. When all enabled, applicable guide quests really are turned in, completion
   should appear. Disabled optional class work and incompatible quests do not
   block that check. Diagnostics should retain the fixed-guide summary and
   show zero unfinished quests. Enabling remaining own-class work can reopen it.
6. Hover the arrow while Scan or route generation runs. Keep the pointer there
   as work finishes: its tooltip must follow the current guide state and stop
   showing “Loading route.” Check party history/last-member behavior if available.
   Host checks validate logic, not native beta completion flags or rendering.

## Zone-themed card regression — about 3–5 minutes

1. Open Leveling guides and select All levels. Compare Durotar, Mulgore,
   Ashenvale, Tanaris and Winterspring where your faction permits browsing.
   Cards should show faint canyon, prairie, woodland, desert and snow scenery.
   The left text area, buttons, level label and gold borders must remain clear.
2. Browse a zone while standing somewhere else. Its artwork should match the
   guide, not your current zone. Path to Orgrimmar should show a settlement;
   dungeon collection cards should show subdued ruins.
3. Resize the dashboard narrow/wide and scroll its cards. Scenery should crop
   smoothly within each card without stretching, crossing its border or covering
   controls. Try your normal UI scale. Hover and click buttons as usual.
4. Switch between Leveling guides, All quests and ordinary party progress.
   Reused cards must not retain a previous guide's background on plain quest
   rows. Start, accept/turn in, Scan, skip and reload: guide order and progress
   should behave as before, without new chat/party messages from theming.
5. If artwork is blank or shows a placeholder, verify the complete Media folder
   was installed and restart the client fully. Send version/build, guide/zone,
   UI scale, screenshot and the first Lua error if it persists. Host checks
   verify files and card state; actual beta texture rendering still needs testing.

## Upcoming-guide browsing regression — about 5–10 minutes

1. On a level-12 character, open **Leveling guides**. The default bracket should
   recommend suitable current work. Select **Levels 21–30**: matching future
   zones should appear as **Upcoming zone guide**. Starter zones with only a
   sparse high-level handoff and capital pickup hubs should stay absent.
2. Search for a future zone or one of its quests/NPCs. Click **Show quest list**:
   see the full pickup/objective/turn-in order. Your current route, progress,
   skips and character level must remain unchanged. Try **All levels** too;
   suitable guides should sort before upcoming guides.
3. Click **Start route** on an upcoming guide. Check its level warning and
   current-level recommendation. **Cancel** keeps your route. **Start recommended**
   starts the named suggestion. If no suitable unfinished guide is known, that
   button should be disabled rather than inventing a recommendation.
4. Try **Start anyway**. Existing quest-log choices should still appear when
   relevant. Locked quests must not become pickup targets or gain completion
   credit. If all work is too early, the guide panel should wait and explain
   the level requirement. Scan and `/reload` must preserve its fixed order.
5. At a suitable level, start the same guide: no early-start warning should
   appear. Existing pickup, identity, class-checkbox, prerequisite and NPC-offer
   checks still apply. In a synced party, suitability follows the lowest level;
   solo mode uses your level. Path to Orgrimmar remains a travel guide.
6. Report version/build, level, faction/class/race, bracket, search, selected
   guide, action, screenshot and `/wt probe` for failures. Host previews cannot
   establish live beta layout or API behavior. Manual installation is unchanged.

## Beta event startup regression — about 3–5 minutes

1. Replace the complete folder and `/reload`, keeping SavedVariables. Confirm
   no unknown INN_INFO event error appears, and `/wt`, the minimap button,
   Settings and guide controls are available. `/wt probe` must say **0.8.13**.
2. The report includes **Unavailable event registrations** and **Inn recording**.
   Rejected optional events should be listed there without stopping loading or
   creating extra chat warnings. Send those lines with the client build if any
   event is unavailable; host tests cannot establish beta event support.
3. Accept/turn in a quest, change zones and `/reload` again. Quest progress,
   guide selection, class/nearby-pickup settings and saved skips should still work.
4. At a suitable inn, open the manual home-binding dialog and cancel it. Opening
   it must not make the addon record a confirmed home. Open it again and confirm
   manually: advice for the current home should disappear. Test a different inn
   when practical. Optional recording may be limited if binder events are absent;
   the addon should continue using a public native home name when available.

## Optional class quest checks for 0.8.9 — about 5–10 minutes

1. Keep **Include class quests** off and start a fixed zone guide with a known
   quest for your class. Its pickup, objective and turn-in steps must stay out
   of the arrow, map and **Show quest list**. Normal quests should remain.
2. Turn the checkbox on while following that guide. Eligible class steps should
   return at their fixed positions, still respecting levels, prerequisites and
   actual NPC offers. Turn it off again: they disappear immediately. Try while
   the dashboard is closed; the arrow and map must still update.
3. Accept a class quest, then toggle off. Even its ready turn-in should leave
   the guide; it remains in the game's quest log. Toggle on to restore the next
   unfinished stage. A disabled prerequisite must never count as completed.
4. Manually skip a class quest. Toggle off/on and `/reload`: the skip stays and
   the quest remains uncompleted. Check that other classes and known incompatible
   faction/race quests never become eligible just because the checkbox is on.
5. Open **Show quest list** and toggle the setting. Visible counts/rows change;
   existing step numbers and relative order stay fixed. Reload with the checkbox
   off, then enable it: optional steps must still be available. A pre-0.8.9 zone
   checkpoint should rebuild once to recover previously omitted class records.
6. With auto-accept enabled, talk to a giver offering a class quest from the
   selected guide. It must stay manual while the checkbox is off; enabling the
   checkbox permits the normal in-guide acceptance checks. Send version/build,
   class, race, zone, guide key and `/wt probe` with any failure.

## Nearby pickup checks for 0.8.9 — about 5–10 minutes

1. Enable **Collect useful quests nearby**. Use a guide with several mapped,
   unlocked pickups within 100 yards of its next pickup. The arrow/map should
   gather those accepts before leaving the hub. Only selected-guide quests are
   used; kills, gathers and turn-ins keep their relative order.
2. Talk to each giver. A complete offer list without a planned quest must defer
   it; unknown/branching requirements still need confirmation. Auto-accept must
   require a real offer, and never take unrelated quests just because they are
   close. Turning in a prerequisite may make its pickup eligible later.
3. Test a locked quest, a skipped pickup, a disabled class quest, another zone
   and a pickup beyond 100 yards. None should enter the hub. The radius stays
   anchored to the first pickup, rather than extending through successive NPCs.
4. Accept the grouped quests and check that the existing objective/return order
   resumes. Toggle nearby collection off to follow the original accept order.
   Scan, `/reload` and NPC dialogue must preserve the saved guide sequence.
5. Accept an escort. Its immediate work must stay first, even if other guide
   pickups are offered nearby; auto-accept must not interrupt it. Test a zone
   guide, an adaptive guide and dungeon collection when suitable. Missing map
   scale/coordinates must not create a guessed 100-yard group.

## Confirmation and nearby-objective regression checks — about 10 minutes

1. Start a guide with an unconfirmed branching prerequisite. The warning must
   name the known NPC. The arrow should lead there when a location is recorded;
   a large map star and visible friendly-nameplate hint say **Confirm**. An
   unknown location must stay unknown. Enable friendly NPC nameplates; the
   existing nameplate/star settings still apply and markers hide in combat.
2. Click **Map NPC** outside combat. It opens the giver's zone. On maps with
   working waypoint/readback/clear APIs, it places one Blizzard waypoint; if
   unsupported, the addon's star still works. Normal guide steps must never
   create native waypoints. Opening diagnostics also must not create one.
3. Talk to the giver. An offered quest clears confirmation and becomes a pickup;
   a complete list without it defers it as before. Accept, skip or change guides
   and confirm the old native waypoint clears. Place your own different waypoint
   before progressing: yours must remain. Combat delays cleanup until safe.
4. Accept at least two nearby kill/gather/loot quests. In their objective phase,
   **In this area** shows each target, quest and matching count. Finish just one:
   its row should disappear without completing/skipping the other quests. Check
   separate drops from one mob, multiple objectives in one quest, and synced
   friends with different counts. Use **Skip step/quest** and Scan as usual.
5. Try four or more nearby tasks: scroll the list; none should disappear merely
   because only three fit. Nearby flight/hearthstone tips sit below the list.
   Move/scale the panel and confirm labels, counts and hover details remain clear.
6. Check that pickups, hand-ins, travel, another zone, distant objectives and
   missing-location steps stay separate. Scan, abandon and reload must preserve
   the selected fixed guide's order. These are proximity groups, not proof of a
   walkable path through terrain. Test outside/inside dungeons where applicable.
7. Report tester name, version/build, zone/guide, quest/NPC name, screenshot and
   `/wt probe` for failures. Host checks cannot certify live beta waypoint APIs,
   secret-value behavior, nameplate range or rendering.

## Optional guide tips regression checks — about 5–10 minutes

1. Start a leveling guide and leave both tip options on under **Travel routing**.
   Walk within 150 metres of a friendly flight master. The small strip should
   say **Get flight path** only for a confirmed undiscovered path, or **Check
   flight path** when unlock status is unknown. Open the flight map: a known
   path's tip should disappear. The quest title, step and route order stay put.
2. Move away beyond 150 metres; the strip hides. Test a large and a small zone,
   Horde/Alliance ownership and a neutral hub. Changing yards/metres changes
   only the displayed units; the physical trigger distance stays the same.
3. Near an inn, use a guide with upcoming objectives away from the hub and at
   least two later turn-ins nearby. **Set hearthstone** should appear with a
   reason on hover. It should stay absent for a single nearby errand or an
   existing home. Set your home manually and verify the tip disappears.
4. Click × on a tip, then `/reload`; dismissed advice stays hidden for this
   character and no quest/step is skipped. Different characters keep their own
   unlocks, home and dismissed advice. Disable either option to hide that type.
5. During combat, a flight, Scan guide, step preview or corpse recovery, tips
   should hide. Normal questing restores eligible advice. Drag the panel, try
   your usual UI scale, check hover/close readability and test the standalone
   arrow hover if enabled. Report version/build, zone, NPC, `/wt probe` and a
   screenshot for missed tips or clipping. Host tests cannot certify beta APIs.

## Startup hotfix regression checks — about 3 minutes

1. Replace the complete folder and `/reload`, keeping existing SavedVariables.
   With `/console scriptErrors 1`, confirm there is no SetFont error at startup.
2. Open `/wt`. Both search boxes, Settings, Tracker and Sync controls should be
   created normally. Type in both search fields, then open `/wt probe` and
   confirm version **0.8.13** and a populated character/quest report.
   The minimap button should appear unless previously hidden; `/wt minimap`
   toggles it. Left-click should open the dashboard.
3. Accept or turn in a quest, change zones and `/reload` again. Confirm no
   missing `active`, `trackerButton` or character-table-index errors appear.
   Existing guide selection, settings and skips should remain available.
4. Send any remaining first error in full, with version/build and the action
   that triggered it. Host tests reproduce the font signature but cannot
   establish live beta rendering or API compatibility.

## Instruction regression checks — about 10 minutes

1. Start a guide. Pickup says **Accept from [giver]** and turn-in says
   **Turn in to [receiver]**. The quest name stays above the arrow. Check the
   short action hint and zone/coordinates below it, then hover for full details.
2. Test a kill quest, a ground-item quest and a creature-drop quest. Wording
   distinguishes **Kill**, **Gather** and **Loot**. Kill/loot counts should fall
   as progress increases; the distance row shows the matching `have/need`.
3. On Battleboars or another quest with two drops from one creature, collect
   different amounts of each. Each step must show its own item/count; completing
   one must not mark the other complete. Unmatched/unknown counts stay absent.
4. On Lazy Peons, check the Blackjack instruction, Peons Awoken progress and
   provided-item detail on hover. A tool-use objective must never say Kill.
   Check a well-cleansing, healing or escort step if available.
5. Open Show quest list and hover rows, then test the standalone arrow hover.
   Full action/location text is accessible without expanding the compact panel.
   Long names must remain readable on hover at your usual UI scale.
6. Check a remote step and a missing-location step. Known destinations show
   **Travel to [zone]** and coordinates; missing locations stay unknown, with
   the game tracker fallback. A locked prerequisite still shows its blocking
   reason. Scan, progress, skips and reload retain the selected route/order.
7. If testing in a synced party, verify counts refer to the member named for
   the step. Send `/wt probe`, quest ID and a screenshot for incorrect wording
   or clipping. Host tests cannot establish current beta rendering/API behavior.

## UI regression checks — about 10 minutes

1. Open `/wt`. Check the compact header, gold accents, readable search hints
   and guide rows. Resize to the smallest and largest sizes and drag continuously;
   controls stay inside the window and resizing remains smooth. Try your usual
   game UI scale. Send a screenshot if text overlaps, cuts off or feels too small.
2. Switch between Leveling guides, All quests, Dungeon guides and other views.
   Open the view menu, then the level menu; only one menu stays open. Search by
   typing/pause and by Enter, change brackets and page through the results.
3. Hover a long guide row, then Show quest list. Source details remain available
   on hover. Scroll from first to last step; row numbers, status and instructions
   align without overlapping. Closing a preview must not start/change a guide.
4. Start your saved guide. The arrow sits beside its instruction and distance.
   Test long objectives, a flight countdown, arrival and a zone crossing.
   Drag the panel; Back/Next, Skip step, Skip quest and Scan still work. Scan
   keeps the spinner; the selected fixed guide retains its order. Reload and
   confirm the saved guide, skips and panel position are retained.
5. Open Settings and browse every category. Labels, dropdowns, checks and help
   fit; toggles save correctly. Test standalone arrow and the party tracker,
   including transparency, scrolling and automatic solo/raid hiding.
6. Diagnostics still copies and closes with Ctrl+C. Report any Lua error with
   `/wt probe`, your game UI scale, screen resolution and a screenshot.

## Recent automation/guide regression checks

- **Patrick — dialog scope:** enable Accept guide quests only. At an NPC with
  three offered guide quests and an unrelated quest, collect the guide quests;
  the unrelated quest stays manual even if its dialog is opened. Test a skipped,
  locked or wrong-class quest too; do not accept it. Confirm an explicit dungeon
  guide still accepts its eligible pickup. No selected guide means no auto-accept.
- **Patrick — progress stability:** finish a guide quest, leave/re-enter its
  zone and /reload. The completed steps stay completed and the compiled order
  stays fixed. A genuinely abandoned unfinished quest may restore its pickup.
- **Patrick — markers/patrols:** stars are the default. Select Cross, reload and
  confirm that choice stays. Where a giver has an explicit published patrol,
  check the thin amber path; toggle patrol hints off, zoom/pan and enter combat.
  Record displaced beta paths; the line is not a live NPC position.
- **Patrick — flight timer:** take a suggested or manually selected known flight.
  First-trip countdown is labeled Estimated; a later trip uses recorded timing.
  With no duration/geometry, elapsed time is acceptable. No ground quest lines
  appear during flight. Confirm the selected guide resumes after landing.
- **Main developer — New Horde:** an Orc/Troll must not be sent to pick up this
  quest merely from the catalogue. Record Eitrigg's actual offers and character
  race before proposing a race rule. If it is offered, the positive evidence is used.
- **Main developer — bundles/XP:** start a fresh guide and inspect quest order.
  Nearby pickups, work and returns should form shorter trips; escorts stay next
  to their pickups and prerequisites are handed in first. Movement and Scan must
  not reorder a started fixed guide. Record the route-start XP estimate; its
  Classic curve label and unknown-reward count are limitations, not a promise of
  the level you will actually reach after kills/exploration.

## Broader guide checks

- **Broader source coverage:** test Durotar, Mulgore, Zephras Isle and another
  middle/later zone across testers. Known coordinates should replace previous
  missing-location steps. Record every remaining gap with quest ID and /wt probe;
  this release does not claim all guides are complete.
- **Supplied items and events:** Mulgore well-cleansing quests should name the
  well and Cleansing Totem; provided items must not become farming detours.
  Galgar's apples should target actual Cactus Apple objects and require ten.
  Fizsprocket's Notes uses three community-reported ground-item positions in
  Venture Co. Mine; confirm them in the beta and report displaced points.
- **Native source areas:** Testing the Wells in Westfall should route both
  Jansen Stead and Molsen Farm samples. The supplied Well Water Sample Kit
  must not appear as an item to buy or farm. Confirm both sample points in-game.
- **Healing and prerequisites:** The Wounds of Betrayal should require its
  three known parent quests before pickup and heal seven injured druids,
  rather than kill each credit NPC. After seven credits, its target hints should
  clear. Reload during this step: its shared target label/count should remain.
  Test an escort: acceptance and its escort stage must stay together.
- **Identity gates:** ordinary Horde quests must not acquire a race/class
  restriction from older data. Where possible, test a Skyborne-specific quest
  on the intended race and another race; a genuine restriction still applies.


- **Farming source:** Sting of the Scorpid should point to Scorpid Workers and
  say to collect ten Scorpid Worker Tails, rather than tell you to farm Sarkoth.
  The Sarkoth quest itself still points to Sarkoth. Check another multi-source
  item goal: its named source must be real, in the same farming zone, and an
  existing manual skip must remain respected.


- **Zone coverage:** test a starting zone, a middle-level zone and a later zone
  where you have a suitable character. Include both factions across testers.
  Start the fixed guide and open Show quest list. Record any missing pickup,
  objective or hand-in location with its quest ID/name and NPC/target name.
  Include /wt probe; native map conversion requires beta testing.
- **Useful instructions:** Lazy Peons must say to use Foreman's Blackjack on
  Lazy Peons, rather than kill them or farm the provided Blackjack. The Battleboars
  must include both eight Flanks and eight Snouts at a proven Battleboar area.
  Other kill, gather, interact and item-use quests should name the right target
  and quantity. Check friendly targets are never mislabeled as kills.
- **Static route order:** note the next ten steps. Move, accept a quest, abandon
  it and Scan. Progress changes which steps remain; the compiled order stays
  fixed. NPC pickup visits can gather useful guide quests actually offered there.
  Inspect that parent hand-ins precede locked follow-up pickups.
- **Skips:** skip one of two item goals at the same mob. The other goal must
  remain. Old saved skips should still apply to the originally mapped objective.
  Skip quest should refresh the map immediately. Reload and confirm persistence.
- **NPC offers:** test a multiple-quest giver with useful guide quests offered.
  Optional automation should collect them in one visit. An actual offer may
  overrule an older-world fallback prerequisite; known beta/tester prerequisites
  remain enforced. A missing quest remains deferred, with no completion credit.
- **New zones:** Zephras Isle must have its own guide rather than merge with
  unrelated uncategorized quests. Profession/crafting categories must stay out
  of leveling guides. Expect remaining location gaps; export factual findings
  with /wt research and /wt findings, labeled with your tester name.
- **Map and loading:** start a large guide. Loading route should remain visible
  while it compiles, with no freeze or Lua error. Verify pins at actual NPCs/mobs,
  pan/zoom in and out of combat, and retest cross-zone travel. Lines still show
  visiting order; they cannot guarantee a safe path through terrain.

## Lua pane checks retained from 0.7.7

Open /wt lua, paste a multiline check and a long wrapped line, then scroll.
Run the following, copy its output and Clear. The final return must be visible;
clearing must leave a usable empty pane. Include any Lua error and /wt probe.

```lua
print(string.rep("scroll test\n", 100))
return "end of output"
```

## NPC visit and Lua checks retained from 0.7.6

- **Baine's three quests:** on a suitable level-6 Horde character following
  Mulgore, open Baine Bloodhoof with Rite of Vision, Sharing the Land and Dwarven
  Digging offered. Enable Collect useful quests nearby. All useful unaccepted
  guide pickups should be collected in that visit, instead of leaving after one.
  Check both normal gossip and the quest-greeting list where available.
- **Optional automation:** enable Open guide quests at an NPC and Accept the
  quest dialog I open. Each returned native list should select/accept the next
  guide pickup. Test another multi-quest NPC with already mapped locations.
  Turn each automation option off separately: selection and acceptance remain
  independent, and closing the NPC doesn't reopen it remotely. Retest protected
  actions on this build; a host fixture cannot prove native dialog event order.
- **Guide stability:** note upcoming kill/collect/hand-in order. After collecting
  the group, that original order should remain. Accept/Skip should refresh the
  arrow and map immediately. Low-value, too-high, prerequisite-blocked, excluded
  and manually skipped quests must remain out of the pickup group.
- **Save and reuse:** reload mid-visit; pending pickup instructions should resume.
  After seeing an NPC, missing pickup markers should use its approximate dialogue
  position. Another character on this account/build may reuse the location, but
  must meet its own requirements. No objective, hand-in or completion is inferred.
  Export /wt findings and include it in your labeled report.
- **Lua pane:** open /wt lua. Run each check below, then Select output and Ctrl+C.
  Confirm results stay in the pane. Syntax errors/failed assertions should appear
  there; hidden values should display `<restricted>`. Check with no NPC open too.
  If compilation is unavailable, send the loadstring/setfenv probe lines.

```lua
return GetBuildInfo()
```

```lua
return apiType("C_GossipInfo.GetAvailableQuests"), apiType("GetAvailableQuestInfo")
```

```lua
local offered = C_GossipInfo.GetAvailableQuests()
assert(type(offered) == "table", "No public NPC list returned")
return offered
```

For an NPC using QUEST_GREETING instead of gossip, inspect one slot at a time:

```lua
return GetNumAvailableQuests(), GetAvailableQuestInfo(1)
```

Lua only expands the last expression's multiple returns. The fifth field from
GetAvailableQuestInfo is the quest ID in our tested reader; verify this build.
Short checks can also use the game's native /run. The addon pane accepts locals,
conditionals, print, assert and return; return a table instead of writing loops.
IsPushableQuest measures sharing; IsQuestCompletable describes the opened turn-in.
Neither proves that an arbitrary quest can be picked up remotely.

## Farming-location checks retained from 0.7.5

- **The Battleboars:** on a suitable Horde character, finish The Hunt Continues,
  accept The Battleboars and start/resume Mulgore. Its known farming step should
  point to Battleboars around 57.6, 85.2 for Flanks. The other published source
  around 63.4, 78.2 is an alternative, not a second mandatory stop. Verify against
  the current beta; published coordinates are representative areas.
- **Remaining source gap:** complete Flanks while Snouts remain. If the client
  supplies a public active-objective waypoint, the unmapped step should use it and
  explain that the location came from the quest tracker. If no usable native point
  exists, keep the location-missing notice. Do not assume the Flank location proves
  Snout drops. Actual quest completion still gates the turn-in.
- **Other item quests:** try a quest with several possible drop mobs. It should
  retain a mapped farming area instead of losing all targets. Move, reload, Scan,
  complete an item and Skip step: fixed order and saved skips must remain coherent.

## Flight and scan checks retained from 0.7.4

- **Flight agreement:** with flight suggestions enabled, start Path to Orgrimmar
  or a distant quest route. Open a flight master with a reachable useful flight.
  The arrow and map must refresh immediately. If approaching a master, the text
  should explain walking to it and the flight that follows. With automatic flight
  selection enabled, it must select the same flight shown in the guide.
  If Dijkstra chooses walking as faster, it must not secretly select a flight.
- **While flying:** confirm Flying to the destination. Ground walking lines should
  hide for the ride; the known flight destination can remain marked. After landing,
  walking directions resume towards the original guide step. Recheck pan/zoom.
- **Scan loop:** press Scan guide. Both enabled arrow displays should show a rotating
  loop while calculating, then return to the direction arrow. Try with the large
  panel hidden and only the standalone arrow enabled. A short scan can finish quickly.
  Fixed stage order must stay unchanged. Change/clear the guide mid-scan; stale
  callbacks must not bring it back. Confirm saved skips still follow scan settings.

## Fixed leveling guides and full map

1. **Discover zones:** open Leveling guides. The default bracket follows the
   lowest party level. Search another suitable zone; try another bracket and
   All levels. Cards show total quests and separate published pickup/objective/
   turn-in counts. A large quest count must not imply every location is mapped.
   The first result says Recommended zone guide; remaining results say
   Alternative zone guide. Linked questlines should not duplicate those cards;
   their quests/prerequisites remain inside the zone route and searchable by name.
2. **Start the complete guide:** press Start route. Loading route should appear,
   followed by a numbered zone-guide step. The route should retain the full
   guide, beyond the old six-quest/twenty-stop trip limit. Missing locations or
   locked current pickups should be explained, without invented destinations.
   If asked about existing quests, use Start selected guide for this check;
   Include current quests includes worthwhile log work/ready returns and its detours.
3. **Different starting locations/logs:** two matching-faction/class testers
   select the same zone guide from different places, with different active quests.
   Compare future numbered stages. The generated order should agree for matching
   catalogue/learning data; completed stages may already be advanced on one client.
4. **Accept and hand in:** follow several steps. Accepting a quest advances its
   pickup, without reshuffling future stages. Killing/collecting advances completed
   objectives; a quest cannot advance past its hand-in until actually turned in.
5. **Abandon and scan:** record several future quest names/step numbers, abandon
   one test quest, move elsewhere, then Scan guide. Its pickup can become pending
   again. Existing stage numbers/order must stay the same; no new route generation
   or new detour chosen from your current position. Skip step / Skip quest remain
   saved; Reconsider skips when scanning restores selected-guide skips only.
6. **Full route toggle:** click Show full route in the map overlay. Every currently
   eligible mapped quest in the guide should be included, beyond the current trip.
   Locked later quests stay in the internal sequence and become visible after
   unlocking. Focus next steps restores the short preview. Shared NPC markers can
   contain several numbered steps; hover to see them. No extra Blizzard pin.
7. **Other maps:** view another zone used by the route. Its eligible markers should
   appear in full mode. Cross-zone lines must use public world positions rather
   than treating one zone's raw x/y as coordinates in another. Unprojectable
   stages must break the line instead of connecting around the missing stage.
   Pan/zoom, including during combat, and confirm pins/lines stay attached to the
   terrain. Actual rendering needs live testing; a host test cannot prove it.

## Party, findings and native data

8. **Follow or keep:** Player A starts the zone guide. Player B gets Follow route /
   Keep my route. Keep retains B's guide; Follow selects the full guide and fixed
   mode even if B normally uses adaptive trips. Large guides still send at most
   twenty IDs plus guide identity; the recipient reconstructs the full scope.
9. **Last participant:** finish an objective/quest while a friend still needs it.
   The required step/marker remains for that friend. Verify progress counts and
   skull/cross hints stop marking finished target types, except when still needed
   by another participant. Normal events sync automatically; check queue drain.
10. **Observe an unlock:** with a prerequisite already active, open its giver's
    complete quest list before handing it in. Record a quest that is absent.
    Hand in exactly one prerequisite, then reopen the same giver and observe the
    new offer. One clean pair can produce a tentative pattern. A single quest
    detail alone does not prove absence. Changed level, unknown/truncated history,
    other accepted quests, multiple hand-ins or multiple givers can prevent reuse.
    Reputation notifications are recorded as possible alternative explanations.
11. **Reuse and export:** on a new matching build/faction character of another
    class/race on this account, test an ordinary learned quest requirement.
    For a class/race quest or prerequisite, only the required dimension stays
    specific; do not apply that finding to an incompatible character.
    Start a guide that uses a learned relationship. Playing UI shows only the
    action or requirement, without Observed by labels. Existing fixed guides keep their compiled order.
    `/wt findings` or Export guide findings includes patterns and supporting
    before/after evidence; Select all, Ctrl+C closes the window. Names are omitted
    unless enabled; `/wt research` always omits names. Send labeled text files.
    A real offer before a learned prerequisite is done should disable that rule.
    Published alternative prerequisites must remain valid on another branch.
    Existing findings should survive upgrading; conflicting merged predecessors
    should remain visible in exports but not become active pickup requirements.
12. **Native questlines:** run `/wt questlines` in two or three zones. Export the
    result, including empty results. It shows actual native fields and optionally
    GetQuestLineQuests IDs. This does not assume table membership/order proves a
    prerequisite or that an absent quest is unavailable. `/wt probe` reports APIs.
13. **Optional regression:** turn Follow fixed zone guides off and start a new
    guide. Adaptive trips should optimize nearby work and current logs. Their
    full preview should still include all eligible mapped quests. Check reward
    choices stay manual, tracker auto-hides solo/raid, and UI resizing/arrow work.
14. **Mulgore Hunt chain:** start a fresh Mulgore guide. With The Hunt Begins
    (747) accepted or ready for turn-in, The Hunt Continues (750) must stay locked.
    The fixed sequence must place 747's hand-in before 750's pickup. Hand in 747
    and inspect Grull Hawkwind's actual offers. Record whether 750 now appears;
    the correction is tester-reported, not a newly verified API contract.
    After handing in 747, 750's pickup should occur directly after it in the
    newly compiled sequence, rather than behind unrelated far-away travel.
    Test another partially mapped quest chain too; this is a generic ordering fix.
15. **Skip versus learning:** with recording on, skip a step/quest. Hover both
    buttons to read the distinction. /wt research should contain a skip-step or
    skip-quest event with guideKey, stepKey, stepKind, guideStep (fixed guides),
    level and version, with no invented completion or NPC absence. A skip without
    a later observed unlock must not create a learned prerequisite. Other
    characters must retain their own independent saved skips.
16. **Automatic deferral and restoration:** choose a planned pickup which is
    genuinely unavailable. Open its known giver's complete offer list. It should
    temporarily disappear from current steps, allowing other available work.
    It must remain in the compiled guide and must not become a manual skip.
    Complete the actual prerequisite, revisit the giver and confirm its offer.
    The pickup should return at its original fixed position without Scan.
    Export /wt research: offers plus defer-pickup/restore-pickup events should be
    present when observed during this selected guide. A partial single-quest
    dialog must not establish absence. If nothing is available, retain the guide
    and explain the blocked requirement. Test reload/export persistence too.
17. **Personal dungeon threshold:** with dungeon prompts on, inspect its full
    collection pickup level. Test just below/at that level, solo or with an
    unsynced/lower-level friend. Prompt only at the full known threshold; opening
    it must not silently replace your active leveling guide. Review excluded
    factions/classes/races, repeatables and professions. Unknown levels should
    be explained rather than treated as ready. Start collection with a known
    entrance; if all points are missing, review every quest in the list.
18. **Reusable learning versus skips:** on another matching-build Horde character,
    reuse a clean learned ordinary unlock pattern using its own hand-in history.
    A missing-offer observation alone must not apply a shared skip. Send exports
    labeled by tester and level; repeated manual skips are for baseline review,
    not an automatic account-wide skip rule. No data is uploaded automatically.
19. **Reload and outside-guide questing:** note the selected guide, future fixed
    steps and a saved skip. Accept/hand in an unrelated quest; the arrow and
    controls must stay visible. /reload and log out/in: resume the same guide
    using fresh progress without opening the map or sending new invitations.
    Temporarily blocked and finished guides retain controls. Clear route ends
    the guide, clears pins and prevents it restarting next login. Test two characters.
20. **Party catch-up:** in a normal party, compare completed zone quests, with
    one friend behind through a useful chain. Wait for sync. Catch up party
    must offer a plan without replacing the selected fixed guide. Keep my guide
    preserves it; review again through the zone card or /wt catchup. Accept:
    missing parents come before their children, completed friends can help,
    unrelated low-level junk/professions/repeatables stay out. Friends choose
    Follow route or Keep my route. Test three members and a second zone; unknown
    history must wait rather than infer progress. Raid/solo should not offer it.
21. **Clean markers:** in settings → Party and quest markers, choose Quest !,
    cross or skull. Enemy markers should sit beside names rather than far from
    the nameplate. Disable only nameplate hints; item tooltip hints remain enabled.
    Completed objective types lose their marker; unfinished types remain marked.
    Markers hide in combat, and NPC arrival instructions keep their quest names.
22. **Map footer:** route controls should sit below the map viewport, covering no
    terrain or quest pins. Toggle full route/ahead and View route zone. Test
    windowed/maximized map layouts, zoom/pan and combat. Send a screenshot if
    your beta layout clips the footer or places it off-screen.
23. **Actual level eligibility:** at level 12, check Recommended and Alternative
    zone guides, including Ashenvale. A zone must not appear solely because a
    level-20 quest shares your 11–20 filter. Known pickup minimums and necessary
    prerequisite levels must agree with your level, and its work must be useful.
    Try All levels and a future bracket: neither bypasses actual level. Repeat in
    another zone/level and with a lower-level synced friend. Appropriate earlier
    prerequisite chains remain included; selected fixed guides keep their order
    after leveling. Future quests remain browsable in All quests.
24. **Live cross-zone direction:** start a route whose next mapped stop is in a
    neighboring zone. Move with the map open: the line must start at your current
    position and update, including after zoom/pan. View the destination zone and
    continent map, then cross the border: geometry and arrow distance/direction
    should continue toward the same step. Fixed step numbers/order must remain
    unchanged. Missing/private positions or different continents must not invent
    a connecting line. Lines express direction; follow actual roads/terrain.
25. **Performance and freshness:** compare opening/searching Leveling guides,
    compiling a full guide, scanning progress and panning a full route against
    0.6.8 with matching data/settings. Note any stutter and exact zone/guide/step.
    Guide order, pickup gates, skips, UI controls and sync behavior should agree.
    Accept/abandon/hand in, level up, change NPC offers, join/leave a party and
    reload: every next update must use fresh state. Repeat learned-chain and
    combat/secret-data checks. Host timings/call counts do not establish beta FPS.

## New navigation and guide checks

26. **Standalone arrow:** enable it in Arrow and map. Move it independently,
    hide the large direction panel, turn/move and switch yards/metres. It must
    keep directing you to the same next step. Reload: its toggle/position persist.
    Show both panels; neither should lag or double-poll. Clear route hides both.
27. **Travel graph:** with Use travel connections on, test a cross-zone guide
    step through a known pass or city gate, and a boat/zeppelin/tram trip if one
    is relevant. Reaching the boarding point must not advance quest credit or
    say the ride is complete. Check arrival resumes the same guide quest. Map
    walking lines must follow the selected points and break at transport rides.
    Note wrong/missing crossings or terrain obstacles: point walks are estimates.
    Open flight maps: only observed reachable connections may be suggested; test
    a known multi-leg network and an unlearned flight. With no GetTaxiMapID, known
    sourced coordinates can locate nodes but must not grant flight access. A
    visible native flight-frame map ID may allow the observed node read.
    Turn the graph off: ordinary directions remain and fixed quest order agrees.
28. **Reported guide failure:** a level-12 Horde character starts Mulgore, then
    Durotar, then switches back and forth. Also start Durotar on a level-5 Horde
    Warrior. Capture any generation error. `<UNUSED>`/zzOLD entries must not
    appear as leveling steps, including in a retained guide after upgrading.
    Genuine unknown locations stay explicit; no fabricated quest points.

## New solo and guide checks

29. **Quest-giver star:** start a guide with an eligible pickup, enable friendly
    NPC nameplates and approach its giver. A gold star should appear above the
    visible nameplate, with quest names below. Accepted/completed/blocked pickups
    must not leave a pickup star. Toggle it in Quest markers; enter combat and
    return. Missing nameplates mean no star; no real raid marks should be set.
30. **Solo leveling mode:** while grouped with another addon user, enable it in
    Play mode. Party tabs/buttons, progress and route invitations must disappear;
    messages must stop, including previously queued updates. Accept, kill, hand in,
    scan and reload: personal guides continue and the toggle persists. Re-enable
    party features: compare fresh snapshots, without resurrecting old invitations.
31. **Bonus rewards:** browse Welcome! in All quests; it remains searchable. No
    starting-zone guide or retained guide should contain these Collector's Edition
    pickups. Actual unrelated class progression must remain available when enabled.
32. **Quest list and brackets:** Show quest list opens the complete scrollable
    pickup/objective/turn-in sequence without changing the current route or map.
    Check its last row and compare a started fixed guide's order. At level 12,
    selecting 21–30 must not recommend Mulgore or a city just because it has a few
    later pickup quests. Also test a level-25 character: actual useful quest areas
    should appear, with their main quest band and truthful location coverage.
33. **Low-value work:** at level 12, Durotar must not ask for a new Carry Your
    Weight pickup. Check another low-level quest too. Useful lower prerequisite
    chains should explain their continuation. Start selected guide should filter
    unfinished low-value work; Include current quests must filter it too. Ready hand-ins
    still appear. Scan, movement and level changes must not reorder fixed steps.
34. **Recognize flight unlocks:** log in with some known paths, then open a flight
    master's map. Capture the GetTaxiMapID / GetTaxiNodesForMap capability lines
    and Flight paths / Flight unlock scan / Flight map read in /wt probe.
    Where public flags exist, unlocked paths should be known before opening a
    master; unknown flags must not grant access. Opening the master should record
    its source and reachable connections. Close/reopen promptly: stale retries
    must not read or choose flights after closing. Unlock another path, change
    zones and reload; ownership should update and persist only for that character.
    Repeat with Solo leveling mode on. Other characters and opposing-faction
    nodes must not inherit access. Missing APIs/positions give a specific status.
    A public unlocked node with zero observed connections still needs a master's
    reachable list before it can become a flight suggestion. Auto-flight stays
    off unless explicitly enabled; secret slots/current-master gaps stay manual.
35. **Immediate skip redraw:** with a guide and map open, Skip quest. All of that
    quest's markers should disappear immediately; the arrow targets the next
    remaining step. Skip step removes just that step. Repeat with the main window
    hidden, while resizing, and during combat. Owned map geometry can update;
    protected actions still wait. Reload should preserve the skip. Do not receive
    completion credit, unlock a follower or change the fixed sequence's order.
36. **Close level band across guides:** solo at level 23, confirm Diagnostics says
    quest levels 20–26 / You. Centaur Bracers (14) must not become an unaccepted
    pickup. Test normal zone, adaptive, retained quest/circuit and current-quest
    routes; accepting it manually and choosing Include current quests must not
    reintroduce unfinished low-value work. A ready return can remain. Repeat with
    another zone/quest and at a higher level. Useful known prerequisites/class
    progression must explain their exception. With a lower-level synced friend,
    confirm the displayed band changes to that friend's level; a refreshing peer
    must not lower it from stale data. Attach the actual offending pickup step's
    probe if any low quest still appears, including version and party context.
37. **Path to Orgrimmar:** Horde levels 1, 23 and 60 should find this travel guide
    in their normal bracket/search. Start from Durotar, the Barrens and a zone
    requiring a zeppelin where available. Compare directions and estimated time
    with known flights on/off; never suggest an unconfirmed flight. No quest
    pickups or party invitation. Reload and confirm it resumes; Scan refreshes
    travel. Entering Orgrimmar finishes it and retains the panel. Starting inside
    the city should say Arrived. An unmapped/disconnected zone should explain the
    gap without inventing a crossing; this is a travel graph, not a terrain mesh.

## Copyable tester report

```text
Tester: [name; say whether this is the main developer]
Date:
Addon / client build:
Level / class / race / faction / zone:
Party size / selected guide:
Fixed zone guides / full route / learning settings:
Checks 1–37: Pass / Fail / Skip (reason)
Exact quest name and ID / NPC / current and next step numbers:
What happened / expected result:
Was the quest offered? Was its prerequisite handed in?
Attach /wt probe, /wt findings, relevant /wt questlines and a screenshot if useful.
```

Review overlapping reports before changing shared guide data. Ask the user first
when suggested behaviors contradict; observations alone are not contradictions.
Host checks validate Lua 5.1 logic only. Retest beta APIs and map rendering on the
client build in front of you before treating results as final.
