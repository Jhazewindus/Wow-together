# Ashenvale quest guide review — 10 October 2026

This refresh starts from the supplied 8 October 2026 audit and current
`guides/coverage` branch (0.8.66). The main checkout was not changed. The
scoped baseline was regenerated from the branch before reviewing; it finds 44
Ashenvale catalogue records, 126 static points and seven faction/chapter
sections. Exact audit output, matched-scope route reports and source captures
are retained here.

## Sources and decisions

Quest identity, level and prerequisite facts were checked against the pinned
QuestieDB Forever revision `e0a6eaa86f181ac99262e34126bcd2ed1a1712d6` (quest DB
SHA-256 `d5be8516877505334f02073826ea0f22a394ddbf604bb5a33f5a39de5bb1ee87`).
Current Wowhead Forever quest and entity pages were captured on 10 October;
`source-facts.json` retains URLs, response metadata and hashes. Captured page
prose was not copied into instructions. Community comments were treated only
as leads and cross-checks, not native beta observations.

- **Slowing the Orc Advance (86757):** add the Shandrina pickup and return, and
  map the two required items to Horde Scouts and Grunts with the captured
  objective work points. The chapter gains a complete pickup, objective and
  hand-in stage. Test the offers and actual drop areas in game.
- **Elemental Bracers (1016):** retain the five-bracer objective and both
  published Mystral Lake source NPCs. The separate Divined Scroll still has no
  verified acquisition stage, so the objective-location gap stays visible.
- **The Escape Through Force / Stealth (994/995):** preserve the shared 993
  prerequisite, record the explicit mutual exclusion, and retain each quest's
  separate event objective.
- **Silverwing/Warsong care packages (7863–7868):** preserve the three tiers
  for each faction, mark each pickup as offer-checked, and record the published
  Friendly reputation requirement in evidence. The addon does not model a
  reputation threshold; adding shared eligibility behavior requires main
  developer coordination. These are optional battleground packages.
- **Daily PvP quests (79090/79098):** retain their captured NPC returns and
  catalogue records, but exclude repeatable dailies from ordinary leveling
  chapters.
- **Seeking the Kor Gem (95042):** correct the race mask from the generic Horde
  mask to the current page's `reqrace=16` (Undead) and retain `classMask=2`
  (Paladin). Class quest visibility remains controlled by the existing
  setting. Keep the gem quantity unknown. The unusual race/class combination
  and actual beta offer require player verification.
- **Astranaar travel:** preserve the hostile settlement guard and existing
  route behavior. The supplied old partial report says only that a Horde map
  line crossed Astranaar and names no waypoint; it cannot establish a safe
  road. Quest markers remain independent of route lines.

The old Blackfathom quests 908 and 909 remain distinct from 6921 and 6922.
Captured comments do not establish that they are the same quest or support a
safe Horde pickup route. No shared routing, eligibility, guide lifecycle, or UI
code changed.

## Coverage and routes

The refreshed scoped audit checks the same 44 records and 126 source points.
The Alliance 31–40 section grows from 23 to 24 actions and its three
missing-location stages close with quest 86757. Other route stages remain
unchanged. Horde and Alliance daily-only 51–60 chapters disappear because their
remaining ordinary action count is below the existing guide publication
threshold; their quest records remain available in the catalogue. The five
remaining complete guide plans all pass the flow-state checks.

| Guide | Actions before → after | Unknown-location steps before → after | Quest-log peak after | Uncertain travel legs before → after |
| --- | ---: | ---: | ---: | ---: |
| Horde 11–20 | 6 → 6 | 0 → 0 | 1 | 0 → 0 |
| Horde 21–30 | 69 → 69 | 9 → 9 | 6 | 12 → 12 |
| Alliance 11–20 | 43 → 43 | 0 → 0 | 3 | 5 → 5 |
| Alliance 21–30 | 129 → 129 | 7 → 7 | 4 | 27 → 27 |
| Alliance 31–40 | 23 → 24 | 3 → 0 | 2 | 6 → 3 |

Distances are approximate graph estimates, not measured terrain paths or proof
of an optimal route. The host audit has no native map APIs and cannot verify
walkable paths, encounter safety, live quest offers, actual item drops, or beta
experience timing. Open objectives remain documented in `source-facts.json`.

## Validation

- `audit_quest_guides.py --zone Ashenvale`: 44 records, 126 points, seven
  baseline sections; five sections after the repeatable exclusions. Static
  planner and destination-reason invariants pass.
- `audit_quest_flow.py --zone Ashenvale`: five complete route plans pass their
  action-order and flow-state checks.
- Focused regression tests cover Ashenvale data, routing, addon behavior,
  interface-16001 host behavior, importer corrections, exclusivity, and hostile
  Astranaar travel.
- A player checklist is required because Lua 5.1 host checks cannot establish
  native beta behavior.

## Player checklist

1. On Alliance, check both 994 and 995 after 993; confirm the choices are
   mutually exclusive and verify the Force and Stealth objectives separately.
2. At Shandrina (3955), verify quest 86757 availability, both required item
   counts, the Scout/Grunt drop sources and the return offer. Record level,
   faction, race, class, completion history and client build.
3. At Mystral Lake, test both 1016 source NPCs and determine how the required
   Divined Scroll is obtained. Confirm drops, item use, and return NPC.
4. Check the three care package tiers at the correct faction NPCs and Friendly
   reputation; verify the addon defers absent offers. Confirm neither daily
   PvP quest appears as ordinary leveling work.
5. Check whether an Undead Paladin can accept 95042 in this beta build, verify
   the gem requirement quantity and drop sources, and confirm class quest
   setting behavior.
6. On Horde, investigate 908/909 independently from 6921/6922. Do not use an
   Astranaar crossing as a route until a player confirms a safe ground path.
7. Test fresh and mid-zone characters, chapter transitions, Scan Guide,
   reload, zone entry, deferred pickups, completed quests and manual skips.

## Remaining source gaps

- Quests 908/909: pickup, objective and hand-in sources are unresolved.
- Quest 1016: Divined Scroll acquisition and full objective coverage.
- Quest 1046: Dartol's Rod transformation/handoff point.
- Quest 6504: Shredder manual chapter acquisition points.
- Quest 98027: the necklace delivery interpretation needs direct item/quest
  evidence.
- Quest 98417: scroll acquisition area needs a precise current source point.
- Quest 95042: gem quantity and actual race/class offer need confirmation.
- Current route safety, terrain and offer behavior require beta observation.
