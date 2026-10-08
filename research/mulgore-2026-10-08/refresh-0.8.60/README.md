# Mulgore follow-up review — 8 October 2026, 0.8.60

The repeated assignment continues `guides/coverage` at `73c0aee`, with main
`eec9b99` already merged. The previous eight-record Mulgore correction commit
`d6ed2ae` remains intact. This follow-up changes research/documentation only.

## Refreshed facts and scope

All 24 pinned QuestieDB files and 75 existing quest-page captures passed SHA-256
verification. Twenty-one priority quest pages, six linked entity pages and the
current 61-entry Mulgore category list were freshly captured. Adjacent files
retain URLs, dates, hashes, literal facts and source tiers. Downloaded scripts
were not executed and guide prose was not copied. Earlier same-day secondary
research remains in the parent review; no recorded source denial was bypassed.

The standard profile retains **191/66/13** actions; explicit Tauren retains
**200/69/13**, with a combined inventory of **74 distinct quest IDs**. The five
category records outside this inventory are the isolated elite Broodmother,
two existing cloth-donation exclusions, edition-only Welcome! and a placeholder.
No chapter was shortened or factual level changed to force inclusion.

The Hunt Begins 747 → The Hunt Continues 750 → The Battleboars 780 still requires
actual predecessor hand-ins. Fresh pages retain seven meat/seven feathers,
ten cougar pelts and **eight snouts plus eight flanks**. Battleboars' current
quest mapper retains the selected Battleboar 2966 point at **57.6,85.2** and a
Bristleback Battleboar 2954 alternative. Keep the existing selected work and item
counts. An NPC's representative sample is not a cave entrance or terrain path.

Fresh pages again establish Longwalker Malah 99079 → Grim Tidings 99081 → Our
Ancient Enemy 99101 → Drive Them Out 99080 → The High Chieftain 99082. Pinned facts
retain the correct giver/receiver IDs but do not independently provide these
new chain links. Preserve the reviewed current-page links, actual hand-ins,
existing offer confirmation and flags for additional unknown conditions.

Baine's fresh NPC page agrees with the retained **47.4,60.2** position. Its
listed starts are 745/746/767/99080/99082; listed ends are 745/746/763/99080/99101.
All seven distinct records already belong to the retained compiled inventory.
An NPC list identifies possible quests, not a guarantee that every character
can currently accept them. No extra quest is injected from an NPC visit.

## Explicit race-source conflict

| Quest | Pinned beta-delta mask | Current Forever quest/NPC lists |
| --- | --- | --- |
| Our Ancient Enemy 99101 | All Horde, 8589934770 | Tauren/Undead, 48 |
| Drive Them Out 99080 | All Horde, 8589934770 | Tauren/Undead, 48 |
| The High Chieftain 99082 | All Horde, 8589934770 | Tauren, 32 |

The quest pages and Baine's start/end lists agree with each other, but come
from the same provider. The pinned Questie facts explicitly disagree; this is
not an absence inferred from comments. The user's priority for the pinned source
supports retaining the existing Horde gates while this conflict is investigated.
Existing positive-offer requirements for 99101/99082 remain. Do not infer a
universal race restriction, erase known prerequisites or treat temporary absence
as a manual skip. `review.json` records each conflicting fact and source tier.
Current beta build/actor/hand-in/offer observations are needed before changing
eligibility; shared behavior changes remain with the main developer.

## Remaining gaps and shared decisions

Missing pickup/objective/hand-in counts remain **1/0/0**; the ten standard
unverified pickup requirements remain open, with 854 additionally in Tauren scope.
A Darker Truth 96294 still has no typed pickup/acquisition point. The current
quest has a provided Bloody Parchment 273659 and Muln Earthfury hand-in; the item
page has no typed source, and the pinned item only provides its identity. Muln's
location must not replace the missing pickup. The quest's prose describing a
letter recovered from Valraxx does not identify a verified acquisition mechanism.

Elite Broodmother 96261 remains level 31/min 23 in the catalogue. Its isolated
31–40 section is still suppressed by `LevelingGuides.lua:buildChoice`'s two-record
minimum. This visibility problem requires a coordinated shared-code decision;
it prevents claiming complete visible zone coverage. Keep the elite warning,
player choice and actual quest levels. Existing class settings, fixed order,
automatic progress and optional service advice remain unchanged.

## Full-route validation

Both old and corrected captures use the same current 0.8.60 runtime. Old data
comes from `2249deb`; both full orders are repriced with corrected facts.
All 24 candidate states preserve the required actions and onward endpoints.
The old 1–10 orders violate the corrected prerequisite hand-ins, so their
metrics do not describe valid completed guides. Strict optimization guards still
require review for both profiles; the later chapters remain unchanged.

At bracket start, standard travel estimates change 161,630.79 → 161,878.95,
log peak stays 12 and XP deficit falls 18,060 → 17,380. Tauren travel changes
160,524.40 → 156,692.65 and log peak falls 15 → 13, while XP deficit rises
16,660 → 18,060 and reward XP before work falls 811,325 → 776,907. Exact states and
individual delayed rewards are retained in both repriced reports. These are
host estimates without surveyed terrain, native map geometry or flight unlocks.
Coordinate optimization with main; do not shorten scope or weaken the guards.

Seven Mulgore regressions and thirty offer/progress tests pass. All 84 TOC Lua
files compile under Lua 5.1/interface 16001. The refreshed scoped audit passes
three sections and 116 source points. The combined branch's last full run passed
1,492 of 1,493 tests; the sole failure is the known historical catalogue fingerprint
assertion. These follow-ups change only documentation/research, so that runtime
result remains applicable. Host checks do not establish native beta behavior.

## Player checklist

Run the [original full Mulgore checklist](../README.md#player-checklist), recording
build, addon revision, race/class/level, party state and class setting.

1. Compare the three conflicting quests on Tauren, Undead and Orc/Troll with
   matched predecessor hand-ins. Record actual positive/negative NPC offers
   and build context. Do not generalize a single absent offer to all characters.
2. Confirm both full chains, Battleboar item counts/work area and Baine's actual
   offers. A deferred pickup must return after a positive offer; personal manual
   skips and accepted unfinished work must persist through Scan/reload/zone entry.
3. Record Darker Truth's exact starter/acquisition and whether Broodmother is
   visible in the main developer's coordinated build. Check cave approaches,
   all three current chapters, neighbouring-zone handoffs and reward/log pressure.
