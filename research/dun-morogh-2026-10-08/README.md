# Dun Morogh full-zone review — 8 October 2026

This expands the earlier [selected-source review](../2026-10-08-dun-morogh-review.json).
The queued 0.8.59 baseline was refreshed after merging main `eec9b99` (0.8.60)
into `guides/coverage`, producing baseline merge `713a884`. Earlier guide commits
remain intact. Main's vendor-service changes are inherited, not authored by this
review. No shared runtime module, release version or publication is changed here.

## Supported correction

**The Quarry's Smith (95217):** move the existing Scarred Crag Boar work point
from the converted-baseline representative 70.87, 61.35 to the current NPC page's
published representative **73.8, 52.6**, map 1426. This is an actual spawn sample,
not a centroid or a claim that all older samples are invalid. The current quest
mapper also lists the boar as the Toughened Boar Hide source, and the current
item page explicitly links item 267416 to NPC 1689.

Preserve four hides, twelve Copper Bars, the Copper Bar missing-location flag,
the hand-in items, quest identity and existing class/race/minimum-level gates.
No new work, generic monster marker or inferred gathering profession is added.
The short existing loot instruction still names the mob, item and count.
`tools/quest_corrections.json` retains source/date/hash and rejects conflicting
new locations. Applying the corrections again changes nothing. The semantic
diff contains only this quest's objective position/provenance and review source.
Entity data, world completion checks and XP baseline are unchanged.

The earlier review's 70.87, 61.35 source fact remains as historical evidence;
this current-page selection supersedes its use as the guide representative.
Neither point establishes a surveyed path around the quarry or mine entrance.

## Complete scope and evidence

Standard and dwarf captures contain **55 distinct quests**, retaining **151
1–10 actions and 30 11–20 actions**, including dependencies and cross-zone handoffs.
All 55 pages and two later cross-zone quest pages were captured. The current
Dun Morogh category list has 60 entries; this list and the actual compiled
inventory are retained separately. Eleven relevant item/NPC pages were inspected.
Source URLs, capture dates, hashes and typed facts are in the adjacent JSON files.
No downloaded scripts were executed, guide directions copied or quest prose
bundled. Existing third-party notices apply.

The category-only entries outside these chapters are:

- Distracting Jarven (308) and Guarded Thunderbrew Barrel (403): retain existing
  repeatable exclusions.
- Welcome! (5841): retain the edition-only exclusion.
- Stonegear's Search (467) and Search for Incendicite (466): retain both records,
  their level-20 minimum, chain and pickup alternatives. These higher-level
  handoffs include a Loch Modan/Ironforge introduction and Wetlands work. The
  shared local-work/pickup-map criteria do not expose a Dun Morogh 21–30 section;
  category membership alone is not a claim that the work happens here. No
  profession exclusion or shortened early-zone prefix was invented for them.

Class-template audits do not certify suitability for every character. The
Quarry's Smith's existing class mask remains 67; ordinary quests do not inherit
that restriction. Existing class-setting and actor gates remain in force.

## Priority decisions and remaining gaps

| Item | Review decision |
| --- | --- |
| Treacherous Cold 99162 → Rime's Wrath 99161 | Preserve actual predecessor hand-in and the supplied level-7 Alliance dwarf, build-70245/addon-0.8.42 tester provenance. Current pages do not independently establish this gate, so it is not relabeled as a web-verified prerequisite. |
| Rime's Wrath 99160 vs 99161 | Keep separate IDs: ten Minor Ice Elementals (276003) versus one Avala's Core (286325) from Avala (276009). Do not merge by title or transfer the tester gate to 99160. Current NPC pages support the retained representative positions. |
| Winter Wolf 1131 | Current NPC loot data lists Chunk of Boar Meat (769), also used by Stocking Jetsteam (317). This broad relation does not prove an active unfinished objective or a live beta drop. Keep native-false vetoes, accepted-quest and readable unfinished-objective checks; no generic star/raid mark or monster layer is restored. |
| The Quarry's Smith 95217 | Known hide work is mapped. Copper Bars remain unmapped: the current item page lists remote Fel Interlopers and crafting sources, not a verified local acquisition point for every eligible character. No smelting/vendor assumption closes the gap. |
| Treaty of Understanding 98423 | Keep the item starter 281030 and Magni hand-in. A recent comment on both quest/item pages repeats a guide's Hall of Thanes/Relic vault lead, without an exact source object, position or independent acquisition observation. The pickup remains unknown; Magni is not substituted for it. |
| Senir's Observations 282 | Keep predecessor 218, Grelin → Thalos and provided report 2619, distinct from same-title quest 420. Further beta offer conditions remain unverified. |

Recent Treacherous Cold comments report inconsistent rifle looting and disagree
on whether relogging helps. Treat these as beta interaction reports, not proof
of completion, a new prerequisite or permanent manual skips. Rifle object IDs
and distinct work positions are unchanged. Existing initial hub flow, objective
pairing, actual turn-ins, close-level exceptions and personal progress behavior
remain subject to the shared compiler's existing policies.

The revised standard gap counts remain **pickup 1 / objective 1 / hand-in 0**,
with **one unverified pickup requirement** and no recorded unknown quantities.
All three source records remain open. Current US/EU forum searches did not add
reliable missing quest facts. The Treaty wiki page returned 404. Warcraft DB and
Reddit had recorded access denials earlier in this session; none was bypassed.

## Full-route comparison and shared-code handoff

Both profiles preserve every required action and onward endpoint. All 16
candidate starting states are valid, as are their baselines under the corrected
facts. The unchanged shared compiler reorganizes chapter 1–10 after the point
update. At bracket start, repricing both full orders with the same corrected
geography gives:

| Metric | Before | After |
| --- | ---: | ---: |
| Estimated travel | 110,330.68 | 108,044.93 |
| Quest-log peak | 8 | 10 |
| XP shortfall | 6,700 | 6,700 |
| Quest reward XP | 20,720 | 20,720 |
| Aggregate reward XP before work | 432,255 | 411,915 |
| Uncertain travel legs | 25 | 26 |

Work for 319, 320, 412, 413, 415, 417, 419 and 95212 receives later rewards in
at least one replay state. The 11–20 chapter's metrics/order are unchanged.
Exact results are in `repriced-flow.json` and `repriced-dwarf-flow.json`.
An identical-order replay passes; the strict before/after optimization guard
returns **review required**. These are default host travel estimates, without
native world-map geometry, observed flight unlocks or surveyed terrain.

Main-developer coordination is required for a compiler decision before calling
this optimized or merging the data candidate. The data agent has not changed
routing, eligibility, guide lifecycle, marker or UI modules. Do not hide the
tradeoff by dropping objectives, weakening the guard or changing factual levels.
The earlier Durotar/Mulgore handoff findings also remain documented separately.

## Validation and reproduction

The final full suite passes 1,492 of 1,493 tests. Its sole failure is the known
historical catalogue fingerprint assertion, which also fails on main; its fixture
was not changed. The focused 70-test suite and updated eight-test zone suite pass.
`review.json` records the results. Five new Dun Morogh regressions cover
source-gap preservation, atomic/idempotent corrections, distinct Rime identities,
actual prerequisite hand-ins, unresolved starters and stable dwarf/gnome orders.
Existing Winter Wolf tests verify native vetoes and unfinished-objective rules;
existing guide tests cover class settings, temporary deferrals, personal skips,
Scan guide, reload and zone entry. Integration includes main's 0.8.60 vendor
service tests. All 84 TOC Lua files compile under Lua 5.1/interface 16001.
The global 152-section audit passes; only Dun Morogh 1–10 changes from the
post-merge audit baseline. Host tests do not establish native beta behavior.

```sh
/workspace/.wow-together-tests/bin/python tools/apply_quest_stage_corrections.py
/workspace/.wow-together-tests/bin/python -m unittest discover -s tests -p test_dun_morogh_coverage.py -v
/workspace/.wow-together-tests/bin/python tools/audit_quest_guides.py --zone 'Dun Morogh' --output /tmp/dun-morogh-audit.json
/workspace/.wow-together-tests/bin/python tools/audit_quest_flow.py --zone 'Dun Morogh' --race-id 3 --output /tmp/dun-morogh-dwarf.json
/workspace/.wow-together-tests/bin/python tools/reprice_quest_stage_routes.py --before research/dun-morogh-2026-10-08/before-dwarf-flow.json --after research/dun-morogh-2026-10-08/after-dwarf-flow.json --output /tmp/dun-morogh-comparison.json
```

## Player checklist

Record tester identity, addon revision, client build, race/class, level, chapter,
party state and class-quest setting. Mark Pass / Fail / Skip for each item.

1. On a fresh dwarf/gnome, check useful eligible initial hub pickups and the full
   chapter. Actual prerequisite hand-ins must precede successor acceptance;
   merely finishing objectives or seeing an offer must not bypass known gates.
2. For Treacherous Cold, gather all three rifles and hand in. Only then should
   99161 unlock. Separately verify 99160's ten elementals; report the quest ID
   and objective, not only the duplicated title.
3. With Stocking Jetsteam accepted, check Winter Wolf hints against the live
   native flag and unfinished item objective. No hint should remain for an
   unrelated/completed objective or become a raid target marker.
4. On an eligible Quarry's Smith character, verify four hides from Scarred Crag
   Boars around the current point and twelve Copper Bars. Record the actual
   local Copper Bar source; the guide must keep that missing point visible.
5. Record the Treaty item's exact acquisition object/NPC and map position, and
   Senir's full before/after NPC offers with completion context. Do not turn
   secondhand vault directions or an absent offer into a permanent skip.
6. Toggle class quests, Scan guide, reload and leave/re-enter the zone mid-run.
   Preserve fixed work order, accepted unfinished work and personal skips;
   temporary absences must return after confirmed offers and must not complete
   the guide falsely. Optional vendor advice must not consume quest progress.
7. Check all 151/30 template actions through the applicable full chapters and
   Ironforge/Loch Modan handoffs, including cave approaches and group warnings.
   Report reward timing/log-pressure tradeoffs; no flight unlock or terrain
   shortcut is assumed by this review.
