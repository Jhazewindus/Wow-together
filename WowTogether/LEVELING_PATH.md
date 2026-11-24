# Leveling path (0.8.113)

`LevelingPath.lua` answers "where do I go next": the zones to quest in from
the character's level to 60, in order, with the level each should leave the
character at. It is shown in three places:

- **Under the guide window**, also in Glance: one line with the level this
  zone takes the character to, the zone after it and experience per hour.
  Hover for the next zones, click for the whole path. *Show the leveling
  path under the guide window* turns it off.
- **At the top of the main window's first page**, in both layouts (above
  "Next for you" on the new Hub's Play page): the next four zones with their
  level ranges and quest counts. Clicking a zone starts its guide; *Whole
  path* opens the full list and *Follow path* chains the zones.
- **`/wt path`** prints the next eight zones in chat.

A guide being followed is matched to its zone on the path by map, home map
or zone name.

## Following the path

*Follow path* (the button on the main window's path block, or
`/wt path follow`) turns the path into one continuous guide: zone guides are
chained. When the guide for a zone reaches its zone-exit step, or its route
completes, the guide for the path's next zone starts by itself, a few
seconds later and outside combat, with a chat line saying so. The first
start is by hand and may ask about current quests; hand-overs never open a
prompt. `/wt path stop` or *Stop path* ends it; the running guide carries on.

It only acts at a hand-over. Stopping a guide by hand pauses the chain, a
profession or dungeon guide is left alone, and a "gain more XP here first"
step is not a hand-over. The same zone is never started twice within two
minutes, and after three hand-overs in ten minutes following is switched
off with a message, so a data problem cannot send the player hopping.

A zone is also left when its guide has no step left that the player can
take: everything remaining is skipped, blocked by a quest they are not doing,
or set aside. The path then stops offering that zone until the character has
gained a level, since it counts quests the guide cannot route. A quest counts
as not being done once any step of it has been skipped. Elite and raid quests
are set aside by the guide while the player is not in a group (a setting
includes them).

## Finish first

A zone is not left with work already done lying in the quest log:

- **Finished quests are turned in first.** The route already kept a ready
  turn-in of the guide's own quests; the hand-over now also waits for any
  finished quest of the zone in the log, whether or not the guide lists it.
- **Nearly finished quests are finished.** A quest in the log whose
  objectives are on average 85% complete (a setting: 85%, 70% or off) counts
  as worth doing whatever experience it pays now, so the route keeps it and
  the zone is not called done. `ns.QuestProgressFraction` is the average of
  the objectives, each counted as have/need.

While following the path, the hand-over is held and one chat line says what
is left ("before leaving Hillsbrad Foothills, turn in ... and finish ...
(90%)"), repeated only when that changes. A quest belongs to the zone when
the guide lists it or one of its turn-in, objective or pickup points is on
the guide's map. The guide can only draw the arrow to quests it lists; for
any other the chat line names it and the player finds the way.

Every "next zone" answer comes from one place (`ns.NextLevelingGuide`): the
path when it is known, else the lowest zone above the guide's band.

## How the path is worked out

Every zone's quests for the character come from the catalogue, the same ones
the zone guides use, minus repeatable, dungeon, group, profession and
excluded quests. Starting from the character's level and experience the
planner repeatedly:

1. counts what each zone offers now: quests not finished or skipped, no more
   than two levels above the character, and worth at least 30% of a typical
   quest reward at that level;
2. picks the zone with the most experience on offer, preferring the continent
   the character is on (x1.4, from the very first step). The guide being
   followed comes first, then the zone the character stands in when it has
   four quests on offer or any of its quests already in the log. For the
   first step each quest already in the log adds 25% to its zone (up to
   four), because part of that work is done. A zone needs eight quests on offer; four,
   then one, are accepted only when no zone has more;
3. "does" that zone's quests in level order, levelling up along the
   experience curve, and takes any that open as the level rises.

A repeat visit straight after is merged. The result is a list of zones with
start and end levels, to 60 or until the known quests run out.

## Kill experience

Quest rewards are not all the experience there is. In this catalogue they
cover roughly 89% of what levels 21-30 need, 70% of 31-40 and 66% of 41-50
for a Horde character, so the rest comes from kills. The guide measures the
character's own ratio (total experience gained against experience from quest
rewards, in the character's saved data) and scales quest rewards by it.
Before any play is seen it assumes x1.8; that assumption fades linearly over
the first thirty quests turned in, after which the figure is all measured.
It is clamped between 1 and 2.5 and old play is halved in weight after 150
quests. The path text says which of the two is in use.

Pace is experience per hour over the last half hour of play, with the time
to the next level.

## Cost

The path is worked out in the background, a little on each frame, and must
never be felt:

- **Each frame gets at most 1.5 ms of it**, decided by the clock
  (`debugprofilestop`), not by counting items. The first version sliced by
  count: slices that took 4 ms in the test host took tens of milliseconds in
  the game, seventy frames in a row, on every recalculation. That was a
  visible stutter (a profile showed 271 frames over 50 ms in three minutes).
- **Only the next twelve zones are worked out routinely.** The whole path to
  60 is calculated when its window is opened (`ns.LevelingPathWhole`).
- **A path that exists is redone at most every 30 seconds**, however many
  quests are accepted or turned in meanwhile; what is on screen may be that
  much out of date. A caller that waits for the answer (the chat command, a
  hand-over) always gets a fresh one.
- **Quest state is read once per calculation**, not once per zone per step,
  and a recalculation that leaves the first two zones and the level target
  unchanged redraws nothing.

With *Leveling path* off in settings, nothing is calculated. `/wt perf` reports the background work as `path`.

The path has its own setting (*Leveling path*) and does not depend on the
experimental XP model (*let quest XP decide which quests to skip*). That
model is off by default: switched on, it filed quests worth doing as low
value and could leave a guide with no steps. Its cost per refresh was fixed
(`ns.NextZoneBaselineGuide` is worked out once, not twice per refresh), but
its judgement was not, so it stays optional.

Without the model a zone guide has no "zone finished" step, so when the path
is followed a zone is left when it was the path's first zone and no longer
is: nothing in it is still worth the character's level. A zone the player
chose against the path is never left on the path's say-so.

## Limits

- Quest experience for quests far below the character uses Classic's table
  (full to five levels below, then 20% less per level) unless the XP model
  has observed rewards. Forever's own table has not been published.
- The planner does not know travel time between zones beyond preferring the
  same continent.
- Dungeons are not part of the path. When the known quests run out before
  60 the path says at what level.
