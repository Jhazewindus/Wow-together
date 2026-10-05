# Wow Together

A World of Warcraft: Forever beta addon for choosing quests with friends,
comparing progress, and drawing the next stops on the world map.
Targets **interface 16001**, Lua **5.1**. No service or Battle.net credentials
are required by the addon.

## Version 0.5.0

- **Local XP circuits:** prefer nearby pickups and objective areas that return
  to the same hub. Collect first, work objectives, then batch turn-ins. Settings
  control detours and the 2–6 quest limit. Published XP helps rank plans;
  actual XP varies by player level. New zones use the same data-driven rules.
- **Dungeon quests:** a separate tab lists published dungeon quest collections,
  pickup levels, NPCs and prerequisites. A level-appropriate local collection
  prompt can map pickups before the entrance. Native map links supply entrances
  when available; otherwise stand outside and use **Record entrance here**.
  Unknown entrances remain unknown and distant pickups are excluded.
- **Personal professions:** choose a profession quest guide or open your
  crafting window and refresh live recipes. Recipes with confirmed skill gains
  are ranked by difficulty and observed material cost, with small craft batches
  and personal shopping lists. Live recipe APIs must be tested on your beta.
- **Buy lists:** known vendor-listed quest requirements are combined and your
  bag stock is subtracted. AH estimates use commodity searches you make this
  session; the addon does not search, buy, bid, or craft for you.
- **Settings:** `/wt config` controls tracker transparency/height, circuits,
  NPC hints, class quests, map legend and activity prompts. Auto-accept is
  **off by default**; if enabled, it attempts to accept only a quest dialog you
  open, outside combat. Verify that action on your beta build.
- **Next-zone prompts:** suggest a nearby published questline continuation
  when the party completed its previous step and local circuits are running low.
  No transition is inferred without public world positions and prerequisites.

- **Party tracker overlay:** a small movable window compares public item-drop,
  kill, and other objective counts, showing player names and zones below each
  objective. Mouse-wheel scrolling covers all tracked quests/objectives, with
  only visible text rendered. Its background is almost transparent by default.
  Unknown counts stay pending. `/wt tracker` or **Tracker** toggles it.
- **Keep helping the party:** turning in your quest leaves the markers for
  friends who still need it. A party route stays on objectives while anyone
  still needs them, even if another player is ready to turn in. A route finishes
  after the last relevant member's completion is confirmed. Known faction/class/race exclusions do not hold it
  open; unknown restrictions, missing snapshots, and low levels still need checking.
- **Library performance:** easy level brackets and **Near party**, search on
  Enter or after a 0.4-second pause, and 24 results per page.
- **Map polish:** small quest/skull icons and plain collection symbols, outlined
  numbers, consistent line opacity and a compact optional legend. The route
  overlay ignores inherited alpha when the client supports it. Pending party
  snapshots still dim the whole confirmed route deliberately.
- **Snapshot recovery:** peer reloads retain previous progress while refreshing.
  Bounded repair requests recover missing active snapshots. Selected route lines
  remain dimmed while waiting for fresh evidence.
- **NPC hints:** retain alternative item-drop NPC IDs even when route coordinates
  are ambiguous. Already-visible nameplates are checked, with a public native
  quest-flag fallback when available. Icons work outside combat for objectives,
  turn-ins, and selected pickups. Combat hides them; no raid-target marking.
- **Quest guide:** one recommended questline or hub, alternatives, and zone
  routes. Levels, faction, active quests, checked history, and published
  requirements inform the next step. A large level gap can suggest helping
  the lower-level player first; the recommendation logic has no fixed character
  levels or test-zone assumptions.
- **Show route:** numbered pickup, objective, and turn-in stops joined by map
  lines when the canvas supports them. Routes update after quest changes.
  Pickup and return stops at the same location share a pin, such as `1/3`.
- **Quest library:** browse imported zones, search names, check known requirements
  and previous steps, and open routes or quest details.
- **Missing-data explanations:** a quest without coordinates opens details.
  Ambiguous item-drop targets are left out of planned routes.
- Compact party comparisons, minimap button, saved resizable dashboard, Ctrl+C
  diagnostics, and paced party sync remain available.

Lines show a suggested **visiting order**, not roads or an optimal leveling
path. Follow terrain and roads. Objective points represent areas, not every
spawn. Future stages are labeled in tooltips. Cross-zone stages are not joined
across incompatible map coordinates. The beta must confirm actual rendering.

## Install in the Forever beta

Copy the complete **WowTogether** folder to:

```text
World of Warcraft\_classic_beta_\Interface\AddOns\WowTogether\
```

`WowTogether.toc` belongs directly inside that folder. Update **every party
member to 0.5.0**, including all new files, then `/reload`. Restart the client
fully if a new addon folder does not appear in the character-screen addon list.
The release ZIP includes the complete TOC, every Lua file, data summary,
instructions, and license. Copy the folder rather than individual changed files.

Commands:

- `/wt` — open or close the dashboard.
- `/wt sync` — request fresh party updates.
- `/wt probe` — open diagnostics; select all, then Ctrl+C to copy and close.
- `/wt minimap` — hide or show the minimap button. Left-click opens the dashboard;
  right-click opens diagnostics.
- `/wt tracker` — show or hide the party objective overlay. Drag its background
  to move it; mouse-wheel scroll for more quests and objectives.
- `/wt config` — open settings, including tracker transparency and opt-in
  acceptance of opened quest dialogs.
- `/wt route clear` — remove the route overlay; the map legend also has a close
  button. The native user waypoint remains under the player's control.

Drag the bottom-right grip to resize from 760 × 580 to 1280 × 1000. Window size,
minimap visibility, tracker visibility/position, configuration, recorded dungeon
entrances, activity notices, and learned NPC encounters are
saved after `ADDON_LOADED`.
Encounters are separated by client build. Party snapshots and selected routes
remain in memory. Never include credentials in the addon or repository.

## Quest data coverage

The offline snapshot was captured **October 4, 2026**. It combines public game
facts from [Warcraft DB](https://forever.warcraftdb.com/list/quests) and
[Wowhead Forever](https://www.wowhead.com/forever/quests).
Quest descriptions, artwork, and other addons' code are not included.

| Coverage | Snapshot |
| --- | ---: |
| Distinct quest records | 5,230 |
| Published category lists read | 123 |
| Detailed quest pages | 435 |
| Quests with published pickup coordinates | 392 |
| Quests with at least one clear objective-area coordinate | 118 |
| Quests with published turn-in coordinates | 417 |
| Quests in published linear series | 198 |
| Quests with incomplete or ambiguous objective locations | 157 |

**This is not every Forever quest.** Warcraft DB supplied 1,060 records.
Wowhead's main list displayed only 1,000 of its reported 5,366 results. Published
leaf categories supplied the broader list, including class, dungeon, and
profession quests. Detailed imports prioritized quests up to level 30 and retained
previously cached pages, including 65 Durotar and 116 Barrens quests. Some detail
pages returned HTTP 403, so fetching stopped and the accessible facts were kept.
Version 0.5.0 also retains accessible Ragefire Chasm, Wailing Caverns, and
early profession quest details. NPC hints keep up to 96 alternative/direct
targets per detailed quest. Required item counts and vendor prices are imported
only where published. A vendor price does not prove current stock or availability.
Many quests therefore have names and requirements without NPC or objective
coordinates. The coverage summary records unavailable details.
Published facts can include legacy entries or change during beta. Catalogue
presence does not prove current availability in build 70205.

Area-table IDs are joined to client UI map IDs only where shared quest records
provide an unambiguous match. They are never substituted directly for UI map IDs.
Published linear series provide previous-step checks; branching displays are
not treated as linear chains. This is not a complete prerequisite graph. Class
and race masks are checked only when the IDs and bit library are available.
Unknown data stays unknown; the quest giver confirms actual pickup availability.

Client questline markers and active waypoints are read when their APIs exist.
Talking to an NPC with offered quests records the NPC name and the player's
approximate encounter position and shares it with the party. Gossip lists and
direct quest-detail dialogs are supported. Live active destinations take
precedence over imported ones. An active quest is never routed to its pickup
NPC merely because its objective location is missing.

The public [QuestTogether description](https://www.curseforge.com/wow/addons/questtogether)
was reviewed for broad ideas about progress clarity. Its addon code, assets,
and layouts were not downloaded or copied. This implementation is independent.

## Using the guide

1. Open `/wt`, sync the party, and let the queue drain. The guide focuses on the
   lowest synced player's progress. Missing profiles or snapshots are called
   out before judging readiness. A recommendation is a heuristic, not a promise
   of efficient XP gains or pickup availability for every member.
2. Click **Show route** on a recommended questline, hub, zone route, or library
   quest. The first native user waypoint is set and the map opens. Hover numbered
   pins for steps and source notes. If the canvas is unavailable, the destination
   waypoint still works and diagnostics explain why lines are absent.
3. Accepting a quest switches from pickup to an objective. A finished active
   quest switches to turn-in. Turning it in follows the next party member who
   still needs that quest; after everyone finishes, the guide can advance an
   eligible known series or clear an exhausted route. Missing snapshots retain
   dimmed last-confirmed markers. Combat changes apply after combat ends.
4. Use **Quest library** to browse another zone or search a name. Browsing a zone
   requests party history for that area. **View details** explains known
   restrictions, previous steps, and coordinates that are still missing. Choose
   a level bracket, then press Enter or pause typing to search; page through
   larger result sets with the arrows.

Routes are capped at 20 stops. A nearest-next-stop heuristic mixes nearby quests
while preserving pickup → objectives → return for each quest. Nearby pickups
get preference so their objectives can be completed on the same trip. This
does not reserve future quest-log slots or solve the full prerequisite graph. A cross-zone
stage ends that block's current-map drawing. Partial routes stop where objective
evidence is incomplete, and the legend labels them as partial.

Local circuit search considers up to 40 nearby anchors and 80 neighboring quests,
bundling close pickup/return hubs under a configurable map-distance budget.
Quests too high for the lowest synced player, uncertain objective locations,
profession quests and dungeon quests are excluded from these circuits. Class
quests are excluded by default, or labelled when enabled. When public map sizes
exist, walking estimates use distance at 7 yards/second before terrain/combat.
These are approximate circuits, not road pathfinding or optimal XP-per-hour plans.

The **Dungeons** tab lets you inspect all collections even when a popup is
inappropriate. Selected dungeon/prerequisite IDs get bounded party history
checks. Pickups in the current zone come first; a known entrance in another
zone can follow when its public world position is within 2,500 yards on the
same continent. An unknown or distant entrance never becomes a fabricated
destination. Missing prerequisites/locations make the collection route partial.
Recorded entrances are your saved observations; re-record if beta geography changes.

Activity prompts wait for party profiles and completion checks. They appear
once per character and collection/transition; settings can disable them.
Nearby next-zone suggestions require a published previous quest completed by
every eligible party member, a known next pickup, and compatible public world
positions within 2,500 yards. They are offered when few compact local options
remain. No suggestion promises pickup eligibility or better XP gains.

**Professions** is separate from party leveling plans. Open your profession
window, select this tab, and use **Refresh recipes**, then choose the live guide.
It considers up to 400 recipe IDs, confirms learned recipes can raise skill,
and compares materials for up to 24 candidates; 12 choices are displayed.
Choose a small craft batch and refresh as recipe difficulty changes. Unknown
materials/costs are labelled. Reagent alternatives are estimates: verify the
chosen item/quality. Recipes, bag stock, material plans and observed AH prices
stay on your client; profession quests already in a quest log can still appear
in ordinary party quest comparisons. Profession quest guides draw personal
routes and do not wait for friends' profession progress. This does not provide
a complete static skill-level/trainer path for every profession.

Auto-accept requires both its setting and a present `AcceptQuest` function.
It only attempts the currently opened quest-detail dialog, once per dialog,
outside combat; it does not select gossip entries, turn in or share quests.
If the beta blocks the action, turn the setting off and report the operation.

Dungeon XP/boosting efficiency, full prerequisite solving, globally optimal
travel, and automatic sharing are not implemented. Completion history alone
cannot establish pickup eligibility.
The addon informs players and does not automate combat decisions.

## Comparing and syncing progress

**All quests**, **Shared**, and **Different progress** keep party members side
by side. `1 / 2` means one of two synced players has the quest active. A detected
member without a received snapshot remains waiting and does not count as synced.
Normal party-message synchronization does not require the same zone. Position
reads and destinations still depend on the client APIs.

Sync is automatic after party roster, quest-log/objective, level, and zone
changes, with a two-second batching window before the paced queue. `/wt sync`
forces a fresh check; repeated manual requests are unnecessary during normal play.

Cells distinguish **Active**, **Ready to turn in**, **Quest giver offered**,
**Completed**, and **Not in log**, with a separate history line. Negative history
requires matching completed-ID and checked-ID snapshots. Restricted or unqueried
results remain pending, and negative history must be at least as recent as the
active snapshot. Current NPC offers take precedence over past completion,
including repeatable quests. Offers clear when the dialog closes; learned
encounter locations remain.

Titles come from local logs, peer logs, the catalogue, and learned guides.
History checks cover active/learned IDs, relevant party zones, and zones being
browsed. The addon does not export every character's entire history. Catalogue
scope is bounded to 512 IDs, including known series dependencies. Destination
packets require matching active-snapshot revisions and trusted roster senders.
Departed peers are removed.

The overlay reads `C_QuestLog.GetQuestObjectives` only when present. Public
objective text, flags, and fulfilled/required counts are synced in bounded
packets tied to the active snapshot. Up to 12 objective slots per quest are
supported, two per packet. Restricted slots retain their positions to avoid
comparing different objectives. Objective counts arriving before the active
snapshot remain hidden until that revision is received. Reloads trigger at
most three targeted snapshot repairs per detected peer.

Transfers are party-only: at most 64 parts of 18 IDs per snapshot, 96 learned
guide records and 96 live destinations per client, and 256 queued messages.
Sends start one second apart. Throttling can increase the delay to 16 seconds,
with at most five retries per packet. Successful sends gradually reduce the
delay; unchanged automatic updates are suppressed. Catalogue history sync can
take longer than older quest-log-only updates.

## Beta validation

The user verified quest/title/history sync and level/faction/map context with
**0.2.0 on build 70205**, interface **16001**, project **18**. Their 0.3.0 reports
showed route lines on one client and a cleared route/missing active snapshot on
the other. Their **0.4.0 reports on build 70205** show objective details on both
clients, incoming peer objective snapshots, matching quest/history sync, and
routes with 16 pins / 20 lines. The screenshot exposes map presentation issues
addressed in 0.5.0; its actual rendering still needs a beta check. The native
waypoint action worked. Compatibility never depends on project ID alone.
New recipe, AH, map-link/world-position, NPC fallback and auto-accept behavior
remain unverified in the beta. API presence does not establish working behavior.

1. Update both clients, `/reload`, sync, and wait for the queue to drain.
2. In Durotar, click **Show route** for a quest with coordinates. Check numbered
   pins and lines, then zoom, pan, and resize the map. A shared pickup/return
   location can display `1/3`.
3. Accept the same item-drop/kill quest on both clients. Compare the overlay
   after each objective changes; it should show each person's own counts.
   Turn it in on one client while the other still needs it. The remaining
   member's objective/turn-in markers must stay until their completion arrives.
   Repeat with three players and scroll through all tracker objectives. Try
   **Settings → Tracker background → Clear** and different tracker heights.
4. If lines are absent, copy `/wt probe` after the map click. Include **Map route**,
   **Rendered route pins / lines**, **Local quest destinations**, **Route location
   read status**, and UI map/class/race IDs. New capability probes include
   `GetNextWaypoint`, `GetQuestsOnMap`, `IsComplete`, `GetCanvas`,
   `AddDataProvider`, and `Frame.CreateLine`. For the tracker/NPC hints include
   `GetQuestObjectives`, `GetNamePlateForUnit`, `UnitGUID`, local objective
   details/restrictions, peer objective snapshots, and NPC hint status.
5. Use **View details** on a quest without coordinates, browse another zone, and
   confirm paired history arrives. Missing objectives must not send an active
   character back to its pickup NPC.
6. Check deferred map selection, updates, and clearing in combat. Test a third
   synced player, leaving/reforming the party, reconnecting, and a member without
   the addon remaining waiting. Reload the route's focus player; confirm dimmed
   markers stay during recovery. Enable enemy nameplates and approach a published
   target; public NPC IDs may show an icon out of combat, then hide in combat.
7. Check window/minimap persistence and Ctrl+C copying. Restart fully if a new
   addon folder is absent. Persistence failures can also be beta client behavior;
   report the build in use.
8. Select a **Local XP circuit**. Confirm pickups precede objectives and grouped
   turn-ins, routes stay local, and listed rewards do not promise actual XP.
   Inspect **Buy list** on a quest with published vendor-listed requirements.
9. In **Dungeons**, inspect nearby collections. Test the level prompt, current-zone
   pickups before the entrance, prerequisite checks, and the last party member's
   completion. If the entrance is unknown, record it while standing outside.
10. Open your profession window, refresh **Professions**, choose a guide and
    batch, and inspect materials. If APIs are missing, use personal profession
    quest guides and copy the capability report. Make a commodity AH search
    yourself to test public price updates. Private data stays unknown.
11. Auto-accept is off initially. Enable it in settings only to test an opened
    quest dialog, then confirm successful acceptance and no blocked-action report.
    Test known nearby questline transitions after party prerequisites complete.

The diagnostic probe does not place a waypoint. API presence and self echoes
do not prove behavior or peer delivery. Enable `/console scriptErrors 1` while
testing. Report Lua errors, failed sends, or blocked-action reports with the
operation and both clients' diagnostics.

## Host checks and data imports

With Python and `lupa==2.8`:

```sh
python3 -m venv /tmp/wow-together-tests
/tmp/wow-together-tests/bin/python -m pip install lupa==2.8
/tmp/wow-together-tests/bin/python -m unittest discover -s tests -v
```

Tests load all 18 Lua files in TOC order under Lua 5.1. They cover sync, history
pairing, names, secrets, throttling, UI controls, ranking, requirements,
revision-bound destinations, route stages, cross-zone/partial routes, map
geometry, resizing, party route completion, snapshot repair, tracker scrolling,
objective counts/revisions/secret values, guarded NPC hints, combat deferral,
local XP circuits and phase ordering, opt-in acceptance guards, dungeon collection
and completion, nearby zone transitions, personal recipe/material plans,
observed AH prices, alternate NPC targets, vendor buy lists, and source parsing.
Synthetic fixtures are not shipped as game data. Mocks do not establish real
beta rendering or protected-action compatibility.

To regenerate the snapshot outside the game:

```sh
python3 tools/import_warcraftdb.py --refresh
python3 tools/import_wowhead.py --all-categories --detail-level-max 30
```

Tools use paced reads and a `/tmp` cache. Remove relevant Wowhead cache files
before refreshing those pages. The Wowhead importer needs the Warcraft DB cache
for map-ID evidence and accepts repeated `--zone` arguments for narrower zone
lists. Embedded JSON is parsed without executing website JavaScript.
`QuestCatalogue.json` records coverage. No HTTP requests run inside the addon.
`--cached-details` processes accessible cached details without requesting new
detail pages. Repeated detail-page HTTP 403 responses stop further new detail
requests; the import continues using cached pages and list facts.

Build the complete release ZIP with `python3 tools/build_release.py`. It includes
every TOC-listed Lua file, the coverage summary, README, install notes, and license.
