# Feralas quest-guide review, 10 October 2026

Refreshed on `guides/coverage` at `d0023c8` after main 0.8.65 (`cbd1e76`).
The source inventory contains 78 directly listed Feralas quests; the shipped
catalogue currently tags 23 records directly to Feralas and compiles both full
41–50 faction chapters. The current inventory, pinned facts and source hashes
are retained in this folder. The 24 selected QuestieDB files match
`tools/forever_source_manifest.json` at revision
e0a6eaa86f181ac99262e34126bcd2ed1a1712d6.

## Changes

Nine quests explicitly supply a required delivery item on acceptance:
2941, 2943, 2972, 2976, 3121, 3122, 3841, 3843 and 4267. Their item IDs and
counts remain hand-in requirements, but no separate farm objective is shown.
Their existing givers, receivers, quest gates and faction/class/race eligibility
are preserved.

Quest 2942, The Morrow Stone, requires both A Sparkling Stone (9307) and Stave
of Equinex (9306). Quest 2879 is its existing prerequisite and rewards 9307;
9306 is supplied when 2942 is accepted. Both remain required for the Troyas
handoff. The false farm stage is removed, and the mapped objective tells the
player to speak to Troyas. This does not add a prerequisite or farming location.

Quest 3842 still requires two Elixirs of Fortitude (item 3825). The Forever
quest page calls them Elixir of Lesser Fortitude, while the pinned item name is
Elixir of Fortitude. The item source is described broadly as craftable/lootable;
no single Feralas acquisition area is supported. Keep its objective location
unknown and verify the exact native item name and accepted completion count in
beta. Quest 7732's both-parent requirement (7730 and 7731) and supplied report
remain unchanged.

## Coverage and route comparison

The exact before/after audits and full flows are saved here. Both factions retain
the complete chapter action set: Horde 112 and Alliance 127 actions, with 60
static points checked. Pickup and hand-in location gaps are zero in the scoped
audit. Objective-location quest IDs fall from 11 to one: Alliance 2941, 2942,
2943, 2972, 3841, 3842, 3843 and 4267; Horde 2976, 3121 and 3122 are closed;
only 3842 remains. There are no unverified pickup requirements or objective
quantities in this scoped audit.

The separate 78-entry category coverage report rises from 67 to 77 records with
all required locations; all 78 pickup and turn-in records remain. Its one
remaining incomplete entry is 3842. The audit's 23 zone-tagged catalogue records
and the broader category count measure different scopes.

Full-route repricing preserves all actions and endpoints. It reports estimated
distance improving 223,239 → 147,011 for Horde and 296,914 → 238,336 for
Alliance, and uncertain travel legs falling 18 → 15 and 22 → 19 respectively.
Alliance has no delayed work rewards. In Horde, work rewards are delayed before
six or seven quests across the four replay starts; difficulty pressure also
regresses by one point at level 45 with zero XP. The guard therefore remains
**REVIEW REQUIRED**. No shared optimizer or route engine code was changed.
These estimates use the repository's host geometry and do not certify terrain
walkability or native route behavior.

## Validation

- Feralas scoped audit: 2 full guides, 60 source points; all route/data invariants pass.
- Feralas scoped flow: Horde 112 and Alliance 127 actions.
- Feralas focused regressions: 5/5 pass.
- Existing shared zone-audit regressions: 8/8 pass.
- Route/session regressions: 18/18 pass.
- Lua 5.1 packed-catalogue loading and data fingerprint checks: 10/10 pass.
- Full catalogue audit: all 152 guides and 11,839 source points checked.
- Native WoW beta behavior has not been tested.

## Player checklist

Record addon commit, client build, faction/race/class, level, chapter, party and
class-quest setting. Mark each item Pass / Fail / Skip and attach the actual
native offer and hand-in observation.

1. Fresh and mid-route characters, both factions: check the full 41–50 chapter,
   Scan guide, reload, pause/resume, zone entry and automatic progress. Confirm
   every required action remains and that completion does not trigger on a
   deferred or accepted-but-unfinished quest.
2. Verify 2941/2943/2972/2976/3121/3122/3841/3843/4267 arrive with their required
   item, retain it through objectives, and require the real hand-in. Confirm no
   guide step sends the player to farm those supplied items.
3. Complete 2879, accept 2942 and confirm it requires both items 9307 and 9306;
   verify the instruction points to Troyas and the actual hand-in gates completion.
4. For 3842, record the exact item name shown by the Forever client, whether two
   are required, and the actual supply sources available to a level-appropriate
   character. Do not assume a Feralas mob drop.
5. Verify 7732 remains unavailable until both 7730 and 7731 are handed in, and
   confirm its provided report remains required at turn-in.
6. Check optional class quests, elite/group warnings, Feathermoon Harbor access
   and the Alliance boat from the Forgotten Coast. Record boarding, landing and
   dock approach; host travel edges are estimates, not beta observations.
