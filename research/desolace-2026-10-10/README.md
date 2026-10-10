# Desolace quest-guide review, 10 October 2026

Refreshed from the current `guides/coverage` checkout at `f3657e1` (addon
0.8.66). The uploaded starting snapshot was dated 8 October; the scoped audit
was rerun against the current catalogue before source review. Evidence hashes
and source limits are in [`source-facts.json`](source-facts.json).

## Scope and changed data

The 37 Desolace catalogue records compile into five complete fixed guides:
Horde 31–40, 41–50 and 51–60; Alliance 31–40 and 41–50. The chapter labels are
guide sections, not verified minimum play levels. All 28 queued Forever quest
pages and 22 linked NPC/object/item pages were captured successfully on
10 October with the project capture tools. No source request was denied.

The applied additive source facts add **8 pickup points, 8 hand-in points and 1
objective work point**. They map the Highway Robbery campfire object to Bibbly
F'utzbuckle, On the Lam from Bibbly to Tokal in Dustwallow Marsh, A Conqueror's
Crown to Warug, Captain Pentigast's Carved Centaur Totems objective/hand-in,
and both Buying Friendship faction handoffs. Coordinates use current Forever
source mapping; a map point does not prove an accessible road or a live spawn.

Carved Centaur Totems (93224) now has its five-item Kolkar Scout objective and
published work area. The distinct-source count of 28 is retained as alternatives,
not 28 required kills. The newer pages also make the Kodo Roundup unknown Aged
Kodo interaction explicit, so its incomplete-location flag is now set. Its
interaction count stays unknown. Rexxar's Testament remains without a verified
local objective stage. Cherry for Your Thoughts? has its Tokal handoff, but the
Cherry Grog source remains unknown. The unresolved Advanced Target Dummy source
for Gizmo for Warug is unchanged.

The Magram/Gelkis records retain their existing Horde/Alliance identity masks,
explicit previous-quest candidates and current unverified pickup flags. QuestieDB
Forever literals and current quest pages name reputation conditions and chains,
but ordering/reputation reward text alone does not prove that a beta NPC requires
that standing before offering a quest. No new reputation gate was added. Class,
race or faction facts were not broadened to ordinary quests.

### Held for shared guide behavior review

Quest 79242's current page and entity pages identify Tokal, Illari Duskfeather,
Illari's Loot Cache and the required Illari's Key. The key's acquisition point is
still unknown. Marking the added objective incomplete made the current fixed
compiler remove the quest's acceptance, objective and turn-in stages from every
Desolace full-route flow. This data-only change would therefore alter shared
eligibility/guide lifecycle behavior. Its new facts are retained in this review,
but the shipped quest record is unchanged until the main developer coordinates
how an incomplete objective remains visible without falsely completing the
quest. No routing, eligibility, lifecycle or UI module was edited here.

## Refreshed source gaps

Counts below are distinct quest IDs across the five compiled guide sections;
per-guide appearances are noted in parentheses. The 8 October prompt was not
used as a substitute for the refreshed before audit.

| Gap | Before | After |
|---|---:|---:|
| Pickup coordinates | 10 (19 section appearances) | 3 (6) |
| Objective areas | 16 (32) | 11 (23) |
| Hand-in coordinates | 12 (22) | 5 (9) |
| Unverified pickup requirements | 15 (44) | 15 (44) |
| Unverified objective quantities | 0 | 0 |
| Fully gap-free guide sections | 0/5 | 0/5 |

The added points close pickup and hand-in gaps for quests 79229, 79235, 92743,
93224, 93227 and 94872. The page-supported work point closes the 93224 objective
gap. Quest 79242 remains in the reported gaps because its captured facts are held
back to preserve the existing action set pending shared-behavior coordination.
`audit-before.json` and `audit-after.json` retain exact remaining IDs and stages.

## Full-route comparison

The before/after flow replay uses the same faction/chapter scope and the complete
fixed action sets; the action ID/stage sets match in all five guides. The
before/after estimates are stored in [`flow-comparison.json`](flow-comparison.json).

| Faction / chapter | Actions | Estimated distance | Quest-log peak | Quest-XP shortfall | Reward XP available before work | Uncertain legs |
|---|---:|---:|---:|---:|---:|---:|
| Horde 31–40 | 139 | 492,811 → 385,076 | 6 → 6 | 339,905 → 346,155 | 2,306,545 → 2,307,145 | 82 → 77 |
| Horde 41–50 | 45 | 213,752 → 140,950 | 2 → 2 | 0 → 0 | 193,920 → 193,920 | 23 → 19 |
| Horde 51–60 | 12 | 45,710 → 45,710 | 1 → 1 | 3,108,900 → 3,108,900 | 4,620 → 4,620 | 4 → 4 |
| Alliance 31–40 | 150 | 551,760 → 384,119 | 10 → 10 | 163,900 → 163,900 | 3,184,150 → 3,212,900 | 75 → 68 |
| Alliance 41–50 | 53 | 179,489 → 114,826 | 3 → 3 | 0 → 0 | 365,770 → 365,770 | 24 → 18 |

The shorter estimates result from mapping newly supported starts/turn-ins and
replaying the unchanged full route model. The Horde 31–40 reward-only XP
shortfall increases by 6,250 in that estimate; the reward-timing tradeoff is
recorded rather than optimized away. These numbers do not measure actual travel,
XP earned from combat, safe paths, or terrain. The route replay validated all
five states; no global-optimality or terrain-optimality claim is made.

## Validation and player checklist

- Desolace scoped audit: five guide sections and 108 source points checked
  before and after; route invariants passed, while `--require-complete` returned
  its expected exit 2 because all five sections retain source gaps.
- Full-zone flow replay: five valid full guides, with identical action sets
  before and after the applied data changes.
- Focused Desolace regression tests: 4/4 passed. Full catalogue host audit:
  150 guides and 11,882 points checked. The packed catalogue loaded through the
  project Lua 5.1/interface-16001 host. Native beta behavior remains untested.

Player checklist: inspect fresh and mid-zone Horde and Alliance characters in
both 31–40 and 41–50 sections, plus Horde 51–60; confirm the linked offer and
hand-in sequence at Gurda/Warug/Uthek, Nijel's Point, Bibbly and Tokal; confirm
the coastal/zone handoff to Tokal on the live map; try Kodo Roundup and record
which kodo interaction counts; check whether the Karson quest chain offers the
captured quests and record actual faction standing/offer lists; confirm the
Carved Centaur Totems drop count and Kolkar Scouts; reload, enter Desolace and
Dustwallow, Scan, and check chapter transitions and full-guide completion.
Record actual NPC offers, item sources, cave/coast access and roads. Do not infer
that a missing source step is complete or that a straight marker is walkable.
