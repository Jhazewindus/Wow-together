# Wow Together — friend test script

For **0.5.5**, World of Warcraft: Forever beta, interface **16001**.
Allow about **20–30 minutes** for the main checks. Player A starts routes;
Player B tests the invitation and reports their own progress. Swap roles once.
Record **Pass / Fail / Skip** for each check. If a quest is already completed
or unavailable, use another suitable quest or mark that example skipped.

## Before playing

1. Both players replace the complete `WowTogether` folder, including every Lua
   file, in `World of Warcraft\_classic_beta_\Interface\AddOns\WowTogether\`.
   Run `/reload`; restart fully if a new addon folder does not appear.
2. Join a normal party. Start in the same zone for the route comparison.
   Open `/wt config`: enable **Finish our current quests first** and
   **Include eligible nearby pickups**; use **Balanced** walking budget.
   Leave auto-accept off for the main run.
3. Enable `/console scriptErrors 1`. Open `/wt probe` on both clients and
   record addon version, client build, levels, classes, factions and zones.
   Let sync drain; use `/wt sync` once if needed to establish the baseline.
   Each client should show the other player's received quest snapshot.

## Main run

| Check | Actions | Expected result |
| --- | --- | --- |
| 1. Automatic sync | A accepts an available quest, then both watch `/wt`. Do not repeatedly press Sync. Wait for the paced queue to drain. | B sees A's quest change automatically. Diagnostics show received snapshots and no continuing failed transfers. |
| 2. Nearby bundle | With Lazy Peons active around Valley of Trials, inspect the refreshed guide. Use **Show route** on that guide. | Available Galgar's Cactus Apple Surprise and the general Vile Familiars can join the trip when within the walking budget. The pickup NPCs are named. Completed or unavailable quests are excluded. Apple's missing objective coordinates are described as incomplete. |
| 3. Prerequisites | Before completing Vile Familiars, inspect Burning Blade Medallion in the library. Check again after handing in the prerequisite. | Accepting or finishing objectives alone does not unlock the follow-up. Completed history, or a live NPC offer, confirms availability. A general quest must not demand the other class variant's introduction. |
| 4. Ready quests first | Have one ready-to-turn-in quest plus unfinished work. Refresh the recommendation and show it. | The ready turn-in precedes new pickups. Later objective/return stages remain for unfinished party members. |
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
| 13. Controls | Drag-resize the main window in several directions. Scroll the tracker; drag it. Use the minimap button. Search the library by typing a zone, then pressing Enter or pausing. | Resizing is smooth; text and party cells fit. Tracker scrolling reaches later quests. The minimap button opens the addon; route lines are on the world map only. Library searches commit on Enter/pause. |
| 14. Strict mode | Turn off **Include eligible nearby pickups** and inspect the guide/current local route. Turn it back on. | Automatic plans switch to accepted party quests only, then permit nearby pickups again. An explicitly followed friend's bundle retains the selection you accepted. |
| 15. Persistence | Move the window, tracker and arrow. Resize the window, then reload; optionally log out and back in. | Saved positions, size and settings return. If they do not, report the client build and whether it occurred on reload or a full restart. |

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

## Send back this report

Copy this block and fill it in. For a failure, send both clients' `/wt probe`
reports after the problem occurs. Ctrl+C in diagnostics copies and closes it.
For map issues, include a screenshot plus rendered pins/lines, drawing surface
and view geometry. For quest exclusions, include the **quest name, NPC, class,
level, whether already accepted/completed, and whether the NPC offers it**.

```text
Wow Together test report
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
Optional checks:

Failure to investigate:
Quest and NPC:
Steps to reproduce:
Expected:
Actual:
Lua error or blocked-action text:
Both diagnostics / screenshot attached:
```
