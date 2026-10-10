# Eastern Plaguelands audit refresh — 10 October 2026

This refresh covers addon 0.8.66 on `guides/coverage` at commit `225363b41d0faa37b9fccfe092a2677e18a496b2`. The supplied 8 October / 0.8.59 baseline is superseded by the detailed 9 October review in [`../eastern-plaguelands-2026-10-09/README.md`](../eastern-plaguelands-2026-10-09/README.md). That review corrected the required-item distinction for Marauders of Darrowshire (5206) and To Kill With Purpose (6022), using the pinned QuestieDB Forever data. Its evidence, all 24 verified source-file hashes, direct inventory and original before/after reports remain in that directory.

No Eastern Plaguelands catalogue fact or guide behavior changed since the prior review. The refreshed scoped audit is identical to `research/eastern-plaguelands-2026-10-09/after-audit.json` on every reported value. The current full-flow captures have the same faction/chapter action sequences, ordered stops and every scalar metric as `after-flow.json`. The audit checks 102 exact-zone catalogue records and 252 static source points across the Alliance and Horde 51–60 guides. Both full guide states validate. These comparisons confirm the already-reviewed work remains intact; they are not new source discoveries.

## Source gaps

Relative to the pasted 8 October prompt snapshot, missing objective quest IDs fall 19 → 14 unique across the two factions; pickup coordinate gaps remain the two records 5464 and 8946; hand-in coordinate gaps remain zero. The current faction-specific objective IDs are:

- Alliance: 5149, 5206, 5247, 5513, 5517, 5862, 6026, 8946, 9121, 9122, 9123, 9141.
- Horde: 5149, 5206, 5513, 5517, 5862, 6022, 6026, 6146, 8946, 9121, 9122, 9123, 9141.

Unverified pickup requirements remain faction-specific (17 Alliance, 14 Horde; 18 unique IDs across both), and no objective quantities are unknown. The compact full lists and all flow metrics are in [`coverage-summary.json`](coverage-summary.json), with current host reports in [`current-audit.json`](current-audit.json) and [`current-flow.json`](current-flow.json).

The previous source report still identifies the actionable gaps: Menethil's Gift (5464) has an unknown object pickup position; Proof of Life (8946) has an unknown Ysida Harmon start; Pamela's Doll, Fragments of the Past, That's Asking a Lot and Nathanos' Ruse retain unmapped item/event objective stages. The 5206 five Resonating Skulls and 6022 Coagulated Rot preparation/use steps must remain distinct from their Fetid Skull and Living Rot inputs until the conversion/use locations are supported. Do not substitute the Chapel dialogue point for the 5464 object or guess the intermediate work points.

Keep the two Argent Dawn mantle quests' reputation conditions distinct from ordinary quest eligibility. Preserve the 9121/9122/9123 Naxxramas variants and their separate 9,000/21,000/42,000 reputation facts and alternatives; live offer thresholds are not confirmed. Keep 9141/9142's actual token facts without inventing a profession gate. The old-zone review's pinned source fields and current Forever fact URL are cited in the 9 October evidence report.

## Full-flow comparison and limits

Both current previews retain every action and the same order as the 9 October reviewed captures: Alliance 217 actions; Horde 201. Both remain internally valid with zero loop reorders. The host estimates remain Alliance distance 617,955.14, log peak 12, reward-only XP shortfall 2,867,410, 62 uncertain travel legs; Horde distance 483,811.57, log peak 12, shortfall 2,855,010, 69 uncertain legs. Reward XP before objective work is 11,390,920 Alliance / 10,103,870 Horde. These are estimates, not proof of terrain safety or optimal beta routing.

The strict `audit_quest_flow.py --baseline` comparison cannot accept the earlier saved flow JSON because intervening changes in unrelated zones changed the whole-catalogue hash. The scoped audit values and complete guide stops/flow metrics were compared directly and are identical. No route optimization or engine change is proposed. Chapel roads, Tyr's Hand, Plaguewood, Scholomance/Naxxramas approaches, reputation-based live offers and item-use interactions remain native-player validation items.

## Validation

- Scoped `audit_quest_guides.py`: two faction guides, 102 zone records, 252 static source points; both flow states valid and gaps remain as listed.
- Scoped `audit_quest_flow.py`: full Horde 201-action and Alliance 217-action captures.
- Eastern Plaguelands focused coverage tests: 3 passed.
- Shared route regressions: 18 passed.
- No catalogue or Lua code changed; interface-16001/Lua 5.1 compilation was not rerun.

## Player checklist

Record build, addon commit, faction, level, class, party, chapter and confirmed hand-ins. Check fresh and mid-zone progress with Scan, reload, zone re-entry and chapter transition. Confirm the 5206 five Resonating Skulls final hand-in versus its 99 Fetid Skull preparation, and the 6022 seven Living Rot use step versus the Coagulated Rot final item. Verify actual Chapel object pickup and Ysida offer, separate 5513/5517 reputation conditions and 9121–9123 variant offers, and confirm the dungeon/road approaches on foot. Mark observed offer, item use and actual hand-in separately; accepting or completing objectives alone is not a hand-in.
