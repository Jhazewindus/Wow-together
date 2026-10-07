# Destination reasons

The guide window, standalone arrow and quest-list tooltips share one reason
engine. It explains the selected plan without accepting, skipping, reordering or
completing quests. A reason is not a new eligibility check or a guarantee of
optimal XP per minute.

## What the player sees

- A prerequisite names the useful follow-up. Lower-level exceptions explain
  the later quest or dungeon preparation that makes them worth considering.
- Consecutive eligible pickups within 100 yards explain the grouped visit.
  Consecutive nearby returns explain collecting rewards together.
- Nearby accepted, unfinished kill/gather work explains advancing several
  quests in the same area. Item-use, dialogue and other phases remain separate.
- A return names its quest reward. A dungeon pickup explains collecting it
  before entering the dungeon. Training and profession trips retain their
  skill-cap, recipe or optional-training purpose.
- A normal pickup without a special benefit states its quest level and role in
  the selected guide. At 1,000 yards or across maps, it also says that no special
  unlock is known and that the player can skip the detour.
- Unverified pickup requirements name the NPC to check. Missing coordinates
  remain missing; an explanation never invents a destination.

The standalone-only layout shows the reason beneath its arrow. The main guide
window makes room for wrapped explanations, up to 110 pixels; the complete text
remains in the tooltip. Optional advice appears below the standalone reason,
and disappears independently when dismissed. Previewing another guide uses that
guide's records rather than the active guide's dependencies.

## Evidence and limits

`GuideReasons.lua` returns a structured decision: code, explanation, related
quest IDs, whether a specific benefit is known, a review flag and any caution.
The diagnostics report these fields for the current step; routine player screens
show only the explanation.

Published direct and AND prerequisites can establish a required continuation in
the selected guide. Completed, already accepted, explicitly skipped, disabled
class and incompatible follow-ups do not supply that benefit. A chosen dungeon
OR branch is described as one choice, with alternatives acknowledged. An
unverified branch cannot be described as mandatory. Existing locally learned
relations obey their build/faction and restricted-class/race rules; turning off
observed learning removes that reason. Observer names stay out of routine UI.

Useful low-level exceptions use the existing value policy, including its bounded
chain search. That policy can find an alternative path into a worthwhile chain;
its benefit does not prove that the current quest is the only possible unlock.
No source fact changes, prerequisite guesses or rule promotions are made by this
update.

Pickup grouping requires the existing pickup rules to allow the quest. A missing
NPC offer rejects it; an unknown offer does not become a confirmed offer. The
engine respects explicit skips and uninterrupted phases. It describes existing
clustering, and does not move objectives or hand-ins to create a claim.

Travel checks retain their separate connection/unlock rules and estimated
walking/flight costs. Nearer flight-master checks say why they may save time;
opening the flight map is still needed to confirm a connection. A quest reason
does not certify roads, mountain crossings, guard safety, flight access or an
exclusive trainer. Reward values and resulting levels are not fabricated.

Reasons cache the current guide, route and character/progress revisions. The
ordinary arrow refresh reuses the decision; changed progress, identity, guide,
route or learning settings invalidates it. It never performs HTTP requests.

## Catalogue-wide audit

Run:

```sh
/workspace/.wow-together-tests/bin/python tools/audit_quest_guides.py
```

`WowTogether/GuideAudit.json` records explanation coverage for all 5,230 quest
records, each published pickup/objective/return point and explicit missing-stage
fallbacks. It also records reason codes and review counts for all 152 compiled
faction/level-section guides, while retaining prerequisite order, escort
adjacency, excluded-quest and estimated-distance checks.

A nonempty explanation is not the same as complete mapping or useful detour
evidence. `reason_review_quest_ids` includes generic guide-only benefits and
uncertain source facts. Existing source-data gaps remain separately reported;
32 of the 152 audited guides are currently free of the audited source gaps.
Native beta behavior, fonts and rendering require in-game checks in TESTING.md.
