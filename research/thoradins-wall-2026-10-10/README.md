# Thoradin's Wall refresh, 10 October 2026

Refreshed on `guides/coverage`, based on main
`cbd1e7608dc32c2080d8b1d967fb577c10084053` (addon 0.8.65). Previous source
evidence, object-frame corrections, continuation facts and the concrete
presentation proposal remain in
[`../thoradins-wall-2026-10-08/README.md`](../thoradins-wall-2026-10-08/README.md).
No newer source capture or native-beta observation in the worktree supports a
quest-data change.

## Refreshed scope and evidence

The current scoped audit compiles both factions of the 31–40 chapter: one direct
Wall quest (79976) plus the two prerequisite quests (79974/79975), with all nine
actions per faction and two source points checked. Pickup, objective and hand-in
location gaps remain 0/0/0; no pickup requirement or objective quantity is
recorded unknown. The map evidence continues to place the Carved Figurine in
Loch Modan (map 1432) and the Messenger Bag and Hastily Rolled-Up Satchel in
Arathi Highlands (map 1417), not Hillsbrad. The guide chain still requires the
preceding actual hand-ins.

All complete host flow states remain valid. Horde and Alliance each have the
same current estimates: distance 30,000.9; log peak 1; XP shortfall 0; 7,050
quest XP; 7,650 reward XP available before work; two uncertain travel legs; no
blocked legs. These model estimates do not establish a walkable road, personal
flight access or beta behavior. The same-facts replay from the prior review
preserved all nine actions and both endpoints across eight starting states
with unchanged metrics. It is preservation, not an optimization gain.

The source baseline supplied with the prompt records zero gaps, and this
refresh still records zero. No new fact was added. The 8 October review's
source URLs, verified pinned file hashes, exact object points, and trace joins
remain the evidence package.

## Standalone category or regional support

The guide should not be presented as a recommended leveling region on the
available evidence. It contains one direct quest, while its nine actions run
from Stonetalon through Loch Modan to Arathi. The level-14 minimum, level-32
quest and 31–40 chapter label are different facts; none demonstrates that a
player should travel there at level 14.

The data supports an optional chain/handoff in Arathi after a player reaches
that story point. The existing proposal remains unapplied because recategorizing
or suppressing the standalone guide affects shared presentation, saved keys and
running progress. Main-developer coordination is required before such a change;
preserve existing Wall progress and do not make ordinary Arathi players travel
to Stonetalon and Loch Modan automatically. No shared runtime or UI code changed
in this refresh.

No later child of 79976 is established by the available quest relations or
published Satchel starts. Safe cross-continent arrival and on-foot approaches
to the Wall objects remain unknown. Keep those claims explicit.

## Validation and player checklist

- Thoradin focused regressions: 5/5 passed.
- Scoped audit: two guides and two source points. Full-flow capture: both
  complete faction sequences valid.
- Lua 5.1 host load: all 87 TOC Lua files passed; interface remains 16001. No
  Lua source changed in this refresh.
- Native Forever beta behavior remains untested.

Player checklist: both factions, fresh and mid-chain; confirm Mound → Figurine
→ Messenger Bag → Satchel with each real prerequisite hand-in completed; check
the Figurine in map 1432 and Bag/Satchel in Arathi map 1417; record actual
arrival, object position, interactability and safe approach; test suitable
class/race variants, class-quest setting, Scan, pause/resume, reload and re-entry;
record any further quest ID offered after 79976. Confirm existing saved Wall
progress survives any future presentation change, and that normal Arathi work
does not force this distant chain. Keep offer deferrals temporary and manual
skips personal; unfinished work must not mark the guide complete.
