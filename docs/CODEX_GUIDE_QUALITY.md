# Codex operating manual: making Wow Together guides good

This is the standing prompt for every guide-related task. Read it whole once;
afterwards use the section headings as a checklist. It supersedes nothing in
CODEX_CLASS_QUESTS.md or CODEX_STEP_TEXT.md; it is the umbrella those two
hang from. REVIEW_0_8_90.md and HANDOFF_0_8_90.md describe the code; this
file describes the job.

---

## 0. The job in one paragraph

Wow Together's guides are generated from data, not written by hand. A guide
is good when a player who has never read a website can follow the card from
step to step without ever being sent somewhere pointless, without ever
wondering why, and without ever reading addon jargon. Your work is therefore
three things, in this order: make the data true, make the rules that turn
data into steps correct, make the words the rules emit plain. You do not
write guide prose by hand, you do not special-case quest IDs in code, and
you do not ship anything you have not run through the test suite.

---

## 1. How the system actually works (so you change the right layer)

```
sources (web pages, QuestieDB Forever, cmangos classic-db, Mapzeroth, in-game observations)
   │  data-tools/import_*.py, forever_beta_facts.py, legacy_quest_facts.py
   ▼
QuestCatalogue.json  +  quest_corrections.json  +  quest_exclusions.json
   │  data-tools/build_quest_dataset.py → pack_data.py
   ▼
WowTogether_QuestData/QuestCatalogue.lua        (5333 quests, packed, load-on-demand)
   │  Catalogue.lua: eligibility (CataloguePickupCheck), prerequisites, breadcrumbs, exclusives
   ▼
Guide builders: LevelingGuides.lua (zone + class), DungeonCollection.lua, FixedGuides.lua,
                QuestFlow.lua / FixedRouteOptimizer.lua / GuideOptimizer.lua (ordering)
   │  records → stops (Routes.lua RouteStop) → route
   ▼
GuideReasons.lua explain()  →  reason code + sentence per stop
GuideText.lua GuideStepAction/Hint/Facts  →  the verb line
Navigation.lua / UI.lua / StandaloneArrow.lua  →  the card the player sees
   │
   ▼
/wt probe  →  "Guide pickups", "Destination reason", "Reason evidence" (your debugging input)
```

Rule of thumb for where a fix goes:

| Symptom | Layer | File(s) |
|---|---|---|
| Sent to an NPC who does not offer the quest | data (missing link) or eligibility rule | quest_corrections.json → rebuild; Catalogue.lua |
| 40 steps where one would do | builder (group handling) | LevelingGuides.lua addPrerequisites |
| Step says "can be skipped" but is routed | reason/flow policy | GuideReasons.lua, GuidePolicy.lua |
| Wrong verb / internal label on the card | text | GuideText.lua |
| Card layout ugly / lines crammed | UI | Navigation.lua, StandaloneArrow.lua, UI.lua |
| Order is silly (city A → city B → city A) | optimizer | QuestFlow.lua, FixedRouteOptimizer.lua |
| Dungeon guide misses an entry quest | data (dungeon) | dungeon_fact_corrections.json, import_dungeons.py |

Never fix a data problem in Lua logic. Never fix a logic problem with a
correction entry. If you are unsure which it is, it is a data problem until
the data is proven right.

---

## 2. The quality bar for a step (what the player sees)

Every step card answers four questions without a browser:

1. **What** — one imperative verb, one object, one place.
2. **Where** — zone, coordinates, distance and time (already there; keep it).
3. **Why** — what it unlocks or finishes, derived from data, one line.
4. **Required now?** — required for the chain you are on / optional, on the
   way / optional, later / skip.

Layout of the card, top to bottom, fixed:

```
<Quest title>                                   [Pause] [BG] [ST] [x]
<Guide name • step N>                           (muted, small)
┌──────────────────────────────────────────────┐
│ ▲  <WHAT line>                                │   verb first, ≤ 70 chars
│    <WHY line>                                 │   from reason code, ≤ 110 chars
│    <STATUS line> • <distance>, <time>         │   Required / Optional on the way / Later
└──────────────────────────────────────────────┘
[‹] [Skip step] [Skip quest] [Scan guide] [›]
```

Hard rules for the three text lines:

- Verb first, imperative: Accept, Turn in, Kill, Collect, Read, Use, Speak
  to, Fly to, Use your Hearthstone. Numbers before nouns ("Kill 8 …").
- Name what the player sees on screen: NPC name, object name plus
  "(ground object)", item name. Never an internal field.
- No addon vocabulary on the card: never "saved or previewed step",
  "selected guide", "Dijkstra", "published", "snapshot", "revision",
  "beta". Those words belong in `/wt probe` and tooltips' second section.
- No hedges on the card: "may", "possibly", "under review", "unverified"
  go to the tooltip. If a fact is unverified, the step is not current.
- One idea per line. A line never contains two sentences.
- Optional steps end with the action that removes them: "Skip quest hides
  it" / "Skip step keeps it for later".
- Tooltips repeat nothing from the card; they add the evidence: source of
  the location, which quest this is a prerequisite of, the reason code.

The WHY line comes from `GuideReasons.lua` `explain()`; you extend its code
table, never the UI strings. Priority of reasons:

1. continuation (prerequisite of a later guide quest; for any-of groups,
   "One of N options that unlock X; this is the nearest for you.")
2. flow (reward-first, early-reward, quest-log-space, objective-area)
3. hub visit (pickup-hub, return-hub)
4. class-progression / dungeon-pickup / confirm-offer / class-training
5. level-work, selected-guide, outside-level-range — **never as the
   current step**; collapsed under "Later" with the level shown.

A reason with `specificBenefit = false` is a signal that the step has no
business being current. Treat a tester screenshot showing one as a bug in
the policy that let it through, not as a wording problem.

---

## 3. Correctness rules the builders must obey

### 3.1 Eligibility (all guides)
A quest is routable only if, in this order: class ok → race/faction ok →
level ok → prerequisites complete → not superseded (breadcrumb /
exclusive) → not retired, repeatable, complete, or in the log → NPC offer
evidence not negative. Each failure has a reason code in `/wt probe`. See
CODEX_CLASS_QUESTS.md §"The one rule" for the full list and the "upcoming
vs hidden" distinction.

### 3.2 Chains
Build a chain as a unit (root → steps → reward), route the chain the player
is in the middle of first, then the next chain by distance of its first
routable step, then by level. A chain the player cannot start shows as one
collapsed "Later" line.

### 3.3 Breadcrumbs
Errands ("Speak with X") are optional, disappear once their continuation is
accepted or done, and must never be recorded as prerequisites of the real
quest. Published `nextInChain` wins; class-errand inference is the
fallback (`Catalogue.lua CatalogueBreadcrumbTargets`). Importing
QuestieDB `nextQuestInChain` is the real fix and is the top data task.

### 3.4 Any-of groups
"Finish one of these N" is one step: nearest eligible, accepted one first,
none once any is done. Record the choice in `collectionDependencies`, the
count in `collectionAlternatives`. (`LevelingGuides.lua chooseAlternative`.)

### 3.5 Faction geography
A quest marked `side = Both` whose hand-in NPC stands in a faction capital
is not usable by the other faction until the data has that faction's NPC.
Add a faction-aware `ends` selection; until then such quests are "Later"
for the faction that cannot reach the NPC, with the reason "hand-in is in
<city>; confirm a <faction> hand-in exists". Open case: 40 mage research
books → Garion Wendell, Stormwind.

### 3.6 Level range
"Useful leveling range" is the band in which quests are green/yellow for
the lowest synced member. Grey quests are never routed in a leveling guide;
class quests, dungeon pre-quests and chain continuations may exceed the
band only with a specific-benefit reason. Do not route a level 35 pickup to
a level 26 character unless the reason names what it unlocks now.

### 3.7 Dungeon guides
A dungeon guide is: pre-quests (collected outside, in travel order) →
entrance → inside objectives in encounter order → hand-ins. Pre-quests
include attunement/entry quests, item-started quests whose item drops
inside, and chains whose final step is inside. A pre-quest that cannot be
obtained by this character (faction, level, missing prerequisite) is shown
as "Later", never routed, and the dungeon guide says what would be missed.

---

## 4. Research protocol: how to find facts online

You have a pipeline. Use it. Do not scrape ad hoc, do not paste facts from
memory, do not invent coordinates.

### 4.1 Source ranking (highest first; see 4.5 for adding sources)
1. **In-game observation** on the Forever client: a tester's NPC offer,
   `offerKnowledge`, recorded pickup positions, `/wt research` export.
   This beats every website.
2. **Wowhead Forever** quest/npc/object pages
   (`https://www.wowhead.com/forever/quest=<id>`): start/end, objectives,
   requirements, series, "Start"/"End" NPCs, item sources. Capture with
   `data-tools/capture_quest_pages.py`; the capture records URL, date and
   SHA-256 into provenance. Respect denials: a denied fetch is a stop
   signal for that run, not a retry loop.
3. **forever.warcraftdb.com** quest lists for existence, level, side.
4. **QuestieDB Forever corrections** (`foreverQuestFixes.lua` in the
   Questie repo): prerequisites (`preQuestSingle`, `preQuestGroup`),
   `exclusiveTo`, `nextQuestInChain`, `parentQuest`, `childQuests`.
   Import via `forever_beta_facts.py`; these are structured and reliable
   for chain topology.
5. **cmangos classic-db** for unchanged vanilla quests only
   (`foreverStatus` ≠ new/updated). `PrevQuestId`, `NextQuestId`,
   `ExclusiveGroup`, `RequiredRaces/Classes`, `SrcItemId`.
6. **Mapzeroth Forever** (MIT) for NPC positions, travel nodes, inns.
7. **Method / Icy Veins / Wowhead guides** (`method.gg/wow-forever/...`,
   `icy-veins.com/wow-forever/`) for *recommendations*: dungeon pre-quest
   lists, leveling order, what a chain rewards. These are opinions by
   humans; use them to find quests, then verify each quest in 2–5. Never
   copy their prose; never cite them as proof of a requirement.

A fact enters the catalogue with: source URL, capture date, and for pages
a hash. A fact without provenance is removed at the next build.

### 4.2 The loop, exactly
1. `python3 data-tools/audit_quest_guides.py` → `GuideAudit.json`
   (missing locations, unverified pickups/quantities per guide).
2. `python3 data-tools/guide_source_queue.py` → `GuideSourceQueue.json`
   (currently 315 quests: 159 objective areas, 156 pickup requirements,
   53 pickups, 42 hand-ins, 15 quantities). This is your worklist.
3. `python3 data-tools/capture_quest_pages.py GuideSourceQueue.json
   --cache <dir> --denials QuestCatalogue.json` — captures pages for the
   queue, stops on denials.
4. Write corrections into `data-tools/quest_corrections.json` (format in
   §9), one entry per quest, each with a source sentence that a human can
   check in 30 seconds.
5. `python3 data-tools/build_quest_dataset.py` then `pack_data.py` →
   regenerated `WowTogether_QuestData/QuestCatalogue.lua`. Never edit the
   generated Lua.
6. `python3 WowTogether/data-tools/tests/run_tests.py` (both suites) and
   `audit_quest_flow.py` → compare `GuideFlowAudit.json` before/after:
   total route length per guide must not grow without an explanation.
7. Changelog entry (§9) naming the quests, the guides, and the audit delta.

### 4.3 Dungeon pre-quests, specifically
For each dungeon in `DungeonData.lua` (28 today):
1. Start from `https://www.wowhead.com/forever/quests/dungeons/` and the
   dungeon's Method page (`method.gg/wow-forever/dungeons/<slug>`). Build
   the candidate list: every quest whose objective is inside, whose item
   drops inside, or whose chain ends inside.
2. For each candidate, open the Wowhead Forever quest page: record start
   NPC/object (with zone and coords from the NPC page), prerequisites
   (series tab), side, min level, and whether it is new/updated for Forever
   (`foreverStatus`). A quest whose start is outside the dungeon is a
   pre-quest; put it in `collectionGoals` with its chain's first step as
   the collection root.
3. Attunements and keys (e.g. a quest that grants a key or unlocks a door)
   are **required** pre-quests (`collectionRequired`); everything else is
   optional with "Collect before entering <dungeon>" as its reason.
4. Item-started quests: the item page lists the drop source; if the drop is
   inside the dungeon, the quest is an *inside* step with a "loot first"
   hint, not a pre-quest.
5. Verify in game once per dungeon with a character of each faction: the
   probe's "Dungeon viewer" and "Dungeon reference markers" lines report
   positions; `offerKnowledge` reports NPC offers. Record who verified.
6. Add a catalogue test: `test("<dungeon> pre-quests for <faction>", …)`
   asserting the exact list of routable pre-quest IDs for a stated
   character.

### 4.4 Class quests, specifically
See CODEX_CLASS_QUESTS.md. Research order: Wowhead Forever class quest
category page → each quest's series tab → QuestieDB `nextQuestInChain` /
`exclusiveTo` → confirm breadcrumbs by title pattern and start/end NPCs.
Per class, per faction, produce the chain graph (root → steps → reward)
and the list of errands, then assert it in `catalogue_tests.lua`.

### 4.5 When the ranked sources do not have it: find new ones

The list in 4.1 is a starting set, not a fence. When a fact is missing
from all of them (Forever-only content, a renamed NPC, a quest whose
Wowhead page is empty, a custom zone like map 2521), go looking. Do it
like this, and record what you did.

**How to search.** Use a web search with the most specific tokens you
have, in this order of specificity: quest ID with the server name
(`"quest=79948" forever`, `79948 "Defensive Magics 101"`), exact title in
quotes plus `wow forever` / `classic forever`, NPC or object name plus
the zone, then the chain or system name ("research access mage forever
books"). For positions, add `coords` / `location`; for chains, add
`prerequisite` / `attunement` / `pre-quest`. Search both English and the
spelling variants the server uses. Repeat with the vanilla title and
`classic` only for quests whose `foreverStatus` is neither new nor
updated.

**Where new sources usually turn up.**
- Fan wikis of the server (any `*.wiki.gg`, Fandom or MediaWiki site that
  shows quest IDs and NPC coordinates for Forever).
- The server's own forums, Discord/Reddit threads, patch notes and news
  posts (good for *existence* and *change* facts: "X was moved to Y in
  patch 1.60").
- Other open-source addons that carry Forever data on GitHub/GitLab
  (search `"forever" quest lua npc coords github`): structured, often the
  best source for coordinates and chains. **License first** — see below.
- Database mirrors for vanilla-unchanged content: classicdb.ch,
  classic.wowhead.com, warcraft.wiki.gg (already used for one NPC).
- Video guides: usable only to *locate* something on a map (pause, read
  the on-screen coordinates), then verify in game. Never a sole source.

**How to vet a site before using it.** It qualifies as a data source
(tiers 2–6) only if all are true: it shows numeric IDs (quest/NPC/object)
or exact coordinates, not just prose; at least three facts you already
hold verified agree with it (spot-check against warcraftdb/Wowhead
Forever); it is dated or versioned, or you can date the capture; its
content is server-specific (says Forever/the patch) or the quest is
vanilla-unchanged. Otherwise it is tier 7: use it to find candidates,
verify each elsewhere.

**Register it.** A new source gets a line in `THIRD_PARTY_NOTICES.md`
(name, URL, license or terms, what we take from it) and, if it is a
structured repository, an entry in `data-tools/forever_source_manifest.json`
with the commit and file hashes, like the QuestieDB entry. Captured pages
go through `capture_quest_pages.py`'s cache so URL, date and hash are
recorded. A fact whose source is not registered is not a fact.

**License and copying rules.** Facts (IDs, levels, coordinates, which NPC
starts what) are facts; prose, quest text, images and guide writing are
not and are never copied. Data from another addon or database comes with
its license: MIT/BSD → take with attribution; GPL (cmangos is GPL-3, and
the catalogue already carries GPL-adapted baseline facts, see
LEGACY_DATA_COPYRIGHT.md and the QuestCatalogue header) → only via the
existing legacy-facts path and only for facts, with the notice updated;
unknown or "all rights reserved" → candidates only, verify elsewhere. When
in doubt, capture the fact in game instead; an observation needs no
license.

**Corroboration rule for new sites.** The first ten facts from any newly
registered site must each be corroborated by a tier-1..6 source or an
in-game observation before they become routable. After that the site may
be promoted to the tier its agreement rate earns (note the decision and
the ten quest IDs in the changelog). A site that contradicts verified
facts twice is demoted to tier 7 and the contradictions are listed.

**Respect the sites.** One capture per page per run, cached; honour
robots and rate limits; a denial ends the run for that host (the queue
tool already models this). Never automate a login, never scrape a Discord.

**Record the dead ends too.** When a search finds nothing, add the quest
to `GuideSourceQueue.json`'s needs with `"searched": [<queries>, <date>]`
so the next person does not repeat it and a tester knows to observe it in
game.

### 4.6 When sources disagree
In-game beats everything. Otherwise: structured data (Questie/cmangos)
beats page scrape beats guide prose. Record the disagreement in the
correction's `source` sentence and mark the quest `prerequisitesUnverified`
until a tester confirms; an unverified quest is never current.

---

## 5. Verification before you say "done"

1. `syntax_check.py`: 0 errors. `run_tests.py`: both suites pass.
2. For the thing you changed, a new assertion with real quest IDs and a
   stated character (class, race, level, completed IDs, position).
3. `audit_quest_flow.py` delta explained in the changelog.
4. For guide-order changes: enumerate what the guide would route for a
   fresh level 10/20/30/40 character of each eligible race; any step that is
   not obtainable at that point fails the change.
5. For text changes: paste three real cards (before/after) into the PR
   description using the §2 layout; each must pass the four questions.
6. For data changes: the probe line "Guide pickups for <tester>" must show
   the affected quest with the expected reason code.

Tester bug reports start from `/wt probe`. Ask for it. The fields you need:
"Selected guide", "Trip quest IDs", "Destination reason", "Reason evidence",
"Guide pickups" (quest ID + reason), "Offer evidence", character line.
Diagnose the quest ID, find the layer (§1 table), fix that layer, add the
test, ship.

---

## 6. Change discipline

- Data over code: a correction with a source beats a rule; a general rule
  beats a special case; a special case for one quest ID in guide code is a
  rejected change.
- One concern per commit; one definition per `ns.*` function; no wrapping
  another module's function (see REVIEW_0_8_90.md).
- The TOC is the only version. Bump it with every release; saved fixed
  plans rebuild on version change, so say so in the changelog.
- Never patch generated Lua (`QuestCatalogue.lua`, `DungeonJournalData.lua`,
  `ProfessionData.lua`); patch the JSON inputs and rebuild.
- Ship with `package_release.py`; repo-only files (JSON audits, tools,
  these docs) do not go to players.
- 120 columns for new code; reflow a file only when touching it anyway.

---

## 7. Backlog, in order (do not reorder without a reason in the changelog)

1. Import QuestieDB `nextQuestInChain` → `nextInChain`; relax the
   reciprocal-only `exclusiveTo` filter to Questie's one-directional
   semantics. Re-run the breadcrumb tests; expect the inference to be
   rarely reached.
2. "Later" collapse: a non-specific reason can never be the current step.
   Add the status line and the collapsed group to the card.
3. Faction-aware hand-ins (§3.5); resolve the mage research-book hand-in
   for Horde with a tester.
4. Chain-first ordering for the class guide (§3.2).
5. Work the 315-quest source queue down; report the count per release.
6. Dungeon pre-quests per dungeon (§4.3), one dungeon per release, with
   the per-faction test.
7. Any-of reasons for zone guides (today only class guides carry
   `collectionAlternatives`).
8. The REVIEW_0_8_90.md P1 items (artifacts out of the addon folder,
   per-character saved variables, INSTALL/CHANGELOG split).

---

## 8. Things that look like improvements and are not

- Rewriting step strings by hand to sound nicer. They are generated; fix
  the generator or the data.
- Hiding a confusing step by excluding the quest in `quest_exclusions.json`
  without recording why. Exclusions need the same source sentence as
  corrections.
- Adding a website's recommended leveling order as fixed data. The
  optimizer decides order from positions and prerequisites; a website's
  order is a test oracle at best.
- Trusting `foreverStatus = updated` quests to behave like vanilla. They
  changed; cmangos facts do not apply; Wowhead Forever or in-game only.
- Marking a quest verified because the tester "did it fine". Verified means
  the specific fact (offer, position, prerequisite) was observed and
  recorded with the character line.

---

## 9. Templates

### 9.1 Correction entry (`data-tools/quest_corrections.json`)
```json
{
  "questID": 1943,
  "title": "Speak with Deino",
  "source": "QuestieDB Forever foreverQuestFixes.lua commit <sha>: nextQuestInChain = 1944; Wowhead Forever quest=1943 series tab lists Waters of Xavian next (captured 2026-11-08, sha256 <hash>). Observed on <tester> (Troll mage 26): Anastasia Hartwell did not offer 1943 after 1944 was complete.",
  "stageCorrection": {
    "kind": "chain-facts",
    "nextInChain": 1944
  }
}
```

### 9.2 Catalogue test (`data-tools/tests/catalogue_tests.lua`)
```lua
test("Speak with Deino is superseded once Waters of Xavian is done", function()
    -- Troll mage, level 26, Undercity
    completed[1944] = true
    local other, relation = taken(1943)
    assert(other == 1944 and relation == "breadcrumb")
end)
```

### 9.3 Changelog entry (INSTALL.md / CHANGELOG.md)
```
0.8.91 <SHOUTY TITLE> <one sentence of player-visible effect>.
Data: <quest IDs changed>, sources in quest_corrections.json. Guides
affected: <list>. GuideFlowAudit delta: <N> fewer steps / <M> yards shorter
in <guide>. Tests: <names>. Saved fixed plans rebuild at login.
```

### 9.4 Tester report (ask for this, verbatim)
```
Character: <name> <race> <class> <level> <faction>, standing in <zone>
Guide: <name from the card>
What the card said: <title / what line / why line>
What happened: <NPC did not offer / wrong place / unclear why>
/wt probe pasted below.
```

### 9.5 Card review (three per text change, in the PR)
```
BEFORE                                  AFTER
Defensive Magics 101                    Defensive Magics 101
Accept from Manual                      Read the Manual (ground object) to start Defensive Magics 101
212 yd • ~0m 30s travel                 One of 40 options that unlock Research Access; this is the nearest for you.
Outside your useful leveling range;     Optional • on your way • 212 yd, ~30 s
this saved or previewed step can be
skipped.
```

---

## 10. The three questions to ask yourself before every change

1. Will a player ever be sent somewhere that does not offer what the card
   promises? If the answer depends on data you have not verified, stop and
   verify.
2. Does the card say why, from data, in one line a stranger understands?
3. Is there a test with real quest IDs that fails before and passes after?

If any answer is no, the change is not ready.
