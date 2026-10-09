# Mulgore quest-data review — 8 October 2026

See the [0.8.60 follow-up](refresh-0.8.60/README.md) for refreshed source/audit checks and the explicit race-source conflict.

Continues `guides/coverage` after `2249deb`, retaining the Dun Morogh and Durotar
commits. Main remains `67ff36412ede50154ec3a8b2aecb148e72ffb568`, addon 0.8.59.
The refreshed standard audit matches the queue: chapters 1–10, 11–20 and 21–30;
one missing pickup (96294), no recorded objective/hand-in gaps, and ten
unverified pickup requirements. None of those gaps is closed by this review.

## Changed facts

| Records | Correction and evidence |
| --- | --- |
| 99081, Grim Tidings | Require the actual hand-in of Longwalker Malah (99079). |
| 99101, Our Ancient Enemy | Require the actual hand-in of Grim Tidings (99081). Preserve actual-offer confirmation and the flag for unknown additional availability conditions. |
| 99082, The High Chieftain | Require the actual hand-in of Drive Them Out (99080). Preserve actual-offer confirmation and unknown additional conditions. |
| 745, 746, 99082, 99101 | Use Baine Bloodhoof's current published 47.4, 60.2 position for the affected pickups/hand-ins, consistent with the other Baine quests. |
| 758, 759, 760 | Use Mull Thunderhorn's current published 48.4, 60.4 position for pickup/hand-in, consistent with the other cleansing quests. |

All five current chain pages independently display the same linear order:
99079 → 99081 → 99101 → 99080 → 99082. The 99101 → 99080 link was already present.
`page-facts.json` retains the typed relationships, source URLs, capture dates and
hashes. Baine's NPC page independently agrees with the selected quest positions.
Older coordinates remain present in some quest mapper sample lists; the chosen
representatives follow the current quest mapper and NPC page, not a claim that
every older sample is invalid. NPC positions are not surveyed approach paths.

Only eight quest records change. Objective work, quantities, faction/race/class
masks, minimum levels, rewards, native completion checks and the XP baseline are
unchanged. Location corrections reject unexpected new positions and preserve
unresolved work. Reviewed prerequisites use the existing importer correction
mechanism. Both full and supplemental builds retain the corrections; applying
the reviewed corrections again writes nothing. No routing, eligibility,
lifecycle or UI Lua module is changed.

## Scope and source coverage

The standard audit retains **191 / 66 / 13 actions** across its three sections.
It deduplicates each faction/chapter after the first discovered race, so it is
not a union of every race's applicable quests. The separate Tauren capture
retains **200 / 69 / 13 actions** and includes Thunderhorn Cleansing, Wildmane
Totem, Wildmane Cleansing and Journey to the Crossroads. Together these captures
inventory **74 quest IDs**. Class templates in these host captures do not imply
that every class quest belongs to a Tauren character; separate actor tests cover
class/race filters and the Include class quests setting.

All 74 quest pages plus The Broodmother's page were captured. The zone list has
61 entries and is retained separately from the broader compiled scope, which
includes class quests and neighbouring-zone dependencies. Six linked entity
pages and all 24 files of the pinned QuestieDB manifest were checked. Retained
files contain typed facts and original summaries, not copied guide prose or
provider code. `THIRD_PARTY_NOTICES.md` supplies attribution.

The Hunt Begins (747) → The Hunt Continues (750) → The Battleboars (780) already
matches the supplied tester correction and pinned facts. Current pages retain
seven meat and seven feathers, ten cougar pelts, and eight snouts plus eight
flanks. Both Battleboar items have explicit drops from Battleboar (2966) and
Bristleback Battleboar (2954) in pinned item facts. The current quest mapper
selects the retained Battleboar work point at 57.6, 85.2. No target, quantity,
work point or hand-in was replaced for this chain. Older ravine/tunnel comments
do not prove a walkable Forever shortcut.

The cleansing actions already use the appropriate totem at their distinct well
locations. Their published event endpoints remain unchanged. A point at Mull is
only a pickup/hand-in point. Current Venture Co. comments support the existing
local note-object work; item titles referring to other zones are not directions
to leave Mulgore. Two current mine-route comments disagree on turns, so neither
was converted into a terrain path. Group/elite work stays in the catalogue.

## Unresolved facts and shared-code handoff

- **96294, A Darker Truth:** the current quest page describes a letter recovered
  from Broodmother Valraxx and delivery to Muln Earthfury. Neither the quest's
  typed starter fields, Bloody Parchment's source lists nor the pinned item facts
  establish its acquisition/start mechanism. The page provides no pickup point.
  Do not substitute Muln's hand-in or Valraxx's position for that missing fact.
- **Ten standard-profile pickup gaps remain:** 861, 1516, 1519, 2984, 2986, 5655,
  5661, 5928, 99082, 99101. Tauren scope also contains the already-unverified
  Journey to the Crossroads (854). Knowing a predecessor does not prove the
  absence of all other offer conditions. Pinned Shaman self-referential lists
  are not valid AND gates; same-title class variants remain distinct.
- **Player evidence:** the recovered 94-event Mulgore export remains explicitly
  partial, with its original author/build labels. It contains absences, not
  positive offers, for 99082/99101. The new published chain supplements that
  evidence without erasing temporary deferrals or personal manual skips.
- **Broodmother 96261:** the catalogue retains this level-31, minimum-23 elite
  quest and its work point. The shared builder suppresses sections with fewer
  than two enabled records (`LevelingGuides.lua`, `buildChoice`), so the isolated
  31–40 section is absent from both captures. This conflicts with complete
  visible zone coverage. Main-developer coordination is required to decide how
  to expose it; do not relabel its level or invent a dependency to force it into
  another chapter. Welcome! and the unused placeholder stay excluded, as do the
  existing ordinary-leveling exclusions for cloth donations.
- **Sources:** current US/EU forum searches did not resolve further quest gates
  or the Darker Truth starter. The wiki page returned 404. Warcraft DB and Reddit
  remained unavailable under the recorded access denials from this session;
  no denial was bypassed and no facts were imported from them.

## Full-route comparison

Both races retain all actions and endpoints, with all 24 candidate starting
states valid. The 1–10 baseline orders are **invalid under the corrected
prerequisites**: they could attempt a successor before its known predecessor's
hand-in. Therefore the old estimated trip is not a valid completed-route
benchmark. The comparison still records every metric and delayed reward rather
than hiding that difference. Later chapters have unchanged order/metrics.

At bracket start, the standard template's estimated distance changes from
161,630.79 to 161,878.95; log peak remains 12 and XP shortfall improves from
18,060 to 17,380. The Tauren template changes from 160,524.40 to 156,692.65;
log peak falls from 15 to 13, but XP shortfall rises from 16,660 to 18,060 and
aggregate reward XP before work falls from 811,325 to 776,907. Per-objective
reward delays across all replay states appear in the two `repriced-*.json`
reports. These are host estimates, not measured walking distances.

The strict optimization guard returns **review required** for both profiles;
an identical-order replay passes. Correct prerequisites take precedence over a
shorter invalid order. Further optimization and the Broodmother section need a
coordinated shared-engine decision. This remains a data/research draft, alongside
the separately documented Durotar compiler tradeoffs.

## Validation and reproduction

`review.json` records the final host results and exact semantic diff. The full
152-section audit passes; only Mulgore 1–10's standard audit entry changes.
Seven new Mulgore checks cover real hand-ins, offers, Baine consistency, conflict
rejection/idempotence, exclusions, Tauren continuations, fixed order and class/race
gates. Existing tests cover Scan guide, reload, zone entry, temporary absences,
manual skips and accepted-but-unfinished work. Host checks cannot establish
actual beta offers, map rendering, terrain or completion timing.

```sh
/workspace/.wow-together-tests/bin/python tools/apply_quest_stage_corrections.py
/workspace/.wow-together-tests/bin/python -m unittest discover -s tests -p test_mulgore_coverage.py -v
/workspace/.wow-together-tests/bin/python tools/audit_quest_guides.py --zone Mulgore --output /tmp/mulgore-audit.json
/workspace/.wow-together-tests/bin/python tools/audit_quest_flow.py --zone Mulgore --race-id 6 --output /tmp/mulgore-tauren.json
/workspace/.wow-together-tests/bin/python tools/reprice_quest_stage_routes.py --before research/mulgore-2026-10-08/before-tauren-flow.json --after research/mulgore-2026-10-08/after-tauren-flow.json --output /tmp/mulgore-comparison.json
```

For a historical capture, export `2249deb:WowTogether/QuestCatalogue.lua` with
`git show`, then pass that local project file to `audit_quest_flow.py --catalogue`.
The report hashes the actual supplied data. Keep race and source inputs matched
when replaying; the new race selector leaves default audit behavior unchanged.

## Player checklist

Record tester identity, client build, addon revision, race/class, level, chapter,
party state and class-quest setting. Mark Pass / Fail / Skip for each item.

1. On a fresh Tauren, finish and hand in each Hunt quest before its successor
   unlocks. Verify both Battleboar items, their counts and the ground approach.
2. Complete Longwalker Malah → Grim Tidings → Our Ancient Enemy → Drive Them Out
   → The High Chieftain in order. Acceptance/objective completion alone must not
   unlock the successor. Confirm the actual NPC offers with completion context.
3. An absent offer must defer temporarily and return after a later positive
   offer. A manual skip stays personal and is not cleared by an NPC visit.
4. At Baine, collect only eligible in-scope offers. Check Sharing the Land,
   Dwarven Digging and Rite of Vision together when actually offered; verify the
   corrected marker and preserve the full fixed work order after the visit.
5. Check Mull's corrected marker, then use the cleansing totems at their wells.
   Returning to Mull or arriving at the well must not grant quest completion.
6. Toggle class quests. Verify appropriate Shaman/Druid work and Troll/Undead
   priest restrictions without hiding ordinary quests or Tauren continuations.
7. Mid-zone, Scan guide, reload and leave/re-enter the zone. Active work,
   completed hand-ins and personal skips must persist. Deferred or unfinished
   quests must not result in a false Guide complete.
8. Check Barrens/Thunder Bluff handoffs, all three chapters, cave approaches and
   group warnings. No personal flight connection is assumed unlocked. Record
   Darker Truth's actual starter and whether Broodmother is visible in the main
   developer's coordinated build; these remain unresolved review items.
