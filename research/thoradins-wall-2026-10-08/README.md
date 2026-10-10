# Thoradin's Wall review, 8 October 2026

Refreshed baseline: guides/coverage aa24964ec55f97e7dface1725abb55fe79ba6668,
including main 09155ca265278572649a3529b8ce7ea1b4eb8431 / addon 0.8.61.
The supplied zero missing-stage/quantity/pickup-condition inventory still matches.
This narrow category has one direct quest, 79976; its actual compiled scope adds
79974/79975 prerequisites. Both factions retain all **nine actions** in 31–40.

## Supported handoff and frame corrections

The chain is Wet Job: Stonetalon Mound of Dirt → Loch Modan Carved Figurine;
Eagle's Fist: Figurine → Arathi Messenger Bag; This Must Be The Place:
Messenger Bag → Hastily Rolled-Up Satchel. Actual preceding hand-ins remain
required. No new item count, farming objective, kill or repeatable is invented.

Two records, 79975/79976, reconcile rounded positions with the published
beta-observation object facts:

| Object | Published frame and selected actual point |
| --- | --- |
| Carved Figurine 424007 | Area 38, map 1432 (Loch Modan), 49.42 / 12.78; aligns the next pickup with the existing prior return |
| Messenger Bag 406918 | Area 45, map 1417 (Arathi Highlands), 22.48 / 24.23; shared return/pickup |
| Hastily Rolled-Up Satchel 424006 | Area 45, map 1417, 22.47 / 24.23 |

Arathi is explicitly supported; these Wall objects must not be reinterpreted in
Hillsbrad map 1424. The subarea/category 293 has no independent native map frame
in the selected source. Retain the actual parent-map coordinates and saved guide
key. Carved Figurine's three observed positions are retained as evidence; they
are not a patrol. Existing Wet Job starts/return and all published item/work facts
are untouched. Destination object identity and interaction action produce the
original short “Interact with Hastily Rolled-Up Satchel” work instruction.

All **24 pinned source hashes** were verified at QuestieDB revision
e0a6eaa86f181ac99262e34126bcd2ed1a1712d6. Quest/object trace relations, source
tiers, exact point joins and before/after records accompany the review. These
are public factual fields, not imported provider/routing code or quest prose.
The primary source's beta observations distinguish this from assumptions about
similarly numbered quests in other editions. Existing faction/race/class facts
are retained; missing trace masks cannot create a blanket class restriction.
Further denied-source captures remain stopped; available pinned and catalogue
facts are used without retries or access bypass. No native current-build claim.

## Standalone category versus regional support

The category's single local quest does not establish a substantial recommended
leveling region. Its nine-stage route crosses Stonetalon, Loch Modan and Arathi;
minimum level 14 and quest level 32 remain distinct from the 31–40 chapter label.
The initial host capture prices the route from level 14 and reports difficulty
pressure 45. This is another reason not to interpret its nominal minimum as a
recommendation to make that journey at level 14.

The recommended review direction is optional chain/handoff support in Arathi
for a player who has reached this part of the story. **Not applied:** suppressing
or recategorizing the standalone guide would change saved keys, running progress
and automatic regional scope. Main must coordinate presentation/migration and
avoid automatically forcing the distant prerequisites into an ordinary Arathi
visit. support-proposal.json records the concrete proposal and preservation
requirements. No shared routing, eligibility, lifecycle or UI edits were authored.

No explicit child of 79976 is present in the available catalogue dependency
relations or the Satchel's published quest starts. That is not proof that the
live beta has no further continuation; leave it unknown until evidenced. The
real linked handoffs and preceding hand-ins are preserved without claiming a
complete wall/terrain inventory. No unsupported low-level exception is added.

## Validation and limitations

The scoped audit compiles both factions and checks the Wall record's two source
points; zero recorded gaps remain zero. Whole-chain same-facts comparisons cover
eight starting states. Every action and both endpoints survive, with unchanged
estimated distance 30,000.9, log peak 1, quest XP 7,050, reward XP before work
7,650 and two uncertain travel legs. XP shortfall and rewards before work do
not regress. Strict guard PASS;
precision/source improvements are not claimed as routing gains or walkability.

Five focused tests pass: shared object/frame consistency, exact hand-in unlocks,
concise interaction/no fabricated count, six faction/class variants and saved
mid-zone order, plus atomic conflict rejection/idempotence. The 122 selected
transport/class/offer/session checks pass. All 86 TOC Lua files compile in Lua
5.1/interface 16001; entity data, world checks and XP baseline are unchanged.
Additional zone/global results are recorded in review.json. The previous full
combined baseline passed 1,562/1,563 with the historical catalogue fingerprint
failure; targeted validation is used for this focused change, not a new full-run
claim. Host checks cannot establish native beta offers, terrain or persistence APIs.

## Player checklist

Record addon commit, beta build, faction/race/class, level, party and class setting;
mark Pass / Fail / Skip with actual offer/object and completion observations.

1. Fresh and mid-chain, both factions: verify Mound → Figurine → Messenger Bag
   → Satchel. The preceding hand-in must unlock the next pickup; acceptance or
   ready-to-turn-in alone must not do so. Record absent objects or conditions.
2. Check Carved Figurine in Loch Modan and Bag/Satchel in the **Arathi** frame;
   record actual positions, interactability and true hand-in. Native completion,
   not proximity or an invented item count, must control completion.
3. Record safe cross-continent arrivals and real wall/ground access. Do not treat
   a map line as a road or flight-master proximity as a personally unlocked route.
   Minimum 14 does not by itself establish suitable leveling here.
4. Check ordinary availability across applicable classes/races and Include class
   quests on/off; do not infer a class gate from another edition's memory.
5. Scan guide, pause/resume, reload and re-entry must retain fixed order and the
   saved Wall guide. Missing offers remain temporary deferrals that can return
   after confirmation; manual skips stay personal and unfinished work cannot
   cause false Guide complete. Record any actual onward continuation by ID.
6. After a coordinated support presentation exists, verify that existing saved
   Wall progress survives and an ordinary Arathi visit does not force the distant
   chain unless the player chooses it or reaches its supported handoff.

The regenerated global audit checks 152 sections / 11,833 source points;
33 sections remain recorded gap-free and the ordinary queue remains 390.
Both narrow Wall chapters are recorded gap-free under the audit's source fields,
which still does not certify native offers, complete regional coverage or terrain.
Only Wall and Stonewrought Dam rows change (two factions each); all retain their
9/6 respective action counts. Exact changed rows are in global-audit-changes.json.

Final combined zone regression run passes **69/69** tests in 98.193 seconds.
The separate selected behavior run passes **122/122**. Exact logs are retained;
no new full-suite or native-beta completion claim is made.
