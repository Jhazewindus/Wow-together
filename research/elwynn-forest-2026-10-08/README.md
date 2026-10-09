# Elwynn Forest: researched data candidate, 8 October 2026

Baseline: `guides/coverage` at `7e244207c2928491d99f46ee45a508ef99fdda5b`,
including main `09155ca265278572649a3529b8ce7ea1b4eb8431` / addon 0.8.61.
The supplied 0.8.59 baseline was refreshed: its Elwynn gap IDs still matched.
Work remains on the isolated guide branch, for review against main. No release,
Discord publication, or shared runtime change is part of this candidate.

## Scope and source review

The original compiled 1–10 template contains **99 distinct quests / 304 actions**:
71 zone-category quests and 28 class quests/dependencies. The current category
list has 76 entries. `scope-inventory.json` inventories every compiled ID,
including dependencies outside the pickup zone; category membership is retained
separately. Northshire introductions, Goldshire returns, Fargodeep/Jasperlode
work, the farms, eastern guard/lumber-camp work, the western gnoll area and
Stormwind/class handoffs remain in scope. Goldtooth's current published point
agrees with the retained representative; alternative farming targets remain
alternatives, not additional required tours. No unsupported mine entrance,
mountain shortcut, safe road or flight unlock was invented.

All 99 compiled quest pages, Hogger and Applejack Still were captured, along
with 64 relevant NPC/object/item pages and the bounded category list. The
adjacent factual JSON records retain URLs, IDs, capture dates, SHA-256 hashes,
explicit relations, identities and comment dates/IDs. Pinned Questie factual
fields were inspected first; all 24 manifest file hashes were verified against
commit `e0a6eaa86f181ac99262e34126bcd2ed1a1712d6`. Field tiers distinguish beta
deltas from converted-baseline facts. Missing quantities and current acquisition
relations were filled only from matching current typed facts. Downloaded scripts
were parsed as literal data, never executed. No third-party route engine, guide
order, quest descriptions or comment bodies were copied. Existing attribution
in `THIRD_PARTY_NOTICES.md` applies.

The category-only entries are Give Gerard a Drink (16, existing repeatable),
Welcome! (5805, existing edition exclusion), Waskily Wabbits! (7961, incomplete
legacy/test lead), Applejack Still (91736, level/minimum unknown/zero exchange)
and Hogger (176, level 11/minimum 5 elite). No new ordinary leveling chapter is
inferred from a category list or a level-zero exchange. The review does not
establish the recurrence of 91736 from its title; it remains an acquisition
option rather than a forced leveling prerequisite.

## Eight changed records

| Quest | Supported change |
| --- | --- |
| Seek out SI: 7 (2205) | Delivery to Mathias Shaw; acceptance supplies Delivery to Mathias (7674). Preserve its actual hand-in requirement; remove the false farming goal. |
| Simple Letter (3100) | Acceptance supplies letter 9542. Keep Kobold Camp Cleanup's actual hand-in gate and Llane Beshere speech/hand-in. |
| Encrypted Letter (3102) | Acceptance supplies letter 9555. Keep the same hand-in gate and Jorik Kerridan speech/hand-in; use the current published spawn 50.4,39.8 on map 1429 instead of the converted representative. |
| Vejrek (1678) | Explicit current requirement is one Vejrek's Head (6799), from retained Vejrek work in Dun Morogh. Add the real item hand-in count; preserve uncertain unlocks and Warrior gates. |
| Vorlus Vilehoof (1683) | Explicit current requirement is one Horn of Vorlus (6805), from retained Teldrassil work. Add its real item hand-in count; preserve uncertain unlocks and Warrior gates. |
| Beat Bartleby (1640) | Name the scripted duel, then the actual Bartleby hand-in, rather than a generic kill. Preserve the OR prerequisite group and unknown scalar count; no assumed one-kill credit or health threshold. |
| An Apple Treat (91738) | Map optional item acquisition at Applejack Still object 562131, map 1429, 24.5,58.2. Current quest 91736 explicitly exchanges four Shiny Red Apples (4536) for one Thunder Applejack (247824); its item reward relation independently agrees. Keep 91738's one-bottle requirement and Sergeant De Vries hand-in. An already-owned bottle satisfies acquisition without forcing the exchange, apple farming or a repeatable prerequisite. |
| Wabbit Pelts (7962) | Exclude historical testing-only content from ordinary leveling; retain the record and its source gaps. Exact-ID wiki revision 5772277 identifies testing-only content, while the current Forever page marks the quest unchanged and publishes no giver/hand-in. Revisit if a genuine live beta offer is documented. |

`record-changes.json` contains the full before/after records. Reviewed importer
rules reject changed identities, competing objective facts and conflicting
destinations atomically; reapplication is idempotent. The existing catalogue
packing tool regenerates data and exclusions without a whole-source recapture.
Entity data, world completion checks, XP baseline and unrelated quest records
are unchanged. Existing working gates and earlier zone corrections survive.

## Gaps and conflicts still open

| Audit field | Original | Candidate |
| --- | ---: | ---: |
| Missing pickup quest IDs | 2 | 1 |
| Missing objective quest IDs | 7 | 2 |
| Missing hand-in quest IDs | 2 | 1 |
| Unverified pickup requirements | 8 | 8 |
| Audited unknown objective quantities | 3 | 0 |

Wabbit Pelts' three removed actions are an evidenced scope exclusion, not
newly mapped stages. The four genuine objective-stage improvements are the
three supplied deliveries and Applejack acquisition. The two head quantities
are now explicit. Bartleby's `quantityUnknown` remains in the facts: the audit
does not treat an event as a counted kill/collect objective, so its zero result
does not establish a numeric native event count.

- **95771, A Taste of Darkness:** current page has no typed pickup, objective
  or hand-in relation. Its level 10/minimum 6 and reward do not establish a
  Warlock restriction or an acquisition point. Keep all three gaps visible.
- **91753, An Enchanting Lesson:** three Luminous Residue (247884) are required;
  neither current item relations nor comments establish a local source.
  Kitta Firewind's mapped location is the giver/hand-in, not residue work.
  Current Wowhead race mask 4294967372 excludes Humans; the pinned beta delta
  is 4294967373 and includes them. Per the task's source priority, retain the
  pinned existing gate pending actor/build/actual-offer evidence. Do not infer
  a profession restriction from the title.
- **1598, 1638, 1639, 1678, 1683, 1860, 5628, 5635:** keep all eight uncertain
  pickup requirements. A visible series or older comment is not proof of
  every current beta unlock. Actual prerequisite hand-ins remain required.
- **Warrior alternatives:** pinned converted-baseline `exclusiveTo` groups
  name 1639/1678/1683 as alternatives and 1640 accepts any of the three.
  Current Vejrek/Vorlus pages report changed Defensive Stance rewards. The
  template expands all three branches, including Ironforge and Darnassus;
  no current beta observation establishes the exclusivity/continuation behavior.
  Preserve existing OR gates and accepted unfinished work. Coordinate the
  alternative-selection decision before changing shared eligibility/routing.
- **Hogger 176:** retain level 11, minimum 5, Elite, both poster pickup points,
  one Huge Gnoll Claw, Hogger work and Marshal Dughan hand-in. The shared
  chapter builder suppresses the isolated 11–20 chapter (`#enabled < 2`), so
  Hogger is absent from both template and Human actor captures. Main development
  must resolve visibility with a party warning and personal skip choice. Do
  not falsify its level to fit 1–10 or label the zone complete while it is absent.

Current quest/entity comments were checked as dated leads. Applejack comment
6436540 (September 2026) suggested the exchange; typed item/quest/object facts,
not its directions alone, support the change. Older Bartleby failure/retry
reports do not establish a universal reset rule. Current US/EU forum searches
returned no independently useful missing-stage or unlock evidence. The exact
A Taste of Darkness wiki page returned 404. Warcraft DB/Reddit had recorded
access denials earlier in this session; no bypass was attempted. Supporting
ClassicDB and wiki captures are listed in `secondary-captures.json`; the wiki's
historical testing designation is not a surveyed current spawn.

## Full-route comparison and coordination

After the explicit testing-only exclusion, both compared orders contain the
same **98 quests / 301 actions**, with identical corrected objective facts and
unchanged onward endpoints. `before-flow.json` retains the untouched 304-action
baseline; `comparable-before-flow.json` applies only the same exclusion to that
baseline. The comparison never treats the removed placeholder as optimization.
All four bottom/middle/top/partial-XP replay states are valid. At bracket start:

| Metric | Before | After |
| --- | ---: | ---: |
| Estimated travel | 272,010.79 | 265,450.87 |
| Quest-log peak | 19 | 19 |
| Reward-only XP shortfall | 11,625 | 11,625 |
| Quest reward XP | 41,100 | 41,100 |
| Aggregate reward XP before work | 1,567,310 | 1,590,880 |
| Uncertain travel legs | 62 | 65 |

Despite the aggregate reward gain, rewards arrive later before work for 11,
15, 18, 21, 37, 239, 1598, 91743, 91745 and 91752. The strict optimization guard
returns **review required** in all four states. No shortened prefix, relaxed
guard or authored shared optimizer change hides this result. Distance uses
default host estimates, not verified walkability; quest-log capacity is unknown
in this fixture and combat XP is incomplete. The main developer must review
these tradeoffs and Hogger/Warrior handoffs before merge.

The template fixture lacks native bit support and includes optional class
templates; it is not a leveling recommendation for every character. Separate
Human Warrior/Rogue/Mage captures with bit support preserve 247/223/223 compiled
actions and correctly filter disabled class work from the effective route.
At level 10, class-off previews retain ordinary work and zero class stages.
Fixed order remains unchanged on progress/settings updates; no optional stage
earns fake completion/skip credit. Full cross-zone previews, including the
Darnassus endpoint, are evidence for review, not proof that every Human should
travel there.

## Host validation and player checklist

The full suite passes **1,540 of 1,541 tests** (480.586 seconds). Its sole failure
is the known historical catalogue fingerprint assertion, also recorded on the
main baseline; the fixture is unchanged. All **11 focused Elwynn regressions**
pass, including fresh Human Warrior/Rogue/Mage scope, progress/level changes,
actual prerequisite hand-ins, class opt-out, inventory acquisition, atomic
conflict rejection and idempotence. All **86 TOC Lua files** compile for Lua
5.1/interface 16001. The full suite also exercises Scan guide, persistence,
zone entry, offer deferrals, personal skips and native-false marker vetoes.

Validation results are recorded in `review.json`. Host checks cannot establish
native beta offers, item rewards, persistence APIs or terrain. The global audit
retains 152 sections and 33 recorded gap-free sections; source points rise
11,823 → 11,824. Only Elwynn's generated guide row changes. The source queue
remains incomplete (442 records). No 100% coverage or terrain-optimality claim.

Reproduce the focused checks:

```sh
/workspace/.wow-together-tests/bin/python tools/apply_quest_stage_corrections.py
/workspace/.wow-together-tests/bin/python -m unittest discover -s tests -p test_elwynn_coverage.py -v
/workspace/.wow-together-tests/bin/python tools/audit_quest_guides.py --zone 'Elwynn Forest' --output /tmp/elwynn-audit.json
/workspace/.wow-together-tests/bin/python tools/reprice_quest_stage_routes.py --before research/elwynn-forest-2026-10-08/comparable-before-flow.json --after research/elwynn-forest-2026-10-08/after-flow.json --output /tmp/elwynn-comparison.json
```

Record actor, addon revision, beta build, race/class, level, chapter, party and
class-quest setting; mark Pass / Fail / Skip for each item:

1. Fresh Human: follow Northshire → Goldshire, confirm all real pickups/work/
   returns and onward handoffs. Hand in Kobold Camp Cleanup before the letter;
   accepting or merely finishing its objectives must not unlock the next pickup.
2. Warrior/Rogue letters and Seek out SI: 7: supplied items must remain required
   at hand-in, with speech instructions and no fabricated farming trip. Check
   Jorik's actual position and native objective completion.
3. Apple Treat: test both an already-owned bottle and four apples exchanged
   at the Still. Confirm the recipe/reward and actual Sergeant hand-in; apples
   alone, the object's proximity or an absent item must not finish acquisition.
4. Warrior alternatives: record NPC offers before/after one branch's actual
   hand-in, class reward, eligible race and Bartleby continuation. Validate head/
   horn count and duel behavior. Do not accept a foreign branch solely to test
   a presumed universal gate; report genuine offers and unresolved conditions.
5. An Enchanting Lesson: record Human and other applicable Alliance offers,
   profession context and exact residue source. For 95771, supply its real
   giver, work and hand-in with IDs/positions if encountered.
6. After main resolves Hogger visibility, verify its elite/party warning, both
   posters, claw work and return. Manual skip must be personal; absent offers
   remain temporary deferrals and accepted unfinished work stays pending.
7. Mid-zone: toggle class quests, Scan guide, Pause/Resume, reload and leave/
   re-enter. Preserve fixed order, personal skips and unfinished work. Check
   later chapter/zone handoff behavior; no false Guide complete when work is
   deferred. Report the long zigzag with full action history and reward timing,
   including cave entrances and actual approaches rather than straight lines.
