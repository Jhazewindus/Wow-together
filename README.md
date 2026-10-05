# Wow Together

A party quest guide for the **World of Warcraft: Forever beta**. Version
**0.6.2** targets interface **16001**, uses Lua **5.1**, and reads capabilities
rather than choosing a Classic implementation from `WOW_PROJECT_ID`.

Friends share their own active quests, completion checks, objectives and
public character context. The guide combines nearby work, preserves selected
routes and shows whose progress needs the next step. It also works solo.

## Install

Extract the release ZIP and copy the complete `WowTogether` folder to:

```text
World of Warcraft\_classic_beta_\Interface\AddOns\WowTogether\
```

Replace the folder on **every party member's client**, including all **28 Lua
files**, then `/reload`. Restart the client fully if a new addon folder does
not appear. Enable Lua errors with `/console scriptErrors 1` during testing.
No Battle.net credentials, external API service or in-game HTTP access is needed.

| Command | Action |
| --- | --- |
| `/wt` | Open the resizable dashboard. |
| `/wt config` | Open settings grouped by purpose. |
| `/wt tracker` | Toggle the movable, scrollable party progress panel. |
| `/wt arrow` | Toggle the movable direction and instruction panel. |
| `/wt guide scan` | Refresh real progress and replan the selected guide. |
| `/wt research` | Open a copyable local quest-data export for prerequisite research. |
| `/wt guide reset` | Clear all saved guide skips for this character. |
| `/wt sync` | Request fresh party snapshots; let the send queue drain. |
| `/wt probe` | Open diagnostics; Ctrl+C copies and closes the report. |
| `/wt route clear` | Clear the selected map route. |
| `/wt minimap` | Toggle the minimap button. |

## Choose and start a guide

The dashboard dropdown contains **Leveling guides**, **All quests** (the old
Library), **Party quests** (the old All quests), **Shared**, **Party progress**,
**Dungeon quests**, **Profession guides** and **Quest log review**.
All quests supports level brackets, Near party and search committed on Enter
or after a typing pause. It retains manual browsing of known repeatables.

**Leveling guides** lists real zone guides and published questlines across the
catalogue, including remote zones. Its default bracket follows the lowest party
level (1–10, 11–20, etc.). Choose another bracket or All levels, and search by
zone, quest or known NPC; Enter or a short pause applies the search. Pages keep
later results accessible. Individual quests stay in All quests, and explicit
quest-log trips are in Party quests.

A bracket filters the browser; it does not cut a selected guide down to that
bracket. The guide retains later quests and published cross-zone chain steps.
New pickups still require suitable levels, faction and known progression. A
full guide selects the next nearby trip rather than drawing every future stop.
The arrow shows **Loading route…** while cooperative route generation compares
dependency-ready walking orders. Trips hold up to six quests and twenty stops;
pickups precede their work and returns. This is a bounded straight-line optimizer,
not a guarantee of the globally shortest road route.

As useful work leads into a suitable nearby zone, an optional popup offers
**Start zone guide** or **Keep my guide**. For example, a known Durotar chain can
continue toward the Barrens while the full Barrens guide is offered. The same
catalogue, level, faction, progress and adjacency checks apply to other zones;
there is no special Durotar/Ashenvale route script. Missing links or locations
remain unknown, and a popup never changes the guide by itself.

**Show route** previews a selection locally. **Start route** starts it and
invites friends with **Follow route** / **Keep my route**. Their route stays
unchanged until they choose to follow. Invitations share selected quest IDs
and pickup roles, up to 20 IDs; each recipient plans against received party
progress rather than copying the sender's coordinates or completion flags.
Full zone/questline invitations also identify the guide and browser bracket,
so recipients reconstruct its full catalogue scope beyond the twenty packet IDs.
Update all clients together to use these new invitation modes.

When you start a new guide while quests are already in party logs, choose
**Start selected guide** or **Include current quests**. The popup explains
that including scattered current quests can cause unusual routes and long
detours. The former global current-quests-first switch is no longer exposed.
Quest-log plans remain available without replacing an explicitly chosen guide.

Normal quest acceptance and zone updates retain the selected quest set.
A committed unfinished objective stays selected while crossing a zone.
**Scan guide** is the explicit way to refresh that selection and optimize it
again. Ready turn-ins and unfinished friends' work remain separate stages.
Arrival alone never accepts, completes or hands in a quest.

## Planning and party progress

- New leveling pickups use the lowest published party level and known faction,
  class, race and completion requirements. Discovery favors the current zone
  and suitable known neighbors. Opposing-faction starters and distant unlinked
  zones do not become automatic recommendations.
- Low-value pickups are excluded. An earlier quest can remain when a known
  useful follow-up or a suitable dungeon quest justifies it; the arrow explains
  the exception. Accepted work explicitly included by you can remain below
  that range. Unknown follow-ups cannot justify a low-level detour.
- Among members with comparable known history, the guide focuses on the member
  furthest behind in its selected quests. Unknown history does not prove a
  player is behind. The lowest level is the fallback; missing snapshots retain
  confirmed stages while sync catches up. A downstream prerequisite cannot be
  treated as done because a more advanced player already completed it.
- Eligible nearby pickups can join a quest-log trip. The original walking
  budget limits additions rather than expanding repeatedly to distant quests.
  Pickups precede their objectives and returns; local work precedes long delivery
  detours. Disable **Collect useful quests nearby** for a strict log-only plan.
- Known repeatables stay outside automatic leveling plans. Group/elite quests
  are labeled and excluded from automatic solo discovery. Class quests are an
  optional inclusion with restrictions; profession quests remain personal.
- **Quest log review** suggests reviewing low-value unfinished work. It never
  abandons a quest. Ready turn-ins and class/profession quests are not included
  in those suggestions.

Sync is automatic on party, quest/objective, level and zone events, batched
before a paced send queue. It suppresses unchanged updates and retries explicit
throttle responses. Successful sends or self echoes do not prove peer delivery.
Diagnostics distinguish peers waiting for snapshots from received progress.
Party identity supports public first-name/surname forms found in this beta;
ambiguous sender matches are rejected.

The progress panel shows personal item/kill counts for each player. It opens
when joining a normal party, hides when solo or in a raid, and can be dismissed
for the current party session. Its background and height have clear dropdowns.
A completed player does not erase another participant's remaining objective.

## Arrow, map and guide controls

The Classic-style panel shows the quest, arrow, distance, action and two small
context lines. Actions distinguish **Kill**, **Pick up** and **Talk to [NPC]**.
Choose yards or metres in **Arrow and travel** settings.

The left/right buttons preview prior and later steps without changing quest
credit. Already accepted pickups and completed quests can supply previous
published locations, labeled **History preview**; these do not establish the
order in which a player actually visited them. Visited guide steps are also
kept for the current session.

**Skip step** and **Skip quest** persist per character. They do not unlock
prerequisites or change friends' progress. **Scan guide** reads actual quest
logs, objectives and completion history, then rebuilds the useful plan and
returns to its current step without a report popup. History scope includes
known series and prerequisites and is bounded to 512 IDs. Restricted values
remain unknown; peer history waits for received snapshots.
There is no extra "Guide replanned" footer below the arrow controls.
Diagnostics distinguish full guide quest counts, trip quest counts and stops:
one quest can supply pickup, objective and turn-in stops, so eighteen stops do
not mean eighteen quests. Completed progress and missing coordinates also
affect each trip; compare the guide identity and scope before comparing counts.

**Reconsider skips when scanning** is off by default. When enabled, Scan clears
skips for quests in the selected guide before replanning. A quest shared with
another guide has the same saved skip. **Reset guide skips** clears every guide's
skips for this character, across zones; other characters are unaffected.

World-map lines show visiting order, with the current place and two ahead by
default. Map controls choose zero/one/two places ahead or the full route.
Consecutive steps at a shared NPC stay grouped. Hover clustered pins for all
steps. Viewing another zone preserves the route; **View route zone** opens its
current destination map. No segment joins unrelated zone coordinates.

Drawing projects onto the public map viewport, clips at its edges and redraws
after pan, zoom and resize. Existing verified unprotected addon geometry can
redraw in combat; protected frames and native map/waypoint actions defer.
**Lines are on the world map only.** The minimap icon opens the addon.
The addon no longer sets an extra Blizzard user-waypoint pin. Numbered route
markers and the owned navigation arrow remain; unrelated manual waypoints are
left alone. A pin left from an older release can be removed manually on the map.

Distances and routes use straight-line estimates. Follow roads and terrain;
this is not obstacle-aware pathfinding. Missing objective locations stay
explicitly partial instead of inventing targets or early turn-ins.

## Travel, NPCs and personal tools

Open flight-master maps to learn this character's network. When public flight
states and positions exist, the guide compares walking with getting to a known
reachable flight, flying and walking from its destination. It includes a
boarding allowance and suggests a flight only for meaningful estimated savings.
Flight times are estimates until that character has timed the route. While
flying, the panel shows elapsed time or an approximate remaining timed duration.

Observed nearby flight masters with unconfirmed unlocks can receive a short
check stop. This is not a complete flight-path database. Unknown reachability,
missing positions, continent mismatches or unsupported APIs keep travel manual.
**Select the suggested flight** is off by default. If enabled, it requests a
currently reachable native slot only when you open the matching flight master,
outside combat. Its protected-action behavior needs testing on your beta build.

While a ghost, the arrow temporarily directs you to a public corpse position
and retains the guide. A recorded death position is labeled approximate;
unsupported corpse data gives an explicit status. Recovering your body resumes
the guide. No release or resurrection is automated.

NPC observations can correct missing pickup gates: a public complete gossip
or quest-greeting list records what that giver offers for your current quest/level context.
Absence blocks a pickup only after all known givers were checked. A single
quest-detail dialog confirms that quest without claiming the list is complete.
Progress, level or reputation changes invalidate relevant knowledge; visit
again to recheck. This cannot discover every hidden prerequisite in advance.
Every pickup uses known level, faction, class, race and prerequisite rules.
Known prerequisite history is checked before positive NPC evidence: accepting
the earlier quest, completing its objectives or skipping it does not count as
handing it in. An alternative prerequisite needs one confirmed completion;
unknown/restricted history stays unknown. Actual offers can confirm missing or
unverified published requirements but cannot bypass a known unfinished prerequisite.
Without an NPC observation, a candidate is based on published data and may still
have a hidden beta requirement. Visit the giver to confirm it.

`IsPushableQuest` reports shareability and is no longer queried for pickups.
`IsQuestCompletable()` describes the currently opened NPC progress/turn-in
dialog; it is used only for optional turn-in, with no quest-ID argument. Neither
function is an arbitrary-quest pickup check. The old beta pickup setting and
packets are removed; update every client to avoid using the old interpretation.

Each client sends its own history and actual NPC offers. Peer offers are tied
to fresh quest-log context, and an empty list does not mean every quest is
unavailable. Automatic sync batches quest/turn-in/party/level/zone updates for
two seconds, including solo guide refresh. Locked quests stay in the full guide;
newly eligible nearby work can join the trip while its unfinished objective stays
first. Accepted work remains. Scan guide also rechecks. Diagnostics show candidate,
blocked and unknown counts plus sample per-quest reasons and NPC offer evidence.

Quest research is enabled locally in **Settings → Quest data for testing**.
Each character retains the latest 300 observations across reloads: public NPC
offers (complete lists distinguished from individual dialogs), accepted quests,
turn-ins, build, level/class/race/faction/map and relevant completion-history
checks. Snapshots check at most 128 relevant IDs and mark history truncation.
Level and reputation-change events flag alternative explanations for unlocks;
no actual reputation standing or unobserved NPC offers are guessed.

Use `/wt research` or **Export quest data**, choose **Select all** and press
Ctrl+C. Save the JSON export as a text file and send it with your tester name
after a session; export before older observations roll off. Diagnostics shows
the retained/replaced count. Each friend exports their own character's data;
the export contains no character names, realms, chat or friends' histories.
Records are not sent through party sync or uploaded automatically. Disable
recording to pause collection; previous observations remain exportable.
Reloads and recording toggles mark a new capture segment so gaps remain visible.
Visit the same giver before and after hand-in for the strongest comparisons.
A missing planned pickup is recorded only for this character at a known giver
with a complete public list. Differences suggest prerequisite candidates; they
do not automatically create a dependency because levels, reputation, branches
and other quest changes can explain them. Retest capture APIs/events on the beta.

The greeting reader probes GetNumAvailableQuests/GetAvailableQuestInfo and
reads the quest ID from the fifth return, as documented by Mainline's native
QuestFrame. Missing or restricted fields cannot prove that a quest is absent.
Retest these optional APIs on Forever; Sting of the Scorpid's exact unpublished
gate is not inferred from a neighboring quest ID.

Needed public nameplates show a cross, or an optional skull for kills. A
finished mob objective loses its hint unless another unfinished objective or
participant still needs it. Known required-item tooltips get a cross and quest
name. Friendly givers can show quest names and a downward pointer. Hints hide
in combat and require public data; world objects without nameplates are not
universally marked. No raid-target icons or secure Blizzard controls are changed.

**Quest dialogs** contains separate opt-ins for opening the exact current guide
quest at a multi-quest NPC, accepting a dialog you open, and turning in completed
opened quests with no reward choice. All default off and defer in combat.
Reward choices remain manual. API presence or an attempted action is not proof
of success on the Forever beta.

**Dungeon quests** offers Start route for collection steps and a known nearby
entrance. Missing prerequisites and distant pickups are explained. If no client
map link locates the entrance, stand outside it and use **Record entrance here**.
Dungeon/next-zone prompts respect a selected quest-log trip.

**Profession guides** uses recipes from your own opened crafting window,
small configurable batches and required materials. Public auction prices come
only from searches you make; there is no automatic AH search, buying or crafting.
Known vendor-listed quest items have a buy list with your own bag counts.
Profession, flight-network and skip data are personal and are not sent to peers.

## Data and beta limits

The offline snapshot was captured **October 5, 2026** from public game facts in
[Warcraft DB](https://forever.warcraftdb.com/list/quests) and
[Wowhead Forever](https://www.wowhead.com/forever/quests).

| Coverage | Records |
| --- | ---: |
| Distinct quest records / category lists | 5,230 / 123 |
| Detailed pages | 1,366 |
| Pickup / objective-area / turn-in coordinates | 763 / 179 / 831 |
| Published series / prerequisite facts | 599 / 432 |
| Incomplete objective locations / known repeatables | 785 / 68 |

This is a partial catalogue, not every Forever quest or a complete prerequisite
or flight graph. Detailed reads now spread across outdoor categories through
level 60, retaining cached pages. Published legacy facts may differ from the beta. List metadata
does not establish current availability. Live active destinations take precedence;
area-table IDs are mapped to UI map IDs only with unambiguous shared evidence.
Coordinates lacking that join are preserved separately, and can resolve at
runtime only against an unambiguous matching native zone name. Localized or
missing names can leave them unknown. The generic guide engine supports every
zone present in usable catalogue data; it does not imply complete coverage of
all current or future beta zones. Unknown locations do not hide the entire guide.
Ambiguous faction, branch, class and race requirements remain unknown until
live evidence establishes availability.

No quest descriptions, artwork or third-party addon code are included.
[QuestTogether's public description](https://www.curseforge.com/wow/addons/questtogether)
provided broad inspiration about progress clarity; its code/assets/layouts
were not copied. This implementation is independent.

Reported beta build **70205** established the earlier sync APIs in user tests.
**0.6.2 has host validation, not a live-client compatibility certification.**
Retest UI rendering, optional gossip/flight actions, corpse positions and item
hooks on the build in front of you. `/wt probe` lists capabilities and runtime
status. Do not interpret presence as proof that protected actions work.
SavedVariables initialize in ADDON_LOADED; beta persistence failures may belong
to the client. No combat-log processing, secret arithmetic, secure snippets,
combat automation or replacement of Blizzard combat tools is used.

## Development and release

Host checks load all 28 Lua files in TOC order under Lua 5.1 through `lupa==2.8`:

```sh
python3 -m venv /tmp/wow-together-tests
/tmp/wow-together-tests/bin/python -m pip install lupa==2.8
/tmp/wow-together-tests/bin/python -m unittest discover -s tests -q
```

Mocks cover sync, secrets, snapshots, planner/chain policy, stable routes,
map geometry, party completion, UI controls, skips/scans, observed flights,
corpse directions and guarded actions. Synthetic fixtures are not shipped.
Run the actual-client checklist in `TESTING.md` and label your report as the
main developer or a named friend. Compare all reports before implementing;
resolve contradictory suggestions with the user first, as required by AGENTS.md.

Regenerate accessible source facts outside the game:

```sh
python3 tools/import_warcraftdb.py --refresh
python3 tools/import_wowhead.py --all-categories --world-details --detail-level-max 60 --spread-details --new-detail-limit 120
```

Importers use paced reads and `/tmp` caches without executing site JavaScript.
Repeated detail denials stop new detail requests; `--cached-details` processes
accessible cached facts. No requests run in the addon. `QuestCatalogue.json`
records coverage and `ZoneConnections.lua` keeps known map connections.

Build with `python3 tools/build_release.py`. Each completed addon release is
also posted with its matching changelog and test script:

```sh
python3 tools/build_release.py --post-discord
```

Store `DISCORD_WEBHOOK_URL` securely in environment settings. For an existing
ZIP, use `python3 tools/post_discord_release.py <archive> --prompt` for hidden
input, or `--dry-run` to preview without sending. The uploader extracts both
documents from the ZIP, disables mention pings, confirms all three attachments
and saves a nonsecret receipt. Identical contents are not reposted; changed
contents require a new version. Check channel history before retrying an
ambiguous delivery. Credentials never belong in addon files or archives.
