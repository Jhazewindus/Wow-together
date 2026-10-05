# Report review for 0.6.0

## Evidence and labels

| Source | Captured character/context | Observations |
| --- | --- | --- |
| Main developer (user-labeled) | Gavin Bavin; solo, level 4, Horde, Durotar; 3 active quests; no selected route | Settings/instructions/scan need improvement. The level-25 Barrens example is a proposed case, not this diagnostic's character. |
| Friend's written Barrens report and Kobiee diagnostic | Written level 25; diagnostic level 26 Shaman, Horde, Barrens; solo, 6 active quests, 12 objectives | Early-zone recommendations, a selected step changing after acceptance, cross-zone objective detours, travel/corpse requests. Preserve the written/diagnostic level difference. |
| Additional supplied diagnostic | Vaiana Motonui; solo, level 22 Druid, Horde, Undercity; 3 active quests, 4 objectives; selected Barrens route | Supports checking retained routes across zones; no additional authored feedback inferred from the diagnostic. |

All captures report addon 0.5.7 and client 70205/interface 16001. Their captured
solo state cannot prove a party catch-up or last-player completion defect.

## Agreement and resolved conflicts

Overlapping requests: level-appropriate useful chains, focus on lagging party
progress, stable selected steps, an actual progress replan, clear Kill/Pick up/
Talk instructions, flight suggestions, Classic-style organized controls.

The user resolved the early-chain priority conflict: **catch up through useful
chains and explain low-level exceptions**, rather than always replaying a zone.
The repeated repeatable-quest feedback was explicitly withdrawn as already fixed;
retain the existing filter without claiming a new repeatable correction.

Other requests covered: previous/next previews; selectable distance units;
current-quest inclusion choice at guide start; NPC offer evidence; item/NPC
crosses; panel visibility for party/solo/raid; renamed quest views; dungeon
Start route; quest-log review suggestions; corpse directions. Professions stay
personal. Route invitations retain Follow route / Keep my route.

## Causes and limits

Code inspection established that recommendation refresh could replace a selected
route with the current-log bundle, and Scan retained its old selection while
showing counts. Both paths changed. Low-level discovery now needs a known useful
follow-up, while explicit active work remains selectable. Public NPC gossip is
availability evidence; IsPushableQuest is sharing support and cannot establish
pickup eligibility or hidden prerequisites.

Host tests use synthetic Lua 5.1 APIs; they establish regression behavior rather
than live beta compatibility. New flight-network data, optional native actions,
corpse coordinates, tooltip hooks and visual layout need the 0.6.0 checklist on
the actual client. Complete prerequisite, objective and flight graphs are not
available in this snapshot. Flight suggestions use observed public networks and
labeled straight-line/timed estimates, not obstacle-aware routing.
