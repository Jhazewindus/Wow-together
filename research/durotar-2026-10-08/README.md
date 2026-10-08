# Durotar data review — 8 October 2026

See the [0.8.60 follow-up](refresh-0.8.60/README.md) for refreshed source checks, unchanged gaps and additional shared eligibility/handoff findings.

Baseline refreshed from main `67ff36412ede50154ec3a8b2aecb148e72ffb568`
(0.8.59), continuing `guides/coverage` after `e61c267`. The global baseline is
152 sections across 44 areas, with 33 sections having no recorded source gaps.
This review covers all 103 distinct quest IDs in the compiled Durotar scope.
The audit includes both Horde and Alliance entries for the 1–10 and 11–20
chapters. These templates include class branches and unknown faction records;
their existence does not recommend Durotar to Alliance players or establish
gameplay minimum levels. Character-specific class/race filters still apply.

## Supported changes

- **Call of Earth 1518/1521, Call of Fire 1524/1527:** the quest supplies the
  delivery item. Keep that item required for hand-in, show it as provided, and
  use the existing delivery-stage behavior at the receiving NPC. The short
  instruction names the NPC to speak to. No farming location is invented and
  no acceptance, work or hand-in action is removed.
- **Call of Fire 1525:** retain the Fire Tar work in the Barrens and add the
  explicit Reagent Pouch drop from Burning Blade Cultist in Durotar. The new
  work point uses the current NPC page's published spawn, at 51.8, 25.8. The
  existing instruction renderer names the item, quantity and mob. This point
  does not establish a cave entrance or a walkable approach.
- **Lost in the Shadows 99123:** identify the unmapped work as escorting
  Pal'juh. Both the Forever quest and official beta notes identify the escort.
  Keep its endpoint/path unknown, preserve its native completion check, and
  keep its acceptance and escort work adjacent. No quantity is assumed.

`tools/quest_corrections.json` stores the identity-checked stage rules and
provenance. They run after enrichment in both the full builder and supplemental
importer. `tools/apply_quest_stage_corrections.py` applies the same rules to the
existing packed catalogue without recapturing or changing unrelated records.
Conflicting identity, quantities, mapped work or location evidence fails for
review. Reapplication is idempotent.

## Evidence and unresolved facts

All 103 Forever quest pages were captured successfully. `page-facts.json`
retains selected typed facts from priority pages; `capture.json` retains the
whole inventory's URLs, capture dates and hashes. `entity-facts.json` retains
the nine inspected item/NPC records. All files in the pinned QuestieDB manifest
were downloaded and checksum-verified; `review.json` records changed facts and
the inventory. Downloaded scripts were not executed and quest prose is not
included. Existing attribution in `THIRD_PARTY_NOTICES.md` applies.

| Remaining issue | What the evidence establishes / what is missing |
| --- | --- |
| 785, A Strategic Alliance | The current page supplies no pickup, work or hand-in locations. The wiki describes an older Lar Prowltusk delivery, but does not establish current-beta availability or a starter. ClassicDB returns Not Found. Do not remove or map it by assumption. |
| 787, The New Horde | Retained Orc rogue evidence does not establish a universal parent or race exclusion. Comment 6436200 (25 September) reports no offer on Orc, Troll and Tauren, without sufficient build/completion context. Retain actual-offer confirmation and existing Horde race coverage. |
| 788 and class pickups | Source lists and the supplied export do not resolve all pickup conditions. Keep the 16 recorded unverified requirement IDs; do not turn ambiguous series into AND gates. |
| 96873, A Pain in the Neck | Three Luminous Residue; quest text describes disenchanting troll pendants. Comment 6435030 reports an Enchanting requirement, but lacks build/character details. No typed source gives a verified acquisition work point. Retain the gap and profession-gate research lead. |
| 96874, This Is Spinal Axe | Five Weathered Spines and five Rough Grinding Stones. Preserve the mapped spine work; the stone has no published drop/vendor location. Comment 6441571 explicitly guesses at a Blacksmithing gate. Do not promote that guess into a restriction. |
| 99123, Lost in the Shadows | Escort confirmed, destination/path still unmapped. NPC spawn samples are not ordered escort waypoints. Official notes report a respawn-time fix, not an endpoint or route. |
| Shared Shaman NPCs | Captured pages list multiple maps for the same manifestation/brazier. Preserve distinct quest IDs, selected pickup locations and existing race/class rules; require beta confirmation of branch-specific availability. |

Galgar's existing Cutting Teeth prerequisite has a supporting current comment
(6434923, 24 September). The known Scorpid and Medallion chains still require
real hand-ins, including the alternative Vile Familiars class branch. Lazy
Peons retains its Blackjack/use action and count of five. Class parchments keep
their individual class masks and the existing Include class quests setting.
Collector's Edition Welcome! remains excluded. No new low-level exception,
elite exclusion, profession gate, transport unlock or terrain shortcut is added.

The US/EU forum searches were accessible; exact-name searches added the official
escort confirmation, but no new reliable gate or coordinate. Recent Durotar
reports describe world objects stuck in an in-use state. Treat these as beta
interaction failures, not completed objectives or permanent manual skips.
Warcraft DB and Reddit requests were denied; no alternative route was used to
bypass those denials. No unsupported facts were taken from them.

## Coverage and route review

Distinct missing pickup/objective/hand-in quest IDs: **1 / 9 / 1 → 1 / 4 / 1**.
Unverified pickup requirement IDs: **16 → 16**. No unknown objective quantities
were recorded before or after. Five gaps close; the escort gap remains visible.
All four audited chapter entries preserve their complete action sets and onward
endpoints: **246 / 85 Horde actions, 13 / 10 Alliance-template actions**.
The global audit still contains 152 sections and 33 gap-free sections.

`before-flow.json` and `after-flow.json` retain every action, not a selected
prefix. `repriced-flow.json` substitutes the corrected stage facts into both
old and new orders, then evaluates bracket bottom/middle/top and half-filled
middle-level XP. Distances use the default host estimates; no native map API,
personal flight unlock or measured terrain path is assumed.

**Main-developer coordination is required before treating this as an optimized
guide.** The unchanged shared compiler can change reward timing and uncertain
legs when these facts become mapped or typed. The replay deliberately returns
status 2 when any objective receives less prior reward XP or another guarded
metric regresses. See the exact quest IDs and states in `repriced-flow.json`.
This PR leaves routing, eligibility, lifecycle and UI modules unchanged. Preserve
this as a data/research draft pending a coordinated compiler decision; do not
hide the result by shortening scope, altering XP facts or weakening the guard.

Reproduce on this reviewed source revision:

```sh
/workspace/.wow-together-tests/bin/python tools/apply_quest_stage_corrections.py
/workspace/.wow-together-tests/bin/python -m unittest discover -s tests -p test_durotar_coverage.py -v
/workspace/.wow-together-tests/bin/python tools/audit_quest_guides.py --zone Durotar --output /tmp/durotar-audit.json
/workspace/.wow-together-tests/bin/python tools/reprice_quest_stage_routes.py --before research/durotar-2026-10-08/before-flow.json --after research/durotar-2026-10-08/after-flow.json --output /tmp/durotar-repriced.json
```

The earlier full host run passed 1,450 of 1,451 checks. Its only failure was the
pre-existing historical catalogue fingerprint mismatch in `test_0829`; the
catalogue already differed on main before this work. Final targeted validation
and compilation outcomes are recorded in `review.json`. Host tests cannot
establish actual beta availability, completion timing or rendering.

## Player checklist for the main developer's test build

Record tester identity, addon version, client build, faction/race/class, level,
chapter, class-quest setting and party state. Report Pass / Fail / Skip separately
for each item; preserve the existing character's progress and manual skips.

1. On a fresh compatible Horde character, accept Cutting Teeth and finish its
   objectives. Sting of the Scorpid and Galgar must wait for the actual hand-in.
   Check both the normal and Warlock Vile Familiars branches before Medallion.
2. Check nearby eligible Lazy Peons/Galgar pickups. Pickup grouping must respect
   the existing hub radius, levels and prerequisites; use the Blackjack on five
   peons. The fixed full-zone order must not change during play.
3. Toggle Include class quests. The appropriate parchment and Shaman work should
   appear only under the existing class policy; ordinary quests must remain.
   Welcome! must stay out of the leveling guide.
4. On the applicable Shaman branches, confirm Rough Quartz and the two torches
   are supplied. Deliver them to the named NPC; do not farm another copy. Mere
   item possession or arriving nearby must not count as a completed hand-in.
5. For Call of Fire 1525, loot one Reagent Pouch from Burning Blade Cultists and
   one Fire Tar from its Barrens source. Verify the cave approach on the ground;
   report blocked terrain instead of assuming a straight marker line is safe.
6. Accept Lost in the Shadows when Pal'juh is available. Stay with the escort;
   its endpoint remains unmapped. Verify that the next instruction does not
   interrupt the escort and that Master Vornal's hand-in waits for real success.
7. Record The New Horde's actual offers/absences with full character and
   completion context. An absence must defer temporarily; a later confirmed
   offer may restore it. Do not make a manual skip merely to simulate absence.
8. Mid-zone, use Scan guide, reload and leave/re-enter Durotar. Active work,
   completed quests and personal skips must persist; deferred or accepted but
   unfinished work must not produce a false Guide complete.
9. Check both chapters' complete journey and the Barrens/Orgrimmar handoffs.
   Compare reward timing before later work and log capacity, not just travel
   to the first objective. Record the precise stops affected by compiler issues.
10. If an object reports already in use or an escort is absent, record the beta
    behavior and build. Do not infer a new prerequisite, spawn point or completion.
