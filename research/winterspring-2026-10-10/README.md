# Winterspring quest-guide refresh

Reviewed 10 October 2026 on addon **0.8.65**. The branch was clean at refresh
start (`guides/coverage`, `ff004b0`); its current main baseline is
`cbd1e7608dc32c2080d8b1d967fb577c10084053`. The supplied starting audit named
0.8.59 / 8 October; I refreshed the exact-zone reports before relying on those
leads. This refresh makes no new shipped quest-data or routing change: the
Winterspring corrections from the 9 October report are already present and the
current source gaps persist.

## Refreshed scope and evidence

The scoped Lua 5.1 audit compiles both fixed Winterspring guides and checks **57
source points**. It sees **44 Alliance** and **37 Horde** catalogue/dependency
quests, comprising **142 Alliance** and **116 Horde** actions. The captured
standard Alliance/Horde route sequences retain every action and endpoint and
pass route invariants. No mapped pickup or hand-in coordinates are missing; no
objective quantity is flagged unknown. The audit still has objective-location
gaps for Alliance **975, 5247, 8471** and Horde **975, 8471**; 3 Alliance
pickup requirements remain unverified (**5244, 5249, 5250**). Neither guide is
source-gap-free. These numbers describe available static source mapping, not
in-game completion or terrain coverage.

The source evidence for earlier corrections is retained in the
[9 October full review](../winterspring-2026-10-09/README.md), including the
exact QuestieDB Forever URLs and commit, the 24 verified manifest hashes,
`source-joins.json`, `pinned-facts.json`, `validated-hashes.json`, and the
stage/scope decisions. Its source pin is
[e0a6eaa86f181ac99262e34126bcd2ed1a1712d6](https://github.com/Questie/QuestieDB/tree/e0a6eaa86f181ac99262e34126bcd2ed1a1712d6/data/Forever).
That review also retains original Wowhead Forever, Warcraft DB, unchanged-ID
classic-db, and source-manifest references as applicable. No new public page
capture or beta observation is represented by this audit refresh.

Comparison of the previous reviewed catalogue at `09155ca` with this branch
shows the already-reviewed **5084 Falling to Corruption** change: the return is
an interaction with the published Deadwood Cauldron object, with existing
coordinates retained. No other Winterspring catalogue quest changed since that
review. The primary source fact and exact quest/entity IDs remain in the prior
report. The current `current-audit.json` and `current-flow.json` are fresh
machine-readable snapshots tied to 0.8.65 module and dataset hashes.

## Existing data decisions and remaining knowledge gaps

The ten prior stage corrections remain: interact with the investigation objects;
preserve the looted necklace/log as item-start inputs without farming them again
after acceptance; treat later deliveries as supplied items with actual hand-ins;
and use the supplied mechanical yeti on all three mapped targets. The distinct
crystal hand-ins remain ordered before their follow-up pickups. The prior
profession-only exclusions for Fiery Plate Gauntlets, Lorax's Tale and A Yeti of
Your Own remain ordinary-scope exclusions, while their catalogue records and
source gaps are retained. Ordinary Yeti and material-delivery quests remain in
scope. Class quests continue to follow the existing setting. Elite/group choices
remain visible.

Open work stays explicit:

- **975 Cache of Mau'ari:** the cache/trinket/event objective trigger and work
  location are not mapped by the available evidence.
- **8471 Winterfall Ritual Totem:** the item start is retained; its reputation
  objective (`faction 576`, published threshold 0) is still unmodeled and its
  work location is unknown.
- **5247 Fragments of the Past:** the acquisition/work point for Enchanted
  Thorium remains unknown; material delivery is not evidence of a profession
  eligibility gate.
- **5244 / 5249 / 5250:** actual pickup availability/requirements remain
  unverified for Alliance. A known NPC position is not proof the offer is live.
- Timbermaw Hold passage, the approaches through the tunnel, neutral hub/guard
  behavior, personal flight connections, and safe high-level cave approaches
  require in-game checks. A border point or spawn does not establish a
  walkable shortcut.
- High-level elite/event and dungeon-linked preparation remains visible, but
  this evidence does not prove a physical dungeon entrance, safe route, native
  summon requirement or universal group requirement.

## Complete-flow snapshot

The fresh two-faction flow capture keeps **116 Horde / 142 Alliance** actions,
valid complete action sequences, no blocked travel legs and peak quest logs of
**9**. Estimated distances are **305,370.85** Horde and **443,755.84** Alliance
map units; uncertain travel legs are **24 / 33**. Quest-reward-only level
shortfalls from level-51 entry are **1,150,620 / 1,954,540 XP**. These are
replay estimates, not beta XP progression or terrain-safe travel; combat XP and
some item requirements are unknown. The audit's own before/after distances are
identical because this refresh did not change the guide. Do not interpret a
shortfall, pickup uncertainty, or access concern as permission to omit full-zone
work or alter shared guide behavior.

## Validation and player checklist

See [`validation.txt`](validation.txt) for exact commands and results. The
zone-specific suite passes **7/7** tests; route regressions pass **18/18**. The
Lua 5.1 host loaded all **87** TOC Lua files for interface **16001**. The
scoped guide and flow audits pass their invariants. No shared routing,
eligibility, guide lifecycle or UI module was changed. The cloud checkout was
already provisioned with its pinned Python test interpreter and repository
caches; Git read access was verified with `git ls-remote origin HEAD`. No
onboarding configuration draft was needed.

Player verification remains necessary:

1. On Horde and Alliance characters, confirm Everlook, Donova Snowden and
   Starfall offers and actual completed hand-ins, especially uncertain 5244,
   5249 and 5250. Record build, level, race/class, profession and reputation.
2. Confirm the crate, wagon and cauldron credit through interaction, and verify
   each actual follow-up offer only after hand-in.
3. Accept the necklace/log item-start quests while carrying their starter items;
   ensure no duplicate farm is instructed, then confirm later recipient and
   quantity at hand-in. Confirm both crystal handoffs in sequence.
4. Test the supplied yeti on all three named targets and return it; check
   ordinary quests with class-quest display disabled and no Engineering.
5. Record actual Cache of Mau'ari trigger and Ritual Totem item/reputation/work
   conditions; verify Enchanted Thorium acquisition without assuming a vendor or
   drop.
6. Test Shy-Rotam and other elite/event steps, high-level dungeon handoffs,
   Winterspring/Felwood tunnel passage, both approaches and personal flight
   connections. Do not infer walkability from pins.
7. Check fresh and mid-zone progress, supported race/class variants, Scan guide,
   reload, chapter transition and zone entry. Ensure offered deferrals can
   return, personal skips remain separate, and accepted unfinished work cannot
   report Guide complete.

Native beta behavior remains unverified. No release, tag, archive or Discord
publication was made.
