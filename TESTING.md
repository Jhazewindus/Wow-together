# Wow Together — friend test script

For **0.6.1**, World of Warcraft: Forever beta, interface **16001**.
Allow about **45–60 minutes** for the main checks. Player A starts routes;
Player B tests the invitation and reports their own progress. Swap roles once.
Record **Pass / Fail / Skip** for each check. If a quest is already completed
or unavailable, use another suitable quest or mark that example skipped.

## Before playing

1. Both players replace the complete `WowTogether` folder, including every Lua
   file, in `World of Warcraft\_classic_beta_\Interface\AddOns\WowTogether\`.
   Run `/reload`; restart fully if a new addon folder does not appear.
2. Join a normal party. Start in the same zone for the route comparison.
   Open `/wt config` → **Leveling guides**: enable **Collect useful quests
   nearby**; choose **Small detours**. Leave **Reconsider skips when scanning** off.
   Leave auto-accept and auto-turn-in off for the main run.
3. Enable `/console scriptErrors 1`. Open `/wt probe` on both clients and
   record addon version, client build, levels, classes, factions and zones.
   Let sync drain; use `/wt sync` once if needed to establish the baseline.
   Each client should show the other player's received quest snapshot.

## Main run

| Check | Actions | Expected result |
| --- | --- | --- |
| 1. Automatic sync | A accepts an available quest, then both watch `/wt`. Do not repeatedly press Sync. Wait for the paced queue to drain. | B sees A's quest change automatically. Diagnostics show received snapshots and no continuing failed transfers. |
| 2. Nearby bundle | With Lazy Peons active around Valley of Trials, inspect the refreshed guide. Use **Show route** on that guide. | Available Galgar's Cactus Apple Surprise and the general Vile Familiars can join the trip when within the walking budget. The pickup NPCs are named. Completed or unavailable quests are excluded. Apple's missing objective coordinates are described as incomplete. |
| 3. Prerequisites | Before completing Vile Familiars, inspect Burning Blade Medallion in All quests. Check again after handing in the prerequisite. | Accepting or finishing objectives alone does not unlock the follow-up. Completed history, or a live NPC offer, confirms availability. A general quest must not demand the other class variant's introduction. |
| 4. Nearby ready quests | Have one ready-to-turn-in quest at a nearby NPC plus unfinished work. Refresh the recommendation and show it. | The nearby ready turn-in precedes new pickups. Later objective/return stages remain for unfinished party members. A distant delivery should not pull the plan away from local work. |
| 5. Keep my route | B selects a route. A presses **Start route** on another guide. B chooses **Keep my route**. | B receives a popup. Their route stays unchanged before and after choosing Keep. |
| 6. Follow route | A presses Start route again. B chooses **Follow route**. | B gets the same quest selection, including nearby pickups. Each client uses the party's actual quest progress; invitations do not resend themselves. |
| 7. Different pickup progress | Only A accepts one newly bundled quest. B leaves it unaccepted briefly, then accepts it. | B still has a pickup step while A has objective work. After B accepts, B's pickup changes to work. Refreshing recommendations does not discard the selected bundle. |
| 8. Personal drop counts | Both hold an item/drop quest. A collects an item while B does not; then swap. Check the movable tracker. | Each player's count matches their own quest log. The addon does not copy one player's item count to everyone. Objective credit shared by the game is allowed to update both. |
| 9. Last player finishes | Only A completes and turns in a selected quest; B finishes later. | B's remaining objectives and turn-in stay marked after A's hand-in. The quest's remaining stages disappear after the final participating player hands in. Other selected quests remain. |
| 10. Reload recovery | While both have unfinished selected work, B runs `/reload`. | A retains the last confirmed route while B's snapshot refreshes. Sync resumes and current progress replaces the old data. |

## Map, arrow and window

| Check | Actions | Expected result |
| --- | --- | --- |
| 11. Map rendering | Show the route, zoom in/out, pan, resize the map, then close/reopen it. Hover a clustered numbered marker. | Addon lines and pins stay on their locations. A shared pin lists all its steps. An incomplete route does not invent missing coordinates. Lines show visiting order; follow roads and terrain. |
| 12. Navigation | Close the map, turn your character and walk toward the next stop. Drag the arrow. Approach a known NPC. | The arrow turns and the distance decreases when public map/facing data exists. At the destination it keeps the quest name, points down and names the NPC. Arrival alone does not accept or complete the quest. |
| 13. Controls | Drag-resize the main window in several directions. Scroll the tracker; drag it. Use the minimap button. Search All quests by typing a zone, then pressing Enter or pausing. | Resizing is smooth; text and party cells fit. Tracker scrolling reaches later quests. The minimap button opens the addon; route lines are on the world map only. Searches commit on Enter/pause. |
| 14. Strict mode | In Party quests, turn off **Collect useful quests nearby**, select the explicit quest-log guide card and inspect its local route. Turn it back on. | Quest-log trips switch to accepted party quests only, then permit nearby pickups again. An explicitly followed friend's bundle retains the selection you accepted. |
| 15. Persistence | Move the window, tracker and arrow. Resize the window, then reload; optionally log out and back in. | Saved positions, size and settings return. If they do not, report the client build and whether it occurred on reload or a full restart. |
| 16. Short preview | With a route longer than three places, inspect the map. Use **Show full route**, then **Focus next steps**. Cycle **2 ahead** through zero, one and two. Complete an objective or accept a pickup. | Default pins/lines show the current place and two ahead; consecutive shared-NPC steps stay grouped. Controls change only the preview, and later steps appear as quest progress advances. Arrival alone does not skip unfinished work. |
| 17. Local work first | Hold active Barrens work plus a delivery to Thunder Bluff, or an equivalent local/remote pair. Select the explicit quest-log guide card; then start a new leveling guide and choose whether to include current quests. | Known active local work remains above remote delivery and new pickups. The new-guide popup warns about detours; Start selected guide preserves that selection. No other zone's coordinates are drawn on the current map. |
| 18. Zone handoff | View a different zone with a selected route. Use **View route zone**. Finish a selected quest whose receiver is in another zone. Read the arrow's small context text. | The map explains where the retained route is. The button opens that map. The active route advances to the receiver's map after progress confirms it; the arrow explains travel and whose pickup/work/hand-in is next. |
| 19. Repeatables | Inspect Spirit of the Wind or another known repeatable in All quests and automatic guides. | It remains in All quests, labeled repeatable, but does not join automatic leveling plans. Report other misclassified quests with their names/NPCs. |
| 20. Saved skips | Start a route with several stops. Click **Skip step**, then **Skip quest** on another quest. Reload and reselect the guide. Use **Reset guide skips** in settings. | Only your guide advances. Skips persist for your character; reset restores them. Actual quest credit/history and friends' guides do not change. Skipping a prerequisite must not unlock its follow-up. |
| 21. Guide scan | Start a guide containing completed and unfinished quests. Click **Scan guide** on the arrow. | Completed work is omitted and actual accepted stages remain. The route replans to useful current work without opening a report popup. Missing history remains unknown; friends' histories wait for their received snapshots. |
| 22. Mob-type markers | Hold a quest requiring two mob types. Finish the first type while leaving the second unfinished. Check both nameplates outside combat. | The finished type loses its marker even while the native quest flag still relates it to the quest. The unfinished type keeps its marker. Another unfinished quest/party participant may still need the first type. |
| 23. Combat map motion | With a route already drawn, enter combat, open the map and pan/zoom. After combat, inspect the next waypoint. | Unprotected addon lines/pins move with the map rather than staying at their old screen position. Protected/native actions wait for combat to end. Report any blocked-action text and `/wt probe` geometry. |

## New 0.6.0 report regressions

| Check | Actions | Expected result |
| --- | --- | --- |
| 24. Useful level range | At roughly level 25, browse Barrens guides. Compare an old isolated quest with an early prerequisite leading to a relevant later/dungeon quest. | Old junk is not newly recommended. A justified low-level prerequisite explains its worthwhile follow-up under the arrow. Manually included active work can remain. |
| 25. Party behind | Use a known chain where A has finished an earlier quest and B has not. Let history sync, then start the same guide. Swap which player starts it. | Both help B through useful earlier stages; A's later quest does not prove B's prerequisite complete. Unknown peer history stays waiting. Test with an actual party, since the submitted diagnostics were solo. |
| 26. Hidden NPC unlock | Visit a known giver before an unavailable follow-up unlocks. Inspect the route, then complete the prerequisite and visit again. If a direct single quest dialog opens, inspect the other quests too. | A complete public list can block an absent pickup; new progress causes a recheck. A single dialog does not mark all other quests unavailable. The optional user-tested beta pickup gate is checked separately; record any disagreement between its boolean and the actual NPC offer. |
| 27. Stable crossing | Select an active cross-zone objective such as Deepmoss Spider Eggs. Accept another quest, cross the zone boundary and continue to that objective before finishing it. | The selected quest set remains. Crossing a zone alone does not turn the player around. Scan guide explicitly recalculates the best plan; report its before/after destinations. |
| 28. Step navigation and scan skips | Start mid-guide with an accepted quest. Preview back to its pickup, then forward. Skip work, reload and scan with Reconsider skips off, then on. | Preview is read-only and labeled; skip controls cannot change the previewed quest. Off retains skips; on clears selected-guide quest skips and replans to the best current step. An entirely skipped guide can still be scanned. Reset clears all zones' skips for this character only. |
| 29. Dashboard and start choice | Browse the dashboard and each settings category; resize. Find an explicit quest-log route in Party quests. Start a different guide with current quests, test each popup choice separately, then select metres. | Dropdown labels and tooltips are readable. Start selected guide uses that guide; Include current quests keeps existing work and warns about detours. Distances switch units. Party quests / All quests names are clear. |
| 30. Markers and actions | Inspect a kill step, an item-collection step and a giver/receiver. Hover a known required quest item outside combat; optionally switch Cross to Skull for kills. | Instructions distinguish Kill / Pick up / Talk to NPC. Cross markers and item-tooltip quest hints use known data. Finished targets remain unmarked unless another unfinished quest/member needs them. Unsupported world objects need not have nameplates. |
| 31. Panel lifecycle and dungeon start | Leave the party, join it, dismiss the tracker, rejoin and enter a raid. In Dungeon quests press Start route for a level-appropriate collection; inspect Quest log review. | Tracker hides solo/raid and opens on a new party session. Dungeon collection has steps and a known nearby entrance, with missing prerequisites explained. Quest-log review only suggests; no quest is abandoned. |

## New 0.6.1 guide regressions

| Check | Actions | Expected result |
| --- | --- | --- |
| 32. Catalogue-wide guides | Use two suitable characters in different zones, such as Ashenvale and another zone outside the Barrens. Open Leveling guides. Change brackets, search a zone/NPC, pause or press Enter, and page through results. | Default lists full zone guides/questlines matching the lowest party level bracket, with faction restrictions. Remote guides remain browsable. No single NPC quest is presented as a full guide. All quests retains individual records. |
| 33. Start and loading | Start or show a real guide in each tested zone. Record the first NPC/quest and whether that NPC offers it. Test a guide with incomplete locations too. | Loading route appears before planning finishes. The first located useful unlocked step is mapped. Missing locations are explained and the guide stays selected; no coordinates or quest availability are invented. |
| 34. Full guide versus trip | Start the same guide on both updated clients after history sync. Compare Diagnostics: Selected guide, quests in scope, Current trip, Trip quest IDs and stops. Complete the trip and continue leveling. | The full guide persists beyond its current trip and bracket. A quest can have three or more stops; different confirmed progress or partial locations can change stop counts. Later eligible work enters the trip rather than replacing the full guide. |
| 35. Optional next-zone guide | Follow a useful chain into a suitable nearby next zone, or finish local work and enter one. Keep zone prompts enabled. Test Keep my guide, then accept a later offered transition. Try below the next zone's useful level range. | Known chain steps can cross zones. A suitable transition offers Start zone guide / Keep my guide; no silent switch occurs. Accept starts the full next-zone guide, with the normal current-quests choice where applicable. Unsuitable levels, unknown links or missing peer snapshots do not confirm a transition. |
| 36. Quest greeting and scorpion pickup | On the affected character, visit the scorpion quest's giver before it unlocks. Record the greeting list, whether Cutting Teeth is completed and the greeting diagnostics. Progress and revisit. Also test a giver offering multiple quests with optional dialog selection. | A complete public greeting list can block an absent quest just as gossip can. Changed progress invalidates that absence. Actual offers confirm availability; hidden gates are not guessed. Opt-in selection uses the matching native slot. Missing/restricted APIs stay explicit and manual. |
| 37. Extra waypoint and scan footer | Place your own manual Blizzard waypoint first. Start a route, progress and Scan guide; then clear the addon route. Inspect the arrow controls. If an old addon waypoint remains, remove it manually. | No extra Blizzard pin is created or moved; your manual waypoint remains. Numbered addon route markers/lines remain available. Scan optimizes progress with Loading route and has no extra Guide replanned footer below its controls. |
| 38. Trip stability and shared scope | With a multi-quest guide, accept one pickup, complete a subset, then finish the trip. Share a full guide with more than twenty quests. B chooses Keep, then Follow on a second invitation. | Acceptance retains the current trip's quest set; finished work leaves as confirmed. The next trip comes from the retained full guide. Follow reconstructs the same full guide identity, not only the invitation's twenty IDs; Keep leaves B's guide untouched. |
| 39. Tested pickup gate and automatic unlock | Keep Use the tested beta pickup check enabled on both updated clients. Test solo, then in a party: before the scorpion follow-up unlocks, record its actual NPC offer and the pickup diagnostics. Turn in the prerequisite, wait for the queue to drain, and revisit without pressing Scan. Compare players at different progress. Also inspect an accepted quest and try the setting off. | A public false excludes a new pickup; true allows a useful, compatible candidate with a known location. The changed result refreshes automatically, including when the quest-log revision is unchanged. Each friend supplies their own result, matched to their log snapshot. Newly unlocked nearby work can join the trip while its unfinished objective stays first. Accepted work is retained. Unknown/restricted values are not false. Missing/disabled APIs use existing gates. Report the build and any boolean/NPC disagreement. |

If a guide cannot start, include its exact name, bracket, first NPC/quest, copied
Diagnostics and the NPC's actual offered list. For an 18-versus-3 comparison,
include both players' guide identity, scope, trip IDs, active quests, completion
history and party snapshot status; do not compare only the map's stop count.

## Flight and corpse checks (optional, beta API behavior)

- Open two flight-master maps on the same character. Record `/wt probe` travel
  capability/status, the suggested destination and whether you actually know it.
  With **Suggest faster known flights** on, choose a long route where flying
  should save travel time. The arrow/map should first direct you to the appropriate
  known flight master; estimated savings must be labeled. Local walking should
  not detour across the world just to board a flight.
- Keep **Select the suggested flight** off initially: opening the map must not
  board a flight. Test a manual flight; record elapsed time. On a later measured
  ride check approximate remaining time. Restart/reload between rides to check
  private network/timing persistence. Flight time is not a server-confirmed ETA.
- If you opt in, open the correct source map and check that only its currently
  reachable suggested destination is requested. Wrong sources, missing/restricted
  data and combat must stay manual. Report Lua errors or blocked-action text,
  whether the request worked, and the build. Turn off the option after testing
  if you do not want it. Do not assume API presence proves protected action success.
- Near an observed unconfirmed flight master, check that a small optional visit
  names it. Confirm/learn the path and reopen the map; it should stop asking.
  There is no complete global flight-path database in this release.
- During ordinary gameplay, die with a guide selected and release manually.
  Check corpse directions in the death zone, then from a neighboring graveyard
  zone; recover manually. The quest guide should survive and resume. If corpse
  API data is unavailable, a recorded death position is approximate or the panel
  explicitly reports unavailable data. No resurrection/release is automated.

## Optional checks

- **Third player:** repeat pickup counts and last-player completion in a party
  of three. A member without a received addon snapshot stays waiting.
- **Combat:** enter combat naturally with a selected route. NPC nameplate hints
  should hide in combat; pending map/route changes should apply afterward.
  Approach a quest NPC with nameplates visible outside combat; where its public
  ID is available, check the quest-name hint and downward pointer.
- **Different levels/zones:** recommendations should account for the lowest
  synced level and faction. Nearby quests should not send a low-level Horde
  character across the world or into an Alliance starting zone. Moving into
  another zone should update context while party quest sync continues.
- **Dungeon / Buy list / Professions:** inspect an available dungeon collection
  and its pickup NPCs; inspect a quest with known buyable items. Open a profession
  window and check its personal recipe/material guide. AH prices depend on
  searches you perform. Missing source information should be explained.
- **Auto-accept:** opt in, open one available quest-detail dialog outside combat,
  and confirm whether it is accepted. Report any blocked-action message. Turn
  the option off again afterward if you do not want this behavior.
- **Auto-turn-in:** in `/wt config`, enable the turn-in option. Open an accepted,
  completed quest at its NPC with **no reward choice**; confirm it hands in.
  Then open one with reward choices: it must wait for your manual choice.
  Repeat with the option off. Report `/wt probe` plus any Lua/blocked-action
  message, and whether `CompleteQuest` / `GetQuestReward` actually worked on
  your build. Automatic actions should not run during combat.

## Send back this report

Label your report **main developer** or **friend: [name]**. Include all checks
that failed or were skipped; do not combine different players into one identity.

Copy this block and fill it in. For a failure, send both clients' `/wt probe`
reports after the problem occurs. Ctrl+C in diagnostics copies and closes it.
For map issues, include a screenshot plus rendered pins/lines, drawing surface
and view geometry. For quest exclusions, include the **quest name, NPC, class,
level, whether already accepted/completed, and whether the NPC offers it**.

```text
Wow Together test report
Reporter (main developer / friend name):
Date:
Addon version on A / B:
Client build on A / B:
A: level / class / faction / zone:
B: level / class / faction / zone:
Party size:

Results (Pass / Fail / Skip; state why a check was skipped):
1 Automatic sync:
2 Nearby bundle:
3 Prerequisites:
4 Ready turn-ins:
5 Keep my route:
6 Follow route:
7 Different pickup progress:
8 Personal drop counts:
9 Last player finishes:
10 Reload recovery:
11 Map rendering:
12 Navigation:
13 Controls:
14 Strict mode:
15 Persistence:
16 Short preview:
17 Local work first:
18 Zone handoff:
19 Repeatables:
20 Saved skips:
21 Guide scan:
22 Mob-type markers:
23 Combat map motion:
24 Useful level range:
25 Party behind:
26 Hidden NPC unlock:
27 Stable crossing:
28 Step navigation / scan skips:
29 Dashboard / start choice / units:
30 Markers / action wording:
31 Panel lifecycle / dungeon start / log review:
32 Catalogue-wide guide browser / brackets / search:
33 Start / Loading route / first NPC:
34 Full guide / trip IDs / map stops:
35 Optional next-zone guide / Keep my guide:
36 Quest greeting / unavailable scorpion pickup:
37 Extra waypoint removal / Scan footer:
38 Trip stability / full shared guide scope:
39 Tested pickup boolean / automatic unlock / peer differences:
Flight network / actions / timed rides (optional):
Corpse directions (optional):
Selected guide / current step / settings:
Optional checks:

Failure to investigate:
Quest and NPC:
Steps to reproduce:
Expected:
Actual:
Lua error or blocked-action text:
Both diagnostics / screenshot attached:
```
