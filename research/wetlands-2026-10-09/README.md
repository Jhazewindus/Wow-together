# Wetlands quest facts and complete-scope review

Reviewed **9 October 2026 (Europe/Amsterdam)** on addon **0.8.61**, branch
`guides/coverage`, baseline `6176f648facb16ea453e6a8a9a38416b588fa194`;
main `09155ca265278572649a3529b8ce7ea1b4eb8431`. The supplied 0.8.59 audit
was refreshed before editing. This review preserves current captured facts and
working guide behavior; native offers and terrain still need players.

## Evidence and ten corrections

Primary public factual source: [pinned QuestieDB Forever facts](https://github.com/Questie/QuestieDB/tree/e0a6eaa86f181ac99262e34126bcd2ed1a1712d6/data/Forever),
commit `e0a6eaa86f181ac99262e34126bcd2ed1a1712d6`. All **24 manifest hashes**
were verified in the available cache. `source-joins.json` records exact IDs,
URLs and source tiers; `pinned-facts.json` retains typed quest/entity fields and
origins without copied quest prose. `record-changes.json` retains exact before/
after records. Converted-baseline quest facts require matching name/level/minimum;
beta deltas and observations remain separate from older-world facts. The review
date is not a new in-game observation.

- **281/284/285**, Reclaiming Goods / The Search Continues / Search More Hovels:
  use **Interact with** the exact Damaged Crate **261**, Sealed Barrel **142151**
  and Half-buried Barrel **259**. Published quest `finishedBy` and object
  `questEnds` join these objects; a conversation instruction was wrong. Keep
  current captured positions and actual chain hand-ins.
- **631 The Thandol Span** similarly interacts with Ebenezer Rustlocke's Corpse
  **2652**. Keep its precise existing point, elite warning and subsequent actual
  631 hand-in before 632. A corpse object is not a living conversation partner.
- **465 Nek'rosh's Gambit** now says **Use Dwarven Tinder on Dragonmaw Catapult**
  at actual object **1609**. Source item **3339** is already supplied; it is not
  independent farming. The work has no invented burn count. The actual 464
  hand-in gate and 474 follow-up remain. Source item ID is retained in data;
  the existing compiled stop uses the tool name rather than a new item API.
- **455 The Algaz Gauntlet** keeps **8 Dragonmaw Scouts / 6 Dragonmaw Grunts**
  and adds its separate, published **Dun Algaz traversal** trigger at map 1437,
  **53.72/70.33**. This is an event-area point, not a road survey or a guessed
  NPC/count. It adds one required work action in each of two compiled chapters.
- **94497/94499/94500/94501 Call of Water** retain explicitly supplied inputs
  **265732 Empty Brown Waterskin / 265747 Empty Red Waterskin / 265772 Unfilled
  Blue Waterskin / 7810 Vial of Purest Water**. Empty inputs are distinct from
  full output items **265734/265748/265773**. Neither supplied quantities nor
  unknown output quantities are assumed. The vial delivery stays mapped to
  Norric Lochthane in Loch Modan, without a new farming stage.

Water-filling work remains unlocated: published context is below Hervdana's cave
waterfalls in Wetlands, Stonewatch Falls by Nightcrawler Murlocs in Redridge,
and Astranaar waters in Ashenvale. The source gives no precise water-use points
or counted output quantity. Hervdana's actual cave point **258203** is a pickup/
return, not a water objective. Original proposed use/travel text is retained in
`coordination-proposal.json`; applying unlocated use instructions needs shared
text support. Shaman mask **64**, Alliance/race gates, minimum **20**, class
setting and all unknown quantity flags remain. No new universal parent chain is
inferred from same-title class records.

## Whole scope, gates and ship handoffs

`direct-inventory.json` retains **66** direct-category records;
`inventory.json` retains all **73 unique compiled IDs**, including eight actual
class/cross-zone continuations. Only the `<UNUSED>` record **462** lies outside
the current discovered scope; an isolated record does not establish a chapter.
No new edition/profession exclusion is guessed. Related onward quests and
categories are retained in `continuations.json`.

The three complete Alliance audit chapters retain all prior actions and add two
traversal occurrences: **11–20: 6 → 6**, **21–30: 179 → 180**, **31–40: 76 → 77**.
Actual Shaman selection retains 6/180/77; Warlock selection retains 6/168/77.
Human, dwarf, night-elf, gnome and Skyborn profiles preserve these full scopes and
saved orders. Horde has no discovered Wetlands leveling chapter. The 11–20
section is the **level-20/minimum-18 Fiora → Astranaar handoff**, not a level-11
Wetlands leveling recommendation. Chapter labels never establish native minimums.

Lower-level Algaz/Rockgar introductions remain because the current chain joins
**468 → 455 → 473 → 464 → 465 → 474** into the later catapult/Nek'rosh branch.
The source has empty or absent converted-baseline parent fields for 455, 464 and
276, conflicting with current captured introductory chains. These are concrete
coordination/native-offer questions; no shared gate was changed. **484 Young
Crocolisk Skins** retains its uncertain pickup requirements and current 469
parent. The pinned baseline has Stormwind reputation **72 / 0**, no parent, and
prose count **4**, whereas current Forever objective count is **6**. Retain the
current six skins and uncertainty. **303 The Dark Iron War** similarly retains
current count **15**, versus converted prose **10**; do not overwrite newer
captured objectives with baseline prose. Race-mask disagreements remain in the
proposal; current faction gates are preserved.

Current supplied deliveries/statuette variants, Ormer/Greenwarden chains,
Menethil and road hub returns, elite/group quests and onward Ironforge/Stormwind/
Arathi handoffs remain. **378 The Fury Runs Deep** retains actual 303 hand-in
requirements but is dungeon-tagged and outside ordinary compiled scope: optional
Stockade support needs coordinated presentation, not a physical-access gate.
**647 MacKreel's Moonshine** has a published timed flag; native duration and
current route timer handling need review before recommending detours. No timer
length is invented.

`ship-handoffs.json` retains current published graph provenance, directed ship
links and exact boarding/arrival nodes. Menethil–Theramore uses map **1437
5.09/63.51 → 1445 71.5/56.35**; Menethil–Auberdine uses **1437 4.64/57.16 →
1439 32.37/43.81**. Both have explicit Alliance ship edges, not water walks.
Fiora **1132** and James Hyal **1302** have mapped Theramore recipients; Bloom
**98209** and Unrequited Love **98461** retain Darkshore recipients/starts and
onward context. NPC destinations are distinct from boarding endpoints. Focused
host checks use synthetic public sizes/continents to select explicit ship legs;
without public geometry, a host path may be unavailable. None proves live ship
availability, dock safety, boat timing or personally unlocked flight links.

## Gaps and complete-route comparison

Recorded gaps remain **pickup/objective/hand-in 5/11/5**, uncertain pickups **6**,
unknown objective quantities **3**. **87318/87491/88756/88757/88758** have no
usable pinned quest records or pickup/objective/return points; their elite status
and visible unknown work remain. Bring Back a Bang's known **3 Stolen Explosives
280806** requirement stays. **98208 Nord'el**, **98246 12 Perfect Razormaw Eggs**
and **98293 30 Dragonmaw Armaments** have no supported drop/object-use joins with
precise work areas in the pin. The known armaments pickup object **672330** alone
does not prove an item source. No giver, matching-name object or guessed nest
closes those gaps.

Available cached/repository facts were used. No new requests were sent to
previously denied Wowhead, Warcraft DB, wiki or community hosts; earlier capture
denials remain documented in prior reviews. No fresh comments/forum review or
exhaustion of all public sources is claimed. Exact missing facts remain explicit.

The raw strict comparison correctly rejects the **added action scope**. Its
output is retained. `reconcile.py` constructs an explicit complete old baseline
by adding only each newly evidenced traversal before its actual 455 hand-in,
removing **no** old action. Both complete orders are then priced on identical
corrected facts. All **12 strict states** are valid for old/candidate orders and
all endpoints remain. 11–20 and 31–40 metrics are unchanged. 21–30 distance
improves **200,056.34 → 195,957.74**, log peak stays **10**, but uncertain legs
rise **41 → 42**, with later rewards before **275/295/299/305/471/472/98072**.
The strict guard remains **REVIEW REQUIRED**; summed earlier XP does not erase
individual reward delays. Candidate chapter-entry quest-only XP deficit remains
147,640 in that replay state; this is not a complete leveling XP path. New work
is a scope correction, not a shortening or free route gain. No shared optimizer,
routing, eligibility, lifecycle or UI modules were authored.

## Validation and player checklist

All **102 zone regressions**, **nine focused tests**, **122 transport/class/
offer/session checks** and **49 importer/source tests** pass. All **86 TOC Lua
files** compile under Lua 5.1/interface **16001**. Reapplication reports no changes;
conflicts fail atomically. Entity data, world completion checks and XP baseline
are unchanged. Only Alliance Wetlands 21–30/31–40 global rows change. Global:
**152 sections / 11,835 points / 33 recorded gap-free / 378 unresolved ordinary
records**. Exact logs and tested hashes are retained. Previous combined suite
passed 1,562/1,563 with the recorded historical catalogue fingerprint assertion;
no new full-suite or native beta result is claimed.

- On a fresh/mid-zone Alliance character, check Menethil and Greenwarden/road
  hub offers, actual level/race/class and source-conflicting introductory gates.
  Check Stormwind reputation and six-skin count for 484, and native dwarf count
  for 303. Accepting/finishing objectives must not replace actual prior hand-ins.
- Interact with all three crate/barrel objects, then check both distinct statuette
  variants and actual recipients. Check Rustlocke's corpse, subsequent report,
  explosives cache in Arathi and Captain Nials onward handoff.
- Traverse Dun Algaz and finish both counted kill goals. Verify native event
  credit/label before hand-in; trigger coordinates do not certify tunnel roads.
- Use supplied Dwarven Tinder on the catapult; verify destruction/completion,
  next actual offer and group preparation. Do not farm supplied tinder or assume
  a burn count. Keep elite/group objectives visible and the player's skip choice.
- On a Shaman, toggle Include class quests. Fill each distinct supplied empty
  waterskin in its actual water area, verify native output counts and hand-ins,
  then deliver the vial. Check cave entrance/elevation, Redridge/Astranaar
  approaches and cross-zone ship connections; record missing precise use points.
- Board at the correct Menethil dock and verify both ship arrival endpoints,
  waiting and native map transitions. Check Fiora/James Hyal and Darkshore
  handoffs, avoiding straight water lines and assumed unlocked flights. Verify
  MacKreel's actual timer and direct Southshore delivery after pickup.
- Check lost/elite quests, explosives, Nord'el, egg nests and armaments with
  build/date/ID-specific target/drop/use evidence and quantities. Do not let
  unknown work or a nearby pickup marker count as completion.
- Test all applicable Alliance races including Skyborn, Shaman/ordinary class
  settings, fresh and mid-zone progress, chapter/zone entry, Scan guide and reload.
  Keep fixed full orders, temporary unavailable deferrals that return after an
  actual offer, personal skips and accepted unfinished work distinct. None may
  produce a false Guide complete.

Native checks and shared decisions remain pending. This focused branch commit
and draft PR leave release/tag/archive/Discord publication to main development.
