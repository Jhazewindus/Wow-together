# Winterspring facts and ordinary guide scope

Reviewed **9 October 2026 (Europe/Amsterdam)** on addon **0.8.61**, baseline
`bb61c3ce86e8f4e7522c94b92f33b2c11628679a`, branch `guides/coverage`;
main `09155ca265278572649a3529b8ce7ea1b4eb8431`. The supplied 0.8.59
baseline was refreshed before editing. This review retains native offer/access uncertainty.

## Sources and corrections

Primary source: [QuestieDB Forever at the pinned commit](https://github.com/Questie/QuestieDB/tree/e0a6eaa86f181ac99262e34126bcd2ed1a1712d6/data/Forever),
`e0a6eaa86f181ac99262e34126bcd2ed1a1712d6`. All **24 manifest hashes** were
verified in the available cache. `source-joins.json` retains URLs, source tiers,
exact IDs and decisions. `pinned-facts.json` retains typed quest/entity facts and
origins without copied quest prose. Identity-matched converted-baseline facts
are distinguished from beta deltas/observations and current captured positions.
The review date is not a new native observation. No provider or routing engine
was imported. Previously denied public hosts were not retried: available cached/
repository evidence was used, with no new comments/forum review or claim that
all public sources have been exhausted.

Ten stage records change:

- **4861/4863 Enraged Wildkin** and **5084 Falling to Corruption** interact with
  the exact published return objects: Damaged Crate, Jaron's Wagon and Deadwood
  Cauldron. Exact quest `finishedBy` / object `questEnds` joins support interaction,
  rather than conversation. Current coordinates and actual hand-in gates remain.
- **4882 Guarding Secrets** and **5123 The Final Piece** retain their initial
  looted item-start acquisition (necklace **12558**, log **12842**). After accepting
  the item-started quest, remove the redundant second farm; keep the actual item
  hand-in and mapped recipient. Items are already held when starting these quests,
  not newly handed out by a giver.
- **4883 Guarding Secrets**, **5128 Words of the High Chief**, **5252 Remorseful
  Highborne** and **5253 The Crystal of Zin-Malor** retain supplied delivery items,
  actual hand-in quantities and faction recipients. Remove false necklace/log/
  crystal acquisition work, retaining mapped conversations/returns. The crystal
  goes through **10684 → 11079 → 3516**, ending in Darnassus; actual 5248/5252
  hand-ins precede the next pickups. Crystal supplied metadata is preserved;
  unrelated world completion data is unchanged.
- **5163 Are We There, Yeti?** records the explicit supplied mechanical yeti
  **12928**, with supplied count unknown. All three existing **use** targets
  remain: Legacki **10978** in Everlook, Sprinkle **7583** in Gadgetzan and Quixxil
  **10977** in Un'Goro. Count **one per target**, spell/action, actual 977 hand-in,
  cross-zone trips and return stay. This ordinary quest has no Engineering gate.

Three evidenced profession-only records are quarantined from **ordinary leveling**:
**5124 Fiery Plate Gauntlets** requires Blacksmithing **164/275**;
**5126 Lorax's Tale** requires Blacksmithing **164/285**;
**8798 A Yeti of Your Own** requires Engineering **202/250**.
Exact name/level/minimum identity agrees with the pin's explicit `requiredSkill`.
The existing data exclusion mechanism preserves their catalogue, source gaps,
materials and actual prerequisites. This is not a class restriction, guessed
classification from a title, solved material acquisition, or deletion. Ordinary
Yeti work and material-delivery **5247** remain. Hot Fiery Death **5103** also has
published Blacksmithing 275 context and remains outside the current compiled
ordinary scope; no unrelated profession module is edited.

## Full scope, gaps and access

There are **57 direct-category records**, retained in `direct-inventory.json`.
The complete remaining ordinary scope has **56 unique IDs** across both faction
51–60 chapters, including relevant cross-zone prerequisites and continuations.
Alliance **154 → 142** and Horde **128 → 116** actions remove only the **24
profession action occurrences**. Every remaining required action and endpoint
survives. Existing E'ko/Wintersaber repeatables and repeatable gear exchanges
remain outside ordinary compilation; all source records are retained. Exact
uncompiled IDs and onward dungeon/Felwood/Western Plaguelands records are in
`continuations.json`. Ten standard/new-race faction/race profiles retain complete
saved orders under mid-zone progress. Chapter names are not native minimums.

Recorded objective-gap IDs **6 → 3** in the union: **5252/5253** genuinely close;
**5124** remains incomplete in the catalogue and is excluded from ordinary scope.
Alliance ordinary gaps are **975/5247/8471**; Horde **975/8471**. Pickup and return
gaps stay zero. Uncertain pickups fall **6 → 3** only because the three
profession records leave ordinary scope; **5244/5249/5250** remain uncertain.
No unknown objective quantity is introduced. The source queue falls **378 → 373**
through two closures and three scope exclusions, not five completed researches.

**975 Cache of Mau'ari** has no supported mapped cache/trinket/event trigger in
this evidence. Mau'ari's known pickup/return cannot substitute for unknown work.
**8471 Winterfall Ritual Totem** retains its initial item acquisition and the
published reputation objective **faction 576 / threshold 0** as unmodeled work.
Do not clear that requirement just because Kernda's turn-in is mapped.
**5247 Fragments of the Past** retains its actual collection/material quantities
and remaining Enchanted Thorium acquisition gap. Crafting/trading material is not
an evidenced profession-only eligibility gate. Excluded **5124** still lacks
precise gauntlet/bar acquisition; its profession parent is not a generic dungeon
access gate. No guessed vendors, safe cave entry or material farm closes gaps.

Current Everlook/Donova/Starfall hubs, Winterfall hand-in chain, Elite Shy-Rotam/
Ursius/Brumeran work, altar guardian event and relevant Burning Steppes/Felwood/
Darnassus/Un'Goro/Tanaris handoffs remain. Lower-level support is retained only
through existing actual continuation links; no new low-level exception or dungeon
entrance gate is inferred. The unchanged class setting still filters actual
class work; ordinary neutral quests stay ordinary.

`access-handoffs.json` retains current published travel provenance and explicit
Winterspring/Felwood border/service nodes. Timbermaw Hold needs native passage/
reputation and safe tunnel approach checks. A border node or NPC spawn does not
prove a traversable corridor, mountain shortcut, neutral guard behavior or an
unlocked flight connection. Shared reputation/offer or travel presentation
changes remain an **unapplied** coordination proposal. No shared routing,
eligibility, lifecycle or UI modules were authored.

## Complete-route result and validation

A comparable old catalogue applies only the same three reviewed ordinary
exclusions before capture. Both complete orders are then repriced on identical
corrected facts; quarantine and removed false farming are not optimization gains.
All **eight Winterspring states** are valid for old/candidate orders and preserve
all **116/142 actions and endpoints**. Horde travel improves **301,222.89 →
297,246.12**; Alliance **435,929.82 → 394,869.43**. Log peaks stay **9**, no blocked
leg increases, and Alliance uncertain legs improve **32 → 30**. However, Alliance
rewards arrive later before **5247/5248/5252**, so the guard remains **REVIEW
REQUIRED**. Chapter-entry quest-reward-only deficits remain 861,920 Horde /
841,840 Alliance in strict replay: this does not establish a full ten-level XP
path. Estimates do not certify native walking time, terrain or an optimal route.

The two crystal corrections also affect Alliance **Eastern Plaguelands 51–60**.
Eight neighbouring strict states preserve **201 Horde / 217 Alliance** actions,
endpoints and valid orders. Horde metrics stay unchanged. Alliance travel improves
**621,261.98 → 591,273.70**, log peak stays **13**, uncertain legs **63 → 61**, but
summed reward XP before work decreases and reward **5249** arrives later. That
comparison also remains **REVIEW REQUIRED**; no shared optimizer change masks it.
Only both Winterspring and Alliance Eastern Plaguelands global rows change.

All **109 zone regressions**, **seven focused tests**, **122 transport/class/
offer/session checks**, **49 importer/source tests** pass. All **86 TOC Lua files**
compile under Lua 5.1/interface **16001**. Reapplication returns no changes;
conflicts fail atomically. Entity data, world completion checks and XP baseline
are unchanged. Global audit: **152 sections / 11,831 points / 33 recorded gap-free /
373 unresolved ordinary records**. Exact logs, comparisons and tested hashes are
retained. The prior combined full-suite result was 1,562/1,563 with the historical
catalogue fingerprint assertion; no new full-suite or native beta run is claimed.

## Player checklist

- Check both factions' Everlook/Donova/Starfall offers and actual hand-ins,
  including uncertain 5244/5249/5250. Record beta build, native level, race/class,
  profession/reputation context; acceptance/objective completion is not hand-in.
- Loot the necklace/log starters and verify that accepting them does not demand
  another farm. Carry their later deliveries and both crystal stages to actual
  recipients, confirming quantities and next offers only after actual hand-ins.
- Interact with the crate, wagon and cauldron. Check investigation/event credit,
  safe object approaches and follow-ups rather than a conversation with an object.
- Use the supplied mechanical yeti on all three named targets across their zones,
  then return. Ordinary Yeti work must remain with class quests disabled and
  without Engineering; check profession quests separately at documented ranks.
- Verify Mau'ari's actual cache mechanics and Ritual Totem reputation/offer
  conditions, material acquisition for 5247 and optional E'ko/reputation advice.
  Unknown work must remain visible and must not be satisfied by a nearby NPC.
- Check Shy-Rotam's native summon/preparation, elite/group choices, altar event,
  high-level outdoor/dungeon handoffs and safe Frostwhisper/cave/Timbermaw access.
  Record exact input/use/drop facts where this review lacks them; do not infer
  physical dungeon entry or kill counts from a precursor hand-in.
- Verify Felwood tunnel passage, both approaches, neutral hub/guard behavior and
  personal flight connections. Avoid unsupported water/mountain shortcuts.
- Test fresh and mid-zone characters, Horde/Alliance races including Skyborn,
  class setting, Scan guide, reload, chapter/zone entry and affected Eastern
  continuation. Full fixed order must survive progress; temporary deferrals can
  return after confirmed offers, personal skips stay separate, and accepted/
  unknown unfinished work must not produce a false Guide complete.

Native checks and shared decisions remain pending. The focused branch commit and
draft PR leave releases, tags, archives and Discord publishing to main development.
