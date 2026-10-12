# Badlands quest guide review — 10 October 2026

This review refreshes the supplied 8 October 2026 / 0.8.59 audit against the
current `guides/coverage` branch (0.8.66, source head
`7c600807f6f9395d2320818b890386c7a6831c54`). The main checkout was not changed.
Guide order and shared engine are unchanged.

## Scope and evidence

The Badlands category contains 44 catalogue records and five existing guide
sections: Alliance and Horde 31–40, Alliance and Horde 41–50, and Horde 51–60.
The standard `audit_quest_guides.py --zone Badlands` filter matches 38 records
whose home `zone` field is exactly Badlands (113 source points). A temporary
category-path audit covers all 44 records (128 source points). Quest 736 is an
Undercity record reached by the Horde Badlands guide. Both scope reports are
preserved here; see `source-facts.json` for captured Forever pages, SHA-256
hashes, parsed item-to-NPC links and coordinates.

The pinned QuestieDB Forever factual source is revision
`e0a6eaa86f181ac99262e34126bcd2ed1a1712d6`; its Forever quest database
SHA-256 is recorded in the evidence file. Captures are dated 10 October 2026.
Wowhead pages and comments were used to cross-check entity relations; their
prose was not copied into guide steps.

## Data changes

- **Prospect of Faith (723):** retain the confirmed 722 handoff and represent
  723 as taking Hammertoe’s Amulet to Prospector Ryedol. No independent farming
  objective is added.
- **The Star, the Hand and the Heart (735 Alliance / 736 Horde):** map all three
  required items to Grel’borg the Miser (2417), Dagun the Ravenous (2937) and
  Mogh the Undying (1060), with published spawn alternatives. Preserve the
  distinct faction quest IDs, 727 / 728 prerequisites, Horde race mask and
  Elite type. Additional pickup conditions remain unverified.
- **Terror of the Desert Skies (78823):** map Primitive Drawing (211269) to all
  11 published Badlands mob sources and 36 captured positions. Hemet Nesingwary
  (715) is the mapped hand-in. No verified starter or acceptance mechanism was
  found, so the guide does not invent one.
- **Liquid Stone (715):** retain the separate Lesser Invisibility Potion
  requirement and add seven published Badlands Solid Chest (object 2857)
  alternatives for Healing Potion. The potion acquisition gap remains. The
  pinned Forever record says Alchemy skill line 171, minimum 0, so this
  profession quest stays in the catalogue but is excluded from ordinary
  leveling routes.
- **Stone Is Better than Cloth (716):** retain Patterned Bronze Bracers (2868)
  as required; no supported local acquisition point was found.
- **Badlands Reagent Run II (2203):** retain Horde eligibility, three Vessels
  of Dragon’s Blood from Scorched Guardians, and predecessor 2202. The pinned
  record requires Alchemy 210, so it stays available in the catalogue but is
  excluded from ordinary leveling routes. Wowhead comment 53995 independently
  describes it as Alchemy-only. Other offer conditions remain unverified.

No routing, eligibility engine, guide lifecycle, travel or UI code changed.
The exclusions use the existing quest data mechanism.

## Coverage and complete-route comparison

The five direct-zone source reports check 113 points, and the expanded
category-path audit checks 128. The standard audit continues to track missing
stage data for the unmapped 715 potion and 716 bracers; 723 / 735 / 736 stage
gaps are resolved. Quest 78823 still lacks a verified starter. These source
counts include catalogue facts for profession quests even though 715 and 2203
are omitted from ordinary route actions.

The full-flow comparison uses identical quest scope: both the pre-review
catalogue and reviewed catalogue exclude Alchemy-only quests 715 and 2203. All
five chapter flows are valid. They retain the same action count and XP/log
metrics; mapped items reduce unknown-location steps. Added distant item
locations increase the estimated distance for the two 31–40 chapters. Distances
are approximate graph estimates, not measured terrain paths or an optimization
claim.

| Guide | Actions | Estimated distance, before → after | Quest-log peak | Reward XP before work | XP shortfall | Uncertain legs, before → after | Unknown locations, before → after |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Horde 31–40 | 43 | 177,965.38 → 207,965.38 | 3 | 270,870 | 496,350 | 21 → 21 | 3 → 1 |
| Horde 41–50 | 56 | 171,569.03 → 171,569.03 | 2 | 493,250 | 632,050 | 19 → 19 | 1 → 1 |
| Horde 51–60 | 12 | 29,936.33 → 29,936.33 | 2 | 26,000 | 577,700 | 3 → 3 | 0 → 0 |
| Alliance 31–40 | 63 | 247,665.61 → 277,665.61 | 3 | 562,600 | 435,100 | 37 → 36 | 4 → 1 |
| Alliance 41–50 | 87 | 237,335.47 → 237,335.47 | 4 | 1,075,960 | 625,050 | 43 → 42 | 2 → 1 |

## Validation

- `audit_quest_guides.py --zone Badlands`: 5 guides, 113 direct-zone source
  points; planner and prerequisite invariants pass.
- Expanded category-path audit: 44 records, 128 source points; invariants pass.
- `audit_quest_flow.py --zone Badlands`: all five complete chapter flows valid.
- Focused Badlands, routing, addon and interface-16001 host tests: **93 passed**
  under Lua 5.1.
- Host checks cannot establish live beta quest offers, spawn availability,
  native map rendering or route safety.

## Player checklist

1. On Alliance, complete the Hammertoe chain through 722, then confirm 723
   delivers the amulet to Prospector Ryedol. Check 727 before 735, the three
   item hand-ins and the elite encounter.
2. On eligible Horde races, complete 728 before 736. Confirm the separate quest
   ID, three item sources, elite warning and actual pickup offer.
3. Check whether 78823 is accepted from a mob drop, item-use interaction or
   NPC. Test reported mob areas and confirm the Hemet hand-in in Stranglethorn.
   Record character level, faction, race and client build with any offer.
4. For an Alchemist, test 715’s chest objective and both potion requirements;
   separately validate 2203 at Alchemy 210 after 2202. Check 716’s bracer
   source. These profession quests are not ordinary leveling route actions.
5. Check fresh and mid-zone characters, class-quest setting, race/faction
   variants, chapter transitions, Scan Guide, reload, zone entry, deferred
   pickups and personal skips.

## Remaining unknowns

- The starter and acceptance conditions for 78823.
- Where to obtain Lesser Invisibility Potion for 715 and Patterned Bronze
  Bracers for 716 in this Forever build.
- Further pickup conditions for 735/736 beyond 727/728, and for 2203 beyond
  its published predecessor and Alchemy rank.
- Current native beta offers, Kargath access route, spawn behavior and safe
  ground paths. Player observations are needed before treating these as
  verified.
