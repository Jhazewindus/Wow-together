# Tirisfal Glades review — 9 October 2026

Current follow-up: [termite output-count correction](termite-count-follow-up/README.md) restores the counted gather instruction while preserving the supplied jar; generic use text was treating 100 termites as 100 mound targets. Earlier source/route evidence below is retained as its dated baseline.

Refreshed addon 0.8.61 at guides/coverage `5bec9dfde8fdcbc70ae59f808a0e4b445ce88117`; main `09155ca265278572649a3529b8ce7ea1b4eb8431`. The supplied 0.8.59 snapshot is historical. Inventory: 66 direct category records, 96 compiled IDs across Horde 1–10, 11–20 and 51–60, with class/cross-zone continuations. Three direct uncompiled records remain: Dormant Shade, Candles of Beckoning and Welcome!; their absent pinned quest facts do not justify new offers or ordinary route insertion. Twenty-four Orc/Undead class/Ironborn chapter profiles retain the 96-ID union. Alliance/Horde identity restrictions and existing Include class quests remain unchanged.

Ten guarded corrections map Rudolph Gelhardt's head to its actual published drop/spawn, preserve the supplied trainer scroll, retain looted residue acquisition without a second farm, use the supplied termite jar for 100 termites, interact with the real Northridge barrel, distinguish burial input from hand-in requirements, and interact with six Webbed Victims. Published escape, observed-conversation and punishment work becomes explicitly incomplete. No profession gate, race/class mask or universal hidden prerequisite is inferred from a name.

## Evidence and gaps

[pinned-facts.json](pinned-facts.json) retains typed facts/origins and all 24 verified hashes from [QuestieDB revision e0a6eaa](https://github.com/Questie/QuestieDB/tree/e0a6eaa86f181ac99262e34126bcd2ed1a1712d6). [source-joins.json](source-joins.json) retains exact name/level/minimum matching and decisions. Head item 270435 explicitly drops from NPC 259431; one actual published spawn at map 1420 11.40/64.36 is selected, not an average or the giver. Existing eight Drudge/six Zealot/one-head counts and Undead Paladin masks remain. SourceItemId 9546 distinguishes supplied scroll from missing farming. No third-party quest prose/engine/route code is copied. Available verified cache is used; previously repeated source-access denials prevent claims of fresh or exhaustive comment/forum research.

Objective gap union three → four: 3095/91317 close; 99134/99144/96896 are newly exposed; 99141 remains unknown. No pickup/return gaps are recorded. Six uncertain class pickup IDs and unknown Ulag/Darkhound counts remain. Patience's report item names do not establish acquisition by talking to similarly named NPCs; unknowns stay explicit. Published Darkhound typed objective conflicts with prose naming only Neophytes/Enforcers. Existing alternate class-quest branches/exclusivity need actual offer observations, not accepting/finishing other objectives.

## Route and shared behavior review

[coordination-proposal.json](coordination-proposal.json) includes the reproduced Marla order issue: both original and candidate plans put grave interaction before remains acquisition, although the factual goal requires acquisition first. Removing the false extra hand-in does not fix shared stage dependencies. Discipline still has conflicting mandatory target/count instructions versus the published five-of-many goal; supplying the motivator and exposing unknown mechanics does not certify those instructions. Coordinate target-choice/completion and input-before-use support before merge; no shared runtime modules were authored.

The raw same-scope guard rejects one newly added unlocated Discipline placeholder. [scope-reconciliation.json](scope-reconciliation.json) retains all old actions and adds only that placeholder before its actual hand-in. Head work replaces its existing unknown occurrence rather than adding an action. Complete chapter actions 222/170/6 become 223/170/6; all 96 IDs and onward endpoints remain. Twelve same-corrected-scope starting states keep both orders valid under existing host invariants, which do not model Marla's inventory dependency. At 1–10 estimated distance falls 202,213.40 → 164,646.26 and peak log 13 → 12, but rewards are delayed before twenty IDs. At 11–20 distance rises 185,317.04 → 185,500.94, peak log 14 → 16 and summed rewards before work decrease, with four delayed IDs. Guard: REVIEW REQUIRED. Four 51–60 states preserve unchanged same-facts metrics. These are coverage corrections/host estimates, not native or optimal-terrain claims.

## Player checklist

- Start fresh Undead and applicable Ironborn characters; compare both starter chapters and class settings. Follow Deathknell → Brill → Undercity handoffs; scan, reload and zone entry must retain fixed order and progress.
- Read supplied class scroll, speak with the correct trainer and hand in real parents before follow-up offers. Observe class/race restrictions and alternative branches; record completed hand-ins/actual offers separately from accepting/finishing work.
- Verify Tarnished eight Drudges/six Zealots/one Rudolph head, actual boss spawn/approach and Undead Paladin access. Confirm residue loot starts its delivery without a second farm.
- Acquire Samuel's remains before burial at Marla's Grave. The recorded current order is a shared review blocker; confirm burial consumes the input rather than requiring an extra item at Elreth. Free six Webbed Victims without attacking friendly victims.
- Record Patience report acquisition dialogues/locations. Verify Discipline's supplied motivator, which five targets count and whether choices are alternatives. Existing kill fallbacks/counts need coordinated correction before using that guide as verified advice.
- Escort Bareth to actual safety and observe Danitha/Leonid's event; record trigger/path/adjacency. Accepted unfinished or temporarily deferred work must not report Guide complete. Manual skips remain personal; actual offers can restore temporary deferrals.
- At appropriate level gather 100 termites using the supplied empty jar in Eastern Plaguelands, return to Mickey, then place/interact with the actual Northridge barrel in Western Plaguelands. Confirm the parent's actual hand-in and onward barrel follow-up.
- Check crypt/hollow approaches, Undercity lifts/interiors and neighbouring Silverpine destinations. Keep elite/group quests visible and optional. Map points/flight masters are not proven paths or personally unlocked connections.

Host checks cannot establish native beta offers, objective completion, escort behavior, map APIs or walkability. This remains a draft data review with explicit engine conflicts, not a release.

Neighbouring Western Plaguelands preserves all 197 Horde / 210 Alliance actions, endpoints and unchanged same-corrected-facts metrics in eight strict states (PASS). This validates the shared termite-chain effects without a new route claim.

The initial 121-test zone run failed nine idempotence assertions after a source-note edit was made after packing. Reapplying that note updated only 91317's evidence metadata; the second application changes no records. Initial failure/source-refresh logs are retained; current captures were refreshed after packing. No quest-stage fact or test assertion was changed to hide the failure.

Final validation: all 121 zone regressions (including six focused Tirisfal checks), 122 transport/class/offer/session checks, 49 importer/source tests and 86 Lua 5.1/interface-16001 compilation checks pass. Corrections now reapply without changes. Entity/world-completion/XP data remain preserved. No new full-suite/native-beta result is claimed.

Global regeneration changes only Horde Tirisfal 1–10/11–20 audit rows: 152 sections / 11,829 points, 33 recorded gap-free and 375 unresolved ordinary records.
