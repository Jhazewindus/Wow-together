# Standing instructions: how a guide step must read

Paste into the Codex project prompt next to CODEX_CLASS_QUESTS.md. Applies
to `GuideText.lua`, `GuideReasons.lua`, `Navigation.lua`, `UI.lua`,
`LevelingGuides.lua`, `QuestFlow.lua` and anything that produces a stop.

## The test for every step

A player who has never seen the addon reads the step card once and can
answer four questions without opening a browser:

1. **What do I do?** One verb, one object, one place. "Read the Manual
   (ground object) to start Defensive Magics 101", not "Accept from Manual".
2. **Where?** Zone + coordinates + distance/time, already shown; keep it.
3. **Why is this in my guide?** What it unlocks or finishes, in one line,
   derived from data: "One of 40 books that unlock Research Access (mage);
   this is the nearest for you." Never a status sentence.
4. **Is it required now?** One of: required for the chain you are on;
   optional, on the way; optional, later; or skip. The card must never
   route the player to a step and call it skippable in the same breath.

If the step text cannot answer 3, the step is not ready to show. A step
whose reason has `specificBenefit = false` ("outside-level-range",
"level-work", "selected-guide", "guide-status") must not be the current
step unless the player chose Continue anyway; it is collapsed under
"Later" with its level.

## Where the "why" comes from (data, not prose)

Every reason is computed in `GuideReasons.lua` `explain()` and carries a
machine code. Codex must extend the code table, not write free text in the
UI. Sources of a "why", in priority order:

1. Continuation: this quest is a prerequisite of a later guide quest
   (`previousQuest`, `prerequisiteAll`, learned prerequisites, or the
   chosen member of a `prerequisiteAny` group). Say which quest and, for
   any-of groups, how many options exist (`guide.collectionAlternatives`).
2. Flow: reward-first, early-reward, log-space, objective-area grouping.
3. Hub visits: pickups/hand-ins grouped at one NPC.
4. Class progression / dungeon pickup / confirmation / training.
5. Only then: level work, and only as a collapsed "Later" item.

Any-of prerequisite groups are **one step**: `addPrerequisites` chooses the
nearest eligible option (an accepted one first, then distance, then level,
then ID) and records it in `collectionDependencies`; the others are never
routed. "Skip quest" on the chosen one must make the next build pick
another option, so the skip is recorded against the option, not the group.

## Wording rules

- Verb first, in the imperative: Accept, Turn in, Kill, Collect, Read,
  Use, Speak to, Fly, Use your Hearthstone.
- Name the thing the player will see on screen: the NPC's name, the
  object's name with "(ground object)", the item's name. Never an internal
  label ("Manual" alone is the object's display name; say what it is).
- Numbers before nouns: "Kill 8 Laughing Sisters", "Collect 12 hairs".
- One idea per line. Line 1 = what, line 2 = why, line 3 = status/travel.
- No hedges in the step card ("may", "possibly", "under review"). Hedged
  facts go to `/wt probe` and the tooltip's second section.
- No meta-language about the addon ("this saved or previewed step", "the
  selected guide", "Dijkstra"). The player does not know what those are.
- Reason sentences end with what to do about it when optional: "Skip quest
  hides it" / "Skip step keeps the quest for later".

## Worked example (the card from 2026-11-08)

Before:
```
Defensive Magics 101
Accept from Manual
212 yd • ~0m 30s travel
Outside your useful leveling range; this saved or previewed step can be skipped.
```
After (same data, no new strings typed by hand):
```
Defensive Magics 101
Read the Manual (ground object) to start Defensive Magics 101
One of 40 books that unlock Research Access; this is the nearest for you.
Optional • on your way • 212 yd, ~30 s
```
What produced it: `entityType = "object"` → "Read the … (ground object)";
`prerequisiteAny` membership → chosen-branch reason with count;
`specificBenefit = true` → shown as current step; distance line unchanged.

## When a tester says "why am I doing this?"

Start from `/wt probe`: "Destination reason: <code>; <sentence>" and
"Reason evidence". If the code is one of the non-specific ones and the step
was current, that is the bug. If the code is wrong for the data, fix
`explain()`. If the data lacks the link that would have explained it
(missing prerequisite, missing `nextInChain`), fix the data and add a
catalogue test with the quest IDs.

## Data question raised by this card (open)

All 40 research books end at Garion Wendell, placed in Stormwind's Wizard's
Sanctum, yet "Research Access" is `side = Both`. A Horde mage cannot turn
in there. Either Forever has a Horde-side NPC (then the catalogue needs a
second `ends` entry and faction-aware selection), or the quest is Alliance
only (then `side` is wrong). Confirm in game with a Horde mage before
routing any Horde character to a research book.
