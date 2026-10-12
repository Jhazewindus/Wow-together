# Arathi Highlands quest guide review — 2026-10-10

This review refreshes the supplied 0.8.59 / 8 October 2026 lead list from the
current `guides/coverage` branch on main’s 0.8.66 base (`2240f4b`). The guide
scope is Eastern Kingdoms Arathi Highlands, chapters 31–40 and 41–50. Chapter
labels are not minimum gameplay levels. The fresh pre-change scoped audit
compiles four faction/chapter guides and checks 169 source points; after the
corrections it checks 171.

## Changes

- **Anyone Can Cook (79624)** remains available to both factions (level 40,
  minimum 32). Its item, Illegible Recipe (213422), is confirmed on nine ogre
  types: five Boulderfist types in Arathi and four Crushridge types in Alterac.
  Their Wowhead Forever NPC pages provide 22 mapped search points. The guide
  keeps the existing local Boulderfist Brute point and stores the other points
  as alternatives, so players need only loot one recipe. Neither the quest nor
  item page identifies a quest giver; its pickup remains an audit gap.
- **Silky Sutures (97539)** is Horde-only, level 36/minimum 30. The page
  confirms 12 Surgical Spidersilk from Plains Creepers or Giant Plains
  Creepers. It starts at Doctor Gregory Victor and says to return to him;
  NPC 12920’s current map point fills the hand-in. Its follow-up remains gated
  behind completing and handing in 97539.
- **Ward Restocking (92519)** is Horde-only, level 36/minimum 30, and follows
  97539. Its page says to pick up Packaged Tonics at Jorell’s lab in Go’shek
  Farm and return them to Doctor Gregory Victor. The mapped return is added.
  The page does not identify who offers the quest, and the item page has no
  source map; both pickup location and objective point remain explicit gaps.
  Apothecary Jorell’s NPC location is not substituted for the tonic location.
- **The Giant in the Den (92707)** is Horde-only, level 33/minimum 30. One
  Goliath’s Wristguards comes from Witherbark Goliath (NPC 218032), whose
  objective is already mapped. The page directs the player to Drum Fel in
  Hammerfall; NPC 2771’s map point now fills that hand-in. The pickup giver is
  not identified. The target is level 35 and classified elite, so this quest
  uses the existing party warning and Skip quest choice.

Existing faction hubs, Stromgarde quests, chapter coverage and fixed guide
orders remain in place. The Horde and Alliance Stromgarde branches continue to
show their existing elite warnings and skip choices. No quest in the scoped
Arathi chapters is classified as a dungeon quest. Thoradin’s Wall remains a
separate optional chain/handoff category; it is not turned into an Arathi
leveling region or used to send ordinary Arathi players on an unsupported
cross-zone route. No runtime routing, lifecycle or UI code changed; the one
importer change allows a reviewed stage correction to preserve the existing
elite warning classification.

## Refreshed audit and remaining gaps

The current guide audit checks 4 faction/chapter guides. All four have valid
host-side guide state transitions. Full action counts are unchanged. The
recorded stage gaps shrink from 8 to 5:

| Guide | Quests / actions | Before gaps | After gaps |
| --- | ---: | --- | --- |
| Alliance 31–40 | 25 / 87 | pickup 79624 | pickup 79624 |
| Alliance 41–50 | 14 / 46 | none | none |
| Horde 31–40 | 40 / 131 | pickup 79624, 92519, 92707; objective 92519; hand-in 92519, 92707, 97539 | pickup 79624, 92519, 92707; objective 92519 |
| Horde 41–50 | 22 / 70 | none | none |

Three hand-in gaps are closed: Doctor Gregory Victor for 92519 and 97539, and
Drum Fel for 92707. The uncertain 79624/92519/92707 pickups and 92519 objective
point remain visible in the global source queue. The refreshed complete audit
and exact remaining queue are stored in the generated project reports.

## Full-route comparison

The full-flow captures preserve the same actions and endpoints for all four
guides. Horde 31–40 estimated distance changes from 309,886.14 to 291,302.16;
quest-log peak remains 6; reward XP available before objective work remains
1,960,405; reward-only XP shortfall remains 309,165; uncertain travel legs fall
from 34 to 30. Its unknown route locations fall from 7 to 4. The other three
guides have unchanged estimates and state metrics. This is an estimated full
route comparison after resolving mapped hand-ins, not a walkable-terrain or
safe-road claim. The route captures retain the complete action sequences.

The complete before and after artifacts are [`audit-before.json`](audit-before.json),
[`audit-after.json`](audit-after.json), [`flow-before.json`](flow-before.json),
and [`flow-after.json`](flow-after.json). Source URLs, response hashes, parsed
facts, all 22 recipe source points, and unavailable Warcraft DB records are in
[`source-facts.json`](source-facts.json).

## Dependencies and unresolved facts

- `92519.previousQuest` remains 97539, so the follow-up becomes available only
after the prior quest is actually completed and handed in. The series evidence
and matching Doctor Gregory Victor endpoint support that chain; the 92519 page
still does not identify its offer NPC.
- 92519’s prose identifies Packaged Tonics at Jorell’s lab, but the linked item
  page has no mapped source. The nearby NPC point is not evidence of the pickup
  object or its exact work coordinate.
- The captured pages provide no start relation for 79624 or 92707. Do not infer
  that Skonk or Drum Fel is their giver from their return instructions.
- Warcraft DB Forever’s detail API returned no record for 79624, 92519 or
  92707; its 97539 record independently confirms the level, item quantity and
  return instruction. Wowhead page captures include comment controls but no
  rendered comment bodies; no comments were used as evidence.
- Points do not establish cave/settlement approaches, hostile crossings, live
  beta offers, or travel access. No terrain shortcut was added. No shared
  engine or eligibility change is pending from this zone.

## Validation and player checklist

- Host validation used Lua 5.1 (`lupa` 2.8), interface 16001. The relevant
  suite `test_arathi_coverage test_routes test_importers test_lua_console
  test_addon test_0866` passed all 109 tests. The full catalogue audit checked
  152 guides and 11,842 source points; the remaining source queue has 362
  quest records, down from 363.
- The full-route and scoped guide audits pass all four guide invariants. They
  cannot establish actual beta map rendering or quest offers.

Before relying on these corrections in the beta client:

1. Check fresh Alliance and Horde characters in both chapters. Confirm 79624’s
   actual offer source for each faction and whether each listed ogre drops the
   recipe in this build.
2. On Horde, complete and hand in 97539, then confirm whether Doctor Gregory
   offers 92519. Find and record the exact Packaged Tonics object and position
   in Jorell’s lab, then turn the item in to Doctor Gregory.
3. For 92707, record the actual quest giver, party difficulty for Witherbark
   Goliath, wristguard drop, Drum Fel hand-in and whether the in-guide warning
   and Skip choice behave correctly.
4. Check the Refuge Pointe/Hammerfall and Stromgarde approaches, including
   group/elite choices, without inferring safe roads from map points. Confirm
   the Thoradin’s Wall handoff remains optional.
5. Check fresh and mid-zone progress, class-quest setting, Scan guide, reload,
   zone re-entry, chapter transitions, temporary offer deferrals, manual skips,
   and that accepted unfinished work cannot produce false completion.
