# Main 0.8.61 integration — 8 October 2026

Main advanced to `09155ca` after the Dun Morogh follow-up was pushed. It adds
session checkpoints, pause/resume and dungeon-player tracking. Merge `0467646`
inherits those changes while preserving every guide commit and reviewed fact.
Only evidence-document overlap and an older test's boar coordinates required
resolution: retain the supported 73.8,52.6 assertion and its count/gap checks.
No shared runtime change, version bump or release publication was authored by
the guide agent. The main developer's release history remains intact.

The packed catalogue is unchanged. Fresh 0.8.61 standard/dwarf captures preserve
151/30 actions and all endpoints. Sixteen replay states remain valid; metrics,
source gaps and strict optimization guard results match the parent review.
No additional location, source, unlock or terrain fact is established by the
new session UI. The retained tester gate and Winter Wolf veto/unfinished-work
rules remain the data agent's acceptance criteria.

All 92 focused tests pass, including Dun Morogh facts, Winter Wolf rules, source
coverage, offers/progress and main's new session/dungeon tests. All 86 TOC Lua
files compile under Lua 5.1/interface 16001. The full suite passes 1,529 of 1,530 tests; its sole failure is the known historical
catalogue fingerprint assertion, with fixture unchanged. The global audit passes
all 152 sections and 11,823 source points and is identical to the generated audit.
Exact results are recorded in `review.json`; host checks still cannot establish
native beta behavior. Existing routing and later Wetlands handoff decisions remain
with the main developer.

Run the [parent player checklist](../README.md#player-checklist), and additionally:

1. Pause Dun Morogh mid-quest, reload/login, and explicitly Resume. Keep the fixed
   order, actual completion gates, accepted unfinished work and personal skips.
   Offline XP/turn-ins must not be reported as observed session activity.
2. At the resumed NPC visit, confirm offers still distinguish temporary absences
   from manual skips. A saved checkpoint must not imply quest completion or
   restore unrelated/completed Winter Wolf markers.
3. Check Stop versus Pause/Exit, chapter transitions and the next useful handoff.
   Record client build, character context and actual beta rendering/event order.
