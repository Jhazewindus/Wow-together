# Stranglethorn Vale review, 8 October 2026

Refreshed baseline: guides/coverage c24e97fd29f7f0ec44a87a20d079d2e69eb058c9,
including main 09155ca265278572649a3529b8ce7ea1b4eb8431 / 0.8.61.
All 132 compiled quest IDs and 885 actions across both factions and all three
chapters remain. This is a researched data candidate requiring coordinated
route review and native beta validation before merge.

## Supported corrections and evidence

Eight records change: 3511/3621 retain supplied delivery items and actual
hand-in requirements without farming instructions; 592 uses the Soul Gem on
Yenniku and requires one Filled Soul Gem; 8551 requires one chest and uses the
current Captain Smotts point. Current exact-ID 8552/8553/8554 gain supported
Captain/Sprogger conversations and returns. The Sash retains unknown item
acquisition; Facing Negolash gains its verified cutlass requirement while its
lifeboat lure stays unmapped. Zimmix 97331 gains an original escort instruction
with unknown location, preserving the actual 97329 hand-in dependency.

Captured facts cover 132 quest pages, 123 linked entity pages, a 129-row category
list and seven entity searches. All 24 pinned QuestieDB file hashes were verified
at e0a6eaa86f181ac99262e34126bcd2ed1a1712d6. JSON files retain URLs, dates, IDs,
source tiers and exact before/after records; no external routing code or quest
prose is incorporated. Initial captures succeeded; later three NPC requests
returned 403 and further requests stopped. Secondary captures and unavailable
requests are retained explicitly. Search identity alone does not prove position.

Distinct missing pickup/objective/hand-in IDs fall 13/15/14 → 11/11/11;
12 uncertain pickup requirements remain. Two audited unknown counts become
verified one-item requirements. See review.json for exact remaining IDs.
The global audit retains 152 sections and checks 11,831 source points; the
source queue contains 438 unresolved records. These counts are source coverage,
not complete terrain, current offers or beta verification.

## Withheld mappings and identity conflicts

Green Hills 338 still has unknown chapter acquisition. A four-chapter reward
prototype is retained as unapplied evidence: the current compiler scheduled the
main quest's work before chapter hand-ins that award the needed items. Its
15 page requirements remain intact. Completion dependencies need main-developer
coordination; no shared engine edits or artificial pickup prerequisites were added.

Old Captain variants 614/615/618/620 remain separate from 8551–8554. Pinned and
current minimum/quest levels conflict, so their gates and coordinates cannot be
transferred by title. Arena Master item evidence points to 7810, not missing
7908. Quest 1036 has unmodeled reputation work; Warlock 1796 needs craft/trade
acquisition rather than an invented Menara work point. Beta tablets, keys,
caged cook and stolen shipments remain unknown where no factual work/giver
position is available. The category list is a source inventory, not permission
to include every repeatable/endgame/placeholder in ordinary leveling.

## Whole-route validation and coordination

All six generated previews are internally valid; all 885 actions survive.
Same-facts strict comparisons evaluate four starting states for each chapter.
31–40 and 51–60 are unchanged. For Horde 41–50, estimated travel improves
291,980.12 → 284,778.63, peak log stays 9, XP shortfall stays 332,658 and
uncertain legs stay 22. Rewards arrive later before 348/8553/8554/614/618.
The final action changes from unknown 618t to mapped 8552t. All four strict
Horde mid-chapter replays fail the original endpoint invariant, despite internally
valid candidate previews. This endpoint change needs explicit coordinated review.
Alliance 41–50 travel improves 334,478.24 → 321,057.68, peak log falls 7 → 6,
shortfall stays 336,609 and uncertainty falls 29 → 28; rewards are delayed before
614/618. Its endpoints and strict replay validity survive. The optimization
guard exits REVIEW REQUIRED. No claim of fully optimized or walkable routes.

Ten focused tests, all 52 zone regressions and 122 transport/class/offer/session
checks pass. All 86 TOC Lua files compile under Lua 5.1/interface 16001.
Atomic correction conflict rejection and idempotence pass. Entity data, world
completion checks and XP baseline remain unchanged. The last full suite was
1,540/1,541 on the Elwynn baseline, with the known historical catalogue
fingerprint failure; a combined queued-zone run is pending.

The retained travel review covers Booty Bay/Ratchet shipping and Grom'gol's
Orgrimmar/Tirisfal zeppelins. Existing directed links and faction access remain;
no personal taxi unlock, walkable water crossing or surveyed dock approach is inferred.

## Native player checklist

Record addon commit, beta build, race/class/faction, chapter/level, party and
class setting. Mark each Pass / Fail / Skip and attach actual offer/completion
observations rather than assuming acceptance is a hand-in.

1. Both factions, fresh and mid-zone: traverse complete chapters, Scan guide,
   reload, pause/resume and zone re-entry; verify fixed progress and handoffs.
2. Deliver Hetaera's Blood and Shipment to Galvan without farming supplied
   items; native completion and actual hand-in remain required.
3. Use the Soul Gem on Yenniku; confirm one filled gem and actual Nimboya return.
   An empty gem, proximity or an absent native objective must not complete work.
4. Check Captain variants individually: actual item-start, Smotts/Sprogger
   offers, chest count and cutlass/lifeboat event. Record exact lure approach,
   item recipe and spawn context before closing the Negolash gap.
5. Escort Zimmix only after the real preceding hand-in. Record pickup, escort
   start/path/end and Wharfmaster return; verify adjacency and failed-escort recovery.
6. Green Hills: retain all pages and chapter hand-ins; record item rewards and
   main quest offer timing. Do not treat accepting a chapter as receiving its item.
7. Check elites/group choices, Warlock class opt-out, unknown offers returning
   after confirmation, personal skips, boat/zeppelin boarding and faction access.
   Deferred or accepted unfinished work must not produce false Guide complete.

Final [combined host validation](../coverage-integration-2026-10-08/README.md)
passes 1,562/1,563 tests, including all 64 zone regressions; the sole known
historical catalogue fingerprint failure remains. Native checklists and
coordination requirements above remain outstanding.
