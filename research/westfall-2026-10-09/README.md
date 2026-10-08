# Westfall facts and complete-scope review

Reviewed **9 October 2026 (Europe/Amsterdam)** on addon **0.8.61**, branch
`guides/coverage`, baseline `2676a4b36bf03712b7184fa72ad5734c274d2342`;
main `09155ca265278572649a3529b8ce7ea1b4eb8431`. The supplied 0.8.59 snapshot
was refreshed before editing. This is a data review with explicit remaining
facts and shared decisions, not complete terrain or native beta certification.

## Evidence and changes

Primary public factual source: [QuestieDB at the pinned commit](https://github.com/Questie/QuestieDB/tree/e0a6eaa86f181ac99262e34126bcd2ed1a1712d6/data/Forever).
All 24 manifest files in the available cache were verified by SHA-256.
`source-joins.json` retains hashes, positions and source tiers;
`pinned-facts.json` retains typed quest/entity facts and origins without copied
quest prose. `record-changes.json` retains exact before/after records.
Converted-baseline facts require matching quest identity; beta deltas and
observations are identified separately. Source dates are the pinned publication,
not a new in-game observation. Map points do not establish roads or approaches.

Eleven records change:

- Captain Sander's treasure chain **136/138/139/140** ends at objects
  **35/36/34/33**, respectively. Exact object `questEnds` and quest `finishedBy`
  joins support interaction, so work instructions now say **Interact with**
  Captain's Footlocker, Broken Barrel, Old Jug and Locked Chest. Published points,
  looted-map start, faction eligibility and actual previous hand-ins remain.
- Alba **253092** starts/ends in **92742/92744/92745/92747/92748/92752** now use
  the actual published beta-observation position **52.4, 52.9 on map 1436**.
  Three actual positions are retained in evidence; this is one representative
  position, not their average or an inferred patrol. Alba **253279** at the
  Deadmines exit remains distinct and unchanged. Quest **92747** retains level
  15; the pinned observation says 16, so that conflict is explicit.
- **92819 Destruction in Deadmines** has source-described detonator-use work.
  Its empty objective record previously compiled into a conversation at the
  giver. Mark the work **unknown** instead: no invented item/target/count or
  coordinates, and mapped pickup/return remain. Same-title **92753** is a
  separate dungeon-tagged record; its explosive-placement facts cannot be
  borrowed to fill 92819.

## Remaining gaps and whole-zone scope

Standard audit objective gaps increase **1 → 2**: **92749** remains and **92819**
is newly exposed, rather than falsely mapped. Recorded pickup, hand-in,
uncertain-pickup and quantity gaps remain zero. The absence of recorded gaps
cannot certify precise positions, complete mechanics or native offers.

**92749 A Dynamite Plan** requires **10 Coarse Dynamite (4365)**. Pinned beta
observation supports crafting, trade or auction-house acquisition, but names no
fixed work area or specific vendor/drop relation. Sprite Jumpsprocket **11026**
is the mapped pickup/recipient in Stormwind, not a dynamite farm. Engineering is
an acquisition option, not an evidenced eligibility gate. The generic unknown
collection step remains; meaningful unlocated acquisition/use text needs shared
text support. Original proposed instruction and constraints are retained in
`coordination-proposal.json`. [Quest lead](https://www.wowhead.com/forever/quest=92749#comments),
[item lead](https://www.wowhead.com/forever/item=4365),
[NPC lead](https://www.wowhead.com/forever/npc=11026).

**Odd Child 249713**, quests **92109/92110**, has published Moonbrook-barn context
but no pinned zone spawn. The existing **Eastern Kingdoms continent marker**
(map 1415, area -3, 41.2/79.0) stays coarse. It must not become invented Westfall
coordinates or a certified safe barn approach. Native well-sampling map-area
research in QUEST_DATA.md remains; well work is not moved to Alba.

The direct Westfall category has **54 records**; `direct-inventory.json` and
`continuations.json` retain all of them. The standard full compiled scope has
**45 unique IDs / 177 actions**: Alliance 1–10 **26**, Alliance 11–20 **127**,
Horde 11–20 **24**. Horde scope is neutral coast/treasure work, not a general
Horde leveling recommendation. Non-Human ordinary Alliance races have 14 actions
in 1–10; their existing gates remain. Separate Skyborn (race 95) captures retain
**26 / 224** actions, including the cross-zone prerequisite chain for **98021
Journey to Sentinel Hill**, gated by the actual **94947 Welcome to Azeroth**
hand-in. Standard global audit profiles omit Skyborn; its evidence is separate.
All checked-race records are retained in `expanded-inventory.json`.

The nine standard-uncompiled direct IDs are **48/49/50/51/53, 117, 79008, 92753,
98021**. Sweet Amber's level-44/minimum-40 chain has mapped work in other zones;
existing `sectionSeeds/localWork` does not offer it as a local Westfall 41–50
chapter. Its catalogue, quantities and actual hand-in chain remain. 117 is
repeatable; isolated level-22 79008 does not meet the builder's two-record
chapter threshold; 92753 is dungeon-tagged; 98021 is race-specific and *is*
retained in Skyborn scope. Optional cross-zone/dungeon support is a coordinated
presentation decision, not justification to delete records or lower minimums.

The existing **36 → 38** recipe/material dependency explains the useful lower-
level prerequisite in 11–20. The actual Defias chain **65 → 132 → 135 → 141 →
142 → 155** and escort adjacency remain; **166** requires **155's hand-in**.
This unlocks a quest, not physical Deadmines access. 166 and dungeon-tagged 214,
and beta dungeon preparation/continuations, need optional handoff presentation.
No universal parent relation is inferred between the beta Alba quests merely
from their titles or proximity. Chapter names are not verified dungeon minimums.

No new requests were sent to previously denied web hosts. Available pinned and
repository evidence was used; earlier repeated denials remain documented in
previous zone captures. No fresh forum/comment review or exhaustion of all public
sources is claimed. Remaining acquisition, use and approach facts need current
native evidence. No shared routing, eligibility, lifecycle or UI changes authored.

## Route and validation

Standard **12** and Skyborn **8** strict complete-route replay states pass:
every required action and endpoint survives, both orders are valid, and travel,
log peak, quest XP shortfalls and reward timing are **unchanged on identical
corrected facts**. No prefix-only or optimization gain claim. Standard Alliance
11–20 estimated distance is 133,274.84 with log peak 13; Skyborn is 236,290.15
with peak 13. Quest rewards alone do not prove enough XP for the whole bracket.
Fixed order remains stable under mid-zone progress. Current route measurements
are estimates, not native walking time, safe terrain or unlocked flight paths.

Eight focused tests, **93 zone regressions**, **122 transport/class/offer/session
checks**, **49 importer/source checks** pass. All **86 TOC Lua files** compile
under Lua 5.1 with interface 16001 retained. Reapplication reports no changes;
conflicts fail atomically. Entity data, world completion checks and XP baseline
are unchanged. Only the Alliance Westfall 11–20 global audit row changes;
152 sections / 11,834 points / 33 recorded gap-free sections remain. The ordinary
source queue has **378** unresolved records. Exact logs and tested hashes are
retained. The prior combined full-suite result was 1,562/1,563 with a documented
historical catalogue fingerprint assertion; no new full-suite run is claimed.
`skyborn_capture.py` extends only the local host capture race loop, without
changing the runtime or audit tool; its complete before/after/repriced outputs
are retained alongside standard captures.

## Player checklist

- Check Sentinel Hill pickups/returns, Alba's actual beta positions and both Alba
  IDs. Record build, faction, race/class and actual native level minimums; resolve
  92747's level conflict with offer evidence.
- Check each well's interaction/sampling area and each collection target/count;
  do not interpret a representative spawn as the only spawn or infer drop rates.
- Loot Captain Sander's map and interact with each exact treasure object in
  order. Check item-start availability and actual hand-ins before next pickup.
- Obtain 10 Coarse Dynamite by a supported acquisition path; confirm its hand-in
  and ordinary eligibility with Include class quests off. Check detonator use,
  explosive placement, native counts and the two distinct Deadmines quest IDs.
- Finish the Defias escort and actual hand-in before testing 166. Check instance
  entry/exit, group preparation and optional Red Silk Bandanas/dungeon handoffs.
  Record which beta continuation offers require actual hand-ins; do not assume
  acceptance/objective completion or physical dungeon access are the same gate.
- Locate Odd Child in the Moonbrook barn and record exact native map/coordinates
  and safe approach. Check Westfall coast, buildings, cave/instance transitions,
  hostile areas and each player's actual flight connections.
- Check Human, dwarf/gnome/night-elf and Skyborn variants, class setting on/off,
  fresh and mid-zone characters, chapter transitions, Scan guide, reload and zone
  entry. Verify Skyborn's actual 94947 hand-in before 98021. Full cross-zone work
  must remain rather than completing a short Westfall-only prefix.
- Unavailable pickups must defer temporarily and return after a confirmed offer;
  personal skips stay separate. Accepted unfinished work and unknown work must
  not create a false Guide complete. Check onward breadcrumbs and Sweet Amber as
  optional later support, without treating it as a low-level Westfall route.

Native beta checks remain pending. This focused branch commit and draft review
PR leave release and Discord publishing to main development.
