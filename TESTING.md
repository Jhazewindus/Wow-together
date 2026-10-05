# Wow Together — friend test script

For **0.7.7**, World of Warcraft: Forever beta, interface **16001**.
Allow **45–60 minutes**. Each tester reports Pass / Fail / Skip with a reason.
Keep tester names and reports separate; label the main developer's report.
The Lua-pane patch checks below take about **2–5 minutes**.

## Install and capture context

1. Replace the complete WowTogether folder, including **all 40 Lua files**, in
   `World of Warcraft\_classic_beta_\Interface\AddOns\WowTogether\`.
   `/reload`; restart fully if a new addon folder does not appear.
2. Enable `/console scriptErrors 1`. Record version, build, level, faction, class,
   race, zone, party size and relevant settings. Update every party member.
3. Leave **Follow fixed zone guides**, **Record NPC offers and quest progression**
   and **Use observed prerequisite patterns** on. Source names in exports are
   optional and off by default. Recording never uploads automatically.

## Focus checks for 0.7.7

- **Open and paste:** enable script errors, then open /wt lua. Opening and typing
  should produce no Lua errors. Paste a multiline check, then a long wrapped line;
  scroll through the input and run it. Repeat with the console reopened.
- **Output and clear:** run the check below. Scroll through the output, use Select
  output and Ctrl+C, and confirm the final return is included. Clear should leave
  an empty usable output pane; a short subsequent result should display normally.
  Results should stay in this pane. Include any error and /wt probe in your report.

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
