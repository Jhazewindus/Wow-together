# Durotar follow-up review — 8 October 2026, 0.8.60

The repeated zone assignment continues the existing guide history. Main
`eec9b99` was merged cleanly before this review; the baseline branch is the
Dun Morogh commit `2aa164c`. The earlier six Durotar corrections remain intact.
This follow-up changes research and coordination documentation only.

## Refreshed evidence and scope

All 24 pinned QuestieDB files and 103 previously captured quest pages passed
SHA-256 verification. Fifteen priority/handoff pages and the current 65-entry
Durotar category list were freshly captured. Adjacent files retain URLs, dates,
hashes and selected factual fields, without downloaded code execution or copied
guide prose. The pinned source's field tiers distinguish converted-baseline
facts from beta corrections; highest source priority does not make an old
baseline fact a live beta observation.

The compiled inventory still contains 103 distinct IDs and **246/85 Horde
and 13/10 Alliance-template actions** across the two existing chapters. The
Alliance templates do not recommend Durotar to Alliance characters. The category
list has eight entries outside that compiled inventory: two repeatables, four
placeholders, edition-only Welcome!, and the remote-work handoff described below.
Class branches and related outside-zone dependencies explain why the compiled
inventory is larger than the category list.

Pinned facts support Cutting Teeth 788 → Sting of the Scorpid 789, the
alternative Vile Familiars 792/1499 → Burning Blade Medallion 794 gates and
Cutting Teeth → Galgar 4402. Keep **actual predecessor hand-ins**, not acceptance
or objective completion. Fresh pages preserve ten boars, ten tails, twelve
familiars for 792, ten cactus apples and five peons with the supplied Blackjack.
The importer sees ambiguous page-series suggestions for 788/792; they do not
override the reviewed gates or add a universal class prerequisite. Existing
class parchments, class-setting behavior, supplied-item deliveries, pouch drop
and escort instruction remain unchanged.

The New Horde 787 retains the pinned Horde mask, actual-offer confirmation and
unverified extra availability. Fresh page data supplies no new explicit parent
or race restriction. Comment 6436200 repeats an absent-offer report on Orc,
Troll and Tauren without enough completion/build context. It does not justify
an Orc/Troll exclusion. The other current comments match the earlier same-day
review: residue acquisition/enchanting leads and a guessed blacksmithing gate
still lack the facts needed to close their acquisition locations.

Missing pickup/objective/hand-in IDs remain **1/4/1**, with **16 unverified
pickup requirements**. The original queue's nine objective gaps were already
reduced to four by the prior Durotar commit. No new gap is closed here. Keep
785's unknown stages, 96873/96874's missing material sources and 99123's unknown
escort endpoint/path visible. Previous same-day forum/reference findings and
recorded access denials remain applicable; no denial was bypassed.

## Shared eligibility conflict: Vile Familiars 792

The pinned source has `requiredClasses=1247`, excluding the Warlock bit 256.
Its source tier is **converted-baseline**, while the fresh Forever page has
`reqclass=0`. The current catalogue retains `classMask=0` for this ordinary
quest and a separate Warlock quest 1499. This is a source conflict requiring
current-beta confirmation, not evidence to silently merge the same-title IDs.

A host probe also demonstrates a shared behavior conflict: with Include class
quests off, ordinary 792 is enabled today; assigning mask 1247 disables it because
`Planner.lua:IsClassQuest` treats every positive class mask as a class quest.
The probe in `eligibility-conflict.json` changes only an ephemeral host object.
No shipped fact or engine module is edited. Native eligibility was not tested.

Main-developer coordination must settle current beta availability and the
distinction between ordinary-quest eligibility and class-quest classification
before importing this mask. Preserve the user's class setting and both branches.

## Useful handoff outside the compiled scope

**Need for a Cure 812** is level 9/min 7 and starts/ends at Rhinag in Durotar.
Its required Venomtail Antidote 4904 is associated with Kor'ghan in Orgrimmar;
the fresh **Finding the Antidote 813** page explicitly rewards one antidote for
four Venomtail Poison Sacs. Existing 813 is repeatable and grants no quest XP.
Flawed Power Stone 926 is also repeatable. Preserve these exclusions and facts.

The shared `LevelingGuides.lua:localWork` criterion omits 812 from Durotar because
its mapped work is entirely in Orgrimmar. This is a real pickup/handoff coverage
limitation outside the 354-action audit scope, not proof of full-zone completion.
The friendly NPC's existing loot-style point also does not prove a drop relation;
the explicit quest reward is the useful acquisition fact. Do not tell a player
to kill or loot Kor'ghan. Coordinate a supported acquisition/handoff instruction
and inclusion policy before changing the shared compiler or adding a repeatable
quest to ordinary leveling. No synthetic prerequisite, fake local point or
blanket repeatable inclusion was introduced here.

## Full-route validation

Both baseline and candidate captures use the same current runtime. The baseline
uses our pre-correction catalogue at `e61c267`; both complete orders are then
repriced with corrected facts. All 16 candidate states and baselines are valid,
and every action and onward endpoint survives. The earlier guarded tradeoffs
remain: early Horde travel falls 264,651.87 → 263,498.05 with log peak 20 unchanged,
but 6067 receives 162 less reward XP before work. Later Horde travel falls
132,875.28 → 132,826.05, log peak 7 remains, and uncertain legs rise 14 → 15.
Some later work also receives rewards later. Alliance-template metrics remain
unchanged. Exact states and delayed stops are in `repriced-flow.json`.

The strict guard still requires review. These are default host estimates, not
terrain surveys, live flight unlocks or beta playtimes. Do not shorten the action
set or weaken the guard to label the route optimized. Shared routing, eligibility,
guide lifecycle and UI remain with the main developer.

The combined branch passed 1,492 of 1,493 full-suite checks before this
research-only follow-up; the sole failure is the known historical catalogue
fingerprint assertion. All 84 TOC Lua files compile under Lua 5.1/interface 16001.
The fresh scoped audit validates all four entries and 160 source points. Final
Durotar regressions and source checks are recorded in `review.json`.

## Player checklist

Run the [original full Durotar checklist](../README.md#player-checklist-for-the-main-developers-test-build)
through both applicable chapters. Record client build, addon revision, character
race/class/level, class setting and Pass/Fail/Skip separately.

1. Compare ordinary 792 and Warlock 1499 on matched non-Warlock/Warlock characters,
   with class quests both on and off. Record actual offers and prerequisite
   hand-ins; ordinary quests must retain the intended class-setting behavior.
2. Verify Rhinag 812's pickup and real antidote acquisition: accept the supported
   Kor'ghan work, collect four sacs, obtain the rewarded antidote and return to
   Rhinag. Record beta availability, repeatability and any hidden conditions.
3. Confirm the hand-in gates, supplied deliveries, pouch drop, escort adjacency,
   full action set, temporary deferrals, personal skips, Scan guide, reload and
   zone entry from the original checklist. Record all remaining missing facts.
4. Check cave approaches and the Orgrimmar handoff on the ground. Report reward
   timing/log pressure and blocked terrain; no straight marker line is certified.
