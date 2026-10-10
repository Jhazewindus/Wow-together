# Felwood guide review — 9 October 2026

Refreshed on 10 October against main cbd1e760 (addon 0.8.65). The queued prompt's 8 October / 0.8.59 baseline is superseded by before-audit.json and before-flow.json, freshly generated from current main before the Felwood data edits. Scope covers all four compiled Horde/Alliance 41–50 and 51–60 guides, including cross-zone work and class quests. Route and map calculations are host estimates, not verified terrain or optimality.

## Evidence and changes

The primary current source is Questie/QuestieDB Forever at pinned revision e0a6eaa86f181ac99262e34126bcd2ed1a1712d6. All 24 downloaded source-file hashes matched the repository's pinned source manifest. pinned-facts.json retains relevant structured facts and field origins without quest prose; direct-inventory.json retains the 87 direct Felwood catalogue records before corrections. source-facts.json records public source URLs, hashes and the limited facts used. Public HTML was read as reference material only; raw pages and quest prose/comments are not committed.

- 5385, The Remains of Trey Lightforge: item 13562 is supplied for delivery from NPC11020 to NPC11019. It is no longer represented as a separate farm objective. No additional actor or source position is inferred.
- 6131, Timbermaw Ally: start and return are Grazle (NPC11554), placed at a current Felwood spawn (map 1448, 50.93/85.01). Existing three five-kill requirements remain. The quest is absent from pinned Questie quest facts; no prerequisite or reputation threshold is inferred from that absence. Native offer availability still needs confirmation.
- 7602, Flawless Fel Essence: existing Azshara point/item 18624 is retained. Missing item 18622 work is mapped to Jaedenar Legionnaire (NPC9862) in Felwood; item 18623 to Felguard Sentry (NPC6011) in Blasted Lands. This is a cross-zone class quest, not a Felwood-only loop.
- 8421, The Wrong Stuff: existing ten Rotting Wood are preserved, and the four Bloodvenom Essence (20614) are mapped to current Felwood Tainted Ooze NPC7092.
- 5883–5886 and 5888–5891 are excluded from ordinary leveling as skill-rank-1 profession quests (Mining, Herbalism, Skinning, Enchanting). Their catalogue records and faction/race gates remain. Hunting variants 5882 and 5887 are not excluded.
- 7602/8421 remain Warlock-only; 7632/7635 remain Hunter-only. The latter's raid cache / raid-drop locations are not given fictional world coordinates. Their unknown pickup/work stages remain visible.

No repeatable quest with pinned specialFlags == 1 appears in the four compiled Felwood guides. Existing repeatable handling remains untouched. Reviewed direct Felwood quest facts exposed no requiredMinRep or requiredMaxRep gate for relevant entries; no reputation gate was added. Elite/group content remains available. No shared routing, eligibility, lifecycle or UI code changed.

## Refreshed coverage and route comparison

The scoped static audit checks 66 source points across four guides. The 41–50 guides each have 13 actions, three quests, and zero remaining unknown-location steps (down from two); no static pickup, objective or hand-in coordinate gap remains in those short sections. The 51–60 guide has 119 Horde actions / 34 quests and 134 Alliance actions / 37 quests. Each retains three unknown-location steps: pickup 7632 and objective work for 7632 and 7635. These are class-specific raid stages with no safe outdoor coordinates. Remaining unverified pickup requirements are 8419/8420 for Horde and 5249/8419/8420 for Alliance.

Profession exclusions remove 12 actions per high-level guide (four three-stage quests); all other quest/action identities remain present. The correction for 5385 removes a false gather stage. Grazle's newly mapped point changes the compiler's automatic short-guide sequence. The complete before/after repricer is saved in full-route-reprice.json; it reports a review-required guard, so these data changes need main-developer review of the existing optimizer tradeoff:

- Both short guides reduce estimated distance (Horde 6,325→5,542; Alliance 4,164→3,381), but the new order is marked invalid and endpoint comparison differs. Peak log use rises 1→2 and reward XP available before work drops 13,200→4,400; quest 6131's three work rewards move later. This is a route/order behavior change from newly mapped data, not a claim of an improved complete route.
- Horde 51–60 preserves actions and endpoints and remains valid in all four repriced starting states. Estimated distance drops 325,653→288,798 and uncertain legs 21→19, while reward XP before work drops by 23,157–30,000, delaying 7602 work.
- Alliance 51–60 preserves actions and endpoints and remains valid in all four states. Estimated distance drops 334,112→312,721 and uncertain legs 44→42, while reward XP before work drops by about 180,000–196,070; work on 5158, 5159, 5165, 5242 and 7602 is delayed in the comparison.

The standard flow audit confirms all four plans compile and replay, but that does not override the independent repricer failure. We did not edit shared engine behavior. The data candidate is submitted with this tradeoff for review; it does not certify a route sequence. Full-zone content stays included rather than optimizing a shorter prefix.

## Validation

- test_felwood_coverage.py: 7 tests pass for delivery semantics, exact Grazle coordinates/quantities, profession classification, class masks and setting, unknown raid locations, correction idempotence and conflict guards.
- audit_quest_guides.py --zone Felwood: all four guides compile; 66 static points checked; two short guides have no source gaps, and two high-level guides retain the explicit gaps above.
- audit_quest_flow.py --zone Felwood: all four guides replay (13/119 Horde and 13/134 Alliance actions).
- reprice_quest_stage_routes.py: review required / guard fails for the documented order and reward timing differences. No claim that this guard passes.
- Full catalogue audit checks 152 guides and 11,838 source points, five more than the refreshed main baseline (11,833); the new coordinates are all in Felwood. The full result is saved in global-audit.json.
- The first full host run on the previous checkout executed 1,678 tests and found a stale expected catalogue fingerprint. After syncing main 0.8.65, the focused fingerprint suite also exposed its now-stale dungeon-map digest. Both expected digests now reflect reviewed data changes; the other four dataset fingerprints match. All 10 memory/fingerprint tests passed against the refreshed data, and all 162 zone-coverage regressions passed before syncing the unrelated 0.8.65 changes.
- Host data and Lua behavior use the repository's Lua 5.1 runtime and interface 16001 mocks; direct lua5.1 is not separately installed. Host tests cannot confirm beta quest offers, profession recognition, loot/raid locations, map rendering, or walkable approaches.

## Player checklist

- Fresh and in-progress Horde and Alliance characters: record level, class, build, active guide chapter, accepted/finished prerequisites, and whether Grazle offers and accepts 6131. Check objective counts at the Deadwood camps and actual return to Grazle.
- On Warlock, verify all three Flawless Fel Essences, especially the Jaedenar and Dark Portal sources, and the four Bloodvenom Essence plus ten Rotting Wood for 8421. Confirm current drop actors and the cross-zone leg to Blasted Lands.
- On Hunter, confirm how Ancient Leaf is obtained and where Mature Black Dragon Sinew drops/turns in; keep raid-only coordinates unknown until verified.
- Check the Salve profession quests with and without each required profession; ensure ordinary guide scope and the existing class-quest setting behave as intended.
- Walk Emerald Sanctuary/Grazle approaches, Jaedenar tunnels and cave approaches, Deadwood camps, Timbermaw Hold tunnel, and the Blasted Lands handoff. NPC positions do not prove walkable terrain.
- Test fixed zone order, automatic progress, low-level prerequisite exceptions, temporary deferrals versus manual skips, elite/group visibility, partial completion and complete-zone completion. Record any native offer, gate, map, routing or chapter discrepancy.

No native beta behavior is claimed as verified by this review.
