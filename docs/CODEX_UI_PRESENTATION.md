# Codex brief: guide step presentation (card, tooltip, arrow, list)

Scope: the presentation layer only — how a step is worded and laid out on
the guide window, its tooltip, the standalone arrow and the guide list.
Not in scope: routing, eligibility, guide building, saved data, frame
sizes/positions. No full rework: the frames stay, the logic stays; what
changes is that one composer produces structured fields and every
renderer draws from those fields instead of gluing strings.

Read CODEX_STEP_TEXT.md (wording rules) and CODEX_GUIDE_QUALITY.md §2
(quality bar) first; this brief is the implementation of those.

---

## 1. The problem, traced

The tooltip in the 2026-11-08 screenshot shows eleven lines for one
teleport step, including the reason twice and the action twice. Cause,
found in code:

- `Navigation.lua updateTooltip` concatenates three independent strings:
  `ns.GuideStepDescription(stop)` (title, instruction, hint, reason,
  location), the card's own context label (`ns.RouteContext` → reason
  *again*, with the quest's pickup hint welded onto the same line), and
  the travel summary (`ns.TravelPathSummary` → the action again, with a
  trailing period).
- The only defence is `compactTooltipText`, an exact-line dedup. "Required
  for X…" survives because the second copy has extra words on the line;
  "Cast Teleport: Orgrimmar" survives because the second copy has a
  period.
- Meta sentences add lines that carry nothing: "Follow the travel
  instructions for this leg." (`GuideStepHint`), "The route re-plans after
  you arrive." (`TravelPathSummary`), "Follow your class quest guide."
  (`LevelingGuides`).
- Every line is the same white 10–12 pt text; there is no hierarchy
  between what to do, why, and bookkeeping.

Two string builders each trying to be complete will always collide. The fix
is structural: one composer, fields, renderers that pick fields.

---

## 2. Design principles (inspiration: Zygor Guides, Questie — not a copy)

Take the ideas, not the art, text or layout. What those two do well:

- **One instruction per step, verb first, with an icon that says the kind
  of action before you read it** (accept / turn in / kill / collect /
  travel). Zygor's step list is scannable because every line has the same
  shape.
- **Progress is visible on the step itself** (3/8, a check when done),
  not in a separate sentence.
- **The current step is loud, the rest is quiet.** One bright line, the
  next step as a muted peek, everything else collapsed.
- **The same symbol means the same thing everywhere** — Questie's map
  icons, minimap icons and tooltips use one vocabulary. Our card symbol,
  map pin (`ns.StopIcon`) and minimap line must agree.
- **Tooltips add detail, they do not repeat the line you hovered.**
  Questie's quest tooltips list objectives with counts, nothing else.
- **Calm density.** Short lines, consistent punctuation, muted secondary
  text. A player glances, acts, glances again.

What we deliberately do *not* take: Zygor's hand-written prose steps (ours
are generated), Questie's icon art (Blizzard textures via `ns.StopIcon`
only), any paywalled or proprietary layout detail. No copied strings, no
copied textures, no copied frame templates.

---

## 2b. Icon vocabulary and Glance mode (small-screen first)

The icon carries the verb; the text carries the object and the number.
Use the symbols the game already teaches, from the client's own textures
(no art, consistent with map pins). Eight symbols, never more.

| kind | symbol | texture (probe on load; fall back to the glyph) | glyph fallback |
|---|---|---|---|
| accept (pickup) | yellow ! | `Interface\GossipFrame\AvailableQuestIcon` | `!` |
| turn-in, ready | yellow ? | `Interface\GossipFrame\ActiveQuestIcon` | `?` |
| turn-in, not ready yet | grey ? | `Interface\GossipFrame\IncompleteQuestIcon` | `?` (muted) |
| kill | sword | `Interface\CURSOR\Attack` | `⚔` |
| collect / loot / use item / ground object | hand | `Interface\CURSOR\Pickup` (object: `Interface\CURSOR\Interact` if present) | `✋` |
| talk to / escort start | speech bubble | `Interface\CURSOR\Speak` | `…` |
| travel: fly / hearth / walk, ship, zeppelin | taxi / mug / footprints | `Interface\CURSOR\Taxi`, `Interface\CURSOR\Innkeeper`, `Interface\CURSOR\Point` | `➤` |
| party: wait / together / share | group marker | `Interface\TargetingFrame\UI-RaidTargetingIcon_1` tinted muted, or the existing shared-pin variant | `⇄` |

Rules:
- `kind → symbol` is one table in `GuideText.lua`
  (`ns.STEP_SYMBOLS`); the card, the quest list, the map pin
  (`ns.StopIcon`) and the minimap all read it. If they disagree today,
  the map wins and the table is corrected.
- Probe the eight textures once at load (`GetFileIDFromPath` or a hidden
  texture with `SetTexture` + `GetTexture` round-trip); a missing one
  switches that kind to its glyph for the session and the probe reports
  "Step icons: 7/8 textures, kill using glyph".
- Icon size 20 px on the card, 16 px in the list; always left of the text
  with 6 px gap; never two icons on one line.
- Vendor / trainer / corpse keep their existing icons but are never shown
  in Glance mode unless they are the current step.

### Glance mode
Option `guideGlance` (off by default; one click on the card's title bar
toggles it, state remembered). One line per step, nothing else:

```
[⚔] Laughing Sisters 3/8 · 210 yd
[!] Deino · 1.2 km
[?] Kil'hala · Crossroads
[✋] Hairs 4/12 · 90 yd
[➤] Crossroads FM · fly
```
- Text = object + count (+ one word for travel kind). No verbs, no why,
  no status words; those appear on hover (tooltip from the same fields).
- Distance rounds: < 1000 yd → "210 yd"; ≥ 1000 → "1.2 km"; another zone →
  the zone name.
- Party tags collapse to the group marker; hover lists who.
- The quest list in Glance mode is icon + title + count, current row
  bright, others muted; Later rows hidden behind a single "+N later"
  line.
- Normal mode is unchanged (§4.1). Both render from
  `ns.GuideStepPresentation`; Glance is a second renderer, not a second
  composer.

Acceptance for Glance: the five lines above, read from a 320-px-wide
card, are understood by someone who has never seen the addon. Tooltip on
each still passes the four questions.

---

## 3. The composer: `ns.GuideStepPresentation(stop, facts, guide, route, state)`

New function in `GuideText.lua`. Pure: reads existing helpers, returns a
table, never touches frames. Every renderer calls it once per update and
reads fields. Field list, each with its source and its cap:

| field | type | source | cap / rule |
|---|---|---|---|
| `kind` | string | `stop.kind`, `facts.action`, travel leg method | one of accept, turnin, kill, collect, use, talk, explore, travel-walk, travel-fly, travel-ship, travel-hearth, travel-teleport, trainer, vendor, corpse, dungeon, notice |
| `icon` | texture path | `ns.StopIcon(stop)` for quest kinds; travel kinds map to existing taxi/ship/hearth textures already used on the map | always set |
| `title` | string | `facts.stop.title` | quest title; for travel legs the *quest* title (the leg borrows the card, §5) |
| `stepLine` | string | guide name, `stop.guideStep`, total steps | "Step 12 of 48 • Horde / The Barrens"; "Optional class training" / "Optional vendor visit" for those kinds |
| `what` | string | `ns.StopInstruction` for quest stops; `ns.PersonalTransportLabel` / `transportAction` for travel legs | ≤ 70 chars, imperative, no trailing period, numbers before nouns, object givers "Read the X (ground object) to start Y" |
| `progress` | string or nil | `facts.progress` | "3/8" rendered as a suffix of `what` on the card, own line nowhere |
| `why` | string or nil | `ns.GuideDestinationDecision(...).why` (reason sentence) | ≤ 110 chars, no trailing period, nil when `specificBenefit = false` (then `status` says Later) |
| `status` | string | derived (§7) | "Required", "Optional, on the way", "Later (level 35)", "Done" |
| `time` | string or nil | existing `clock`/`distance` logic in Navigation | "212 yd, ~30 s" / "~14 min 39 s" |
| `location` | string or nil | `ns.StopLocationText` | "Orgrimmar • 38.6, 85.9"; for travel legs the *leg's* target |
| `then_` | string or nil | the quest stop's own `what` when a travel leg borrowed the card (§5), else nil | "Then: loot the quest item from Galak Messenger and use it to start the quest" |
| `travel` | string or nil | `ns.TravelPathSummary` reduced to its plan sentence | "Teleport, then walk ~2 min" — no "re-plans" sentence (that is `status` text for travel-* kinds: "Route re-plans after you land") |
| `details` | list of strings | `ns.QuestGroupWarning`, "For <player>", provided quest items, `decision.caution`, `compactStepHint` *only* when it is not already `what` or `then_` | each ≤ 110 chars; max 3 |
| `evidence` | string or nil | reason code + confidence: `decision.code`, `decision.confidence`, `decision.estimated` | "Reason: useful-prerequisite • estimated" — tooltip only, last |

Rules inside the composer:

- Dedup by field, not by string. A sentence that is already `what`, `why`
  or `then_` is never also a detail. `compactTooltipText` keeps its
  trimming and empty-line removal; its exact-line dedup becomes a safety
  net, not the mechanism.
- Punctuation: card fields (`what`, `why`, `status`, `stepLine`,
  `location`) have no trailing period; tooltip-only fields (`then_`,
  `travel`, `details`, `evidence`) are sentences with full stops.
- No addon vocabulary in any field except `evidence`: no "saved or
  previewed", "selected guide", "Dijkstra", "published", "snapshot",
  "revision", "beta", "guide step" as a noun.
- Hedges ("may", "possibly", "under review") only in `details`, never in
  `what`/`why`.

Compatibility: `ns.GuideStepDescription`, `ns.RouteContext`,
`ns.GuideStepHint` stay as thin wrappers that render from the presentation
(`GuideStepDescription` = tooltip rendering; `RouteContext` = `why` +
`status`), so `AreaObjectives.lua`, `GuideQuestList.lua` and
`StandaloneArrow.lua` keep working during the migration. Remove the
wrappers once every caller reads fields.

---

## 4. Renderers

### 4.1 Guide window card (`Navigation.lua UpdateNavigation`, frame built in `CreateNavigation`)
Layout, top to bottom, left column is the icon:

```
┌ <title> ───────────────────────── [Pause] [Solid] [Stop] [x] ┐
│ <stepLine>                                                   │  10 pt muted
│ ┌───┐  <what> <progress>                                     │  12 pt, bright (UIColors.text)
│ │ic │  <why>                                                 │  10 pt muted
│ └───┘  <status> • <time>                                     │  10 pt, status coloured (§7)
│ [‹]  [Skip step]  [Skip quest]                         [›]   │
└──────────────────────────────────────────────────────────────┘
```

- `frame.status` ← `what` (+ " " + `progress`). The arrow glyph stays in
  the icon box; when there is no arrow (personal transport, arrived), the
  icon box shows the kind icon instead of "…".
- `frame.context` ← `why`. One line, truncated with "…" at 110 chars.
- New label `frame.state` ← `status` + " • " + `time`. Replaces the
  current `frame.distance` placement; `distance` becomes part of this line.
- Title bar: "Scan guide" moves up next to Pause as an icon button with
  tooltip "Re-scan quest log and rebuild the route". "BG" → "Solid"
  (tooltip: opaque background), "ST" → "Stop" (tooltip: stop the guide).
  Same widths as today; captions change, positions change, nothing else.
- The row of buttons at the bottom keeps ‹ Skip step Skip quest ›.
- Optional, behind option `guidePeek` (default on): one more muted line
  under the state line, "Next: <next stop's what> (<zone>)", from the
  route's next displayed stop. Clicking it does nothing (it is a peek).
- Nothing else is added to the card. If a field does not fit, it goes to
  the tooltip, not to a fourth card line.

### 4.2 Tooltip (`Navigation.lua updateTooltip`, `StandaloneArrow.lua` tooltip, `GuideQuestList.lua` row tooltip, `AreaObjectives.lua` tooltip)
Renders only fields the hovered surface did not show, in this order:
`then_`, `location`, `travel`, `details…`, `evidence`. Cap six lines;
drop from the end (`evidence` first, then details beyond the first).
Header line is the title in gold (already the convention). For the guide
list rows (which show title + icon only), the tooltip additionally starts
with `what`, `why`, `status`.

### 4.3 Standalone arrow (`StandaloneArrow.lua`)
`what` (+ progress) and `time` only. Tooltip as 4.2.

### 4.4 Guide quest list (`GuideQuestList.lua`)
Each row: kind icon, title, and a right-aligned short `status` ("Later
35", "Done" check). Current step row bright, others muted. Optional-only
steps show a hollow icon variant (alpha 0.6), not extra text.

### 4.5 Map pin and minimap line
No change in this brief, but the kind icon used on the card must be the
same texture `ns.StopIcon` puts on the map pin for that stop. If they
differ today for any kind, the card follows the map.

---

## 5. Travel legs borrow the card

When `ns.TravelDestination` returns a travel waypoint for a quest stop
(`result.kind == "travel"` or `"f"`), the card belongs to the leg:

- `title` = the quest's title; `stepLine` as for the quest.
- `what` = the leg's instruction: "Cast Teleport: Orgrimmar", "Use your
  Hearthstone to Tarren Mill", "Fly to Crossroads", "Follow the road
  towards Splintertree Post", "Walk to the Darkshore border".
- `why` = the quest's reason (not a travel sentence).
- `status` = the quest's status; `time` = the whole journey estimate.
- `then_` = the quest stop's own `what` with location in brackets.
- `travel` = the plan summary: transports in order with times, e.g.
  "Teleport, then walk ~2 min" / "Fly Crossroads → Orgrimmar (~3 min), then
  walk ~1 min". For a personal transport add the landing: "Lands in
  Orgrimmar" (a place, never the spell name). The "route re-plans after
  you land/arrive" clause appears once, as the travel-kind `status` text.
- Delete from `GuideStepHint`: the `travel`/`f` branch ("Follow the travel
  instructions for this leg.").

---

## 6. Deletions (exact strings, exact places)

| string | where | replacement |
|---|---|---|
| "Follow the travel instructions for this leg." | `GuideText.lua GuideStepHint` | none |
| "The route re-plans after you arrive." | `TravelNetwork.lua TravelPathSummary` (personal and trail branches) | `status` for travel kinds |
| "Follow your class quest guide." | `LevelingGuides.lua` guide `destination` | the first routable step's `what` |
| "Continue towards your guide destination." | `TravelNetwork.lua TravelPathSummary` terrain branch | none (the `then_` field covers it) |
| "; the map line follows it." | `TravelNetwork.lua` trail branch | none |
| "this saved or previewed step can be skipped" | `GuideReasons.lua` outside-level-range | sentence becomes `why = nil`, `status = "Later (level N)"` |
| "Check the guide status below." | `GuideStepHint` notice branch | the notice text itself |

Grep for each before closing the PR; the catalogue tests include a check
that none of these strings remain in `GuideText.lua`, `GuideReasons.lua`,
`TravelNetwork.lua`.

---

## 7. Status line semantics

Derived in the composer from the reason decision and the route:

| condition | `status` | colour |
|---|---|---|
| decision.specificBenefit and the stop is on the current chain / plan | Required | UIColors.gold |
| decision.specificBenefit and reason code ∈ {pickup-hub, return-hub, objective-area, early-reward, quest-log-space, dungeon-pickup, class-training, vendor} | Optional, on the way | UIColors.text |
| not specificBenefit (level-work, outside-level-range, selected-guide, guide-status) | Later (level N) | UIColors.muted |
| facts.finished or remaining == 0 | Done | UIColors.green |
| stop.confirmation | Confirm at the giver | UIColors.gold |
| travel kinds | the quest's status, plus " • route re-plans after you land/arrive" for hearth/teleport | as the quest |

A step whose status is Later is never the current step (CODEX_STEP_TEXT.md).
That rule is enforced in `GuidePolicy`/route selection, not in the
composer; the composer only labels.

---

## 8. Icons and colours

- Kind icons: reuse `ns.StopIcon(stop)` textures for quest kinds. Travel
  kinds: the taxi/ship/zeppelin/tram/hearth/teleport textures the world
  map already uses for transport pins (`Routes.lua`). No new art.
- Colours: `ns.UIColors.text` for `what`, `UIColors.muted` for `stepLine`,
  `why`, peek; status colours per §7; title stays gold.
- Sizes: title 13, what 12, why 10, state 10, step line 10 — the existing
  `ns.UILabel` sizes; no new fonts.
- Dark/opaque mode ("Solid") unchanged.

---

## 9. Implementation order (one PR each, each shippable)

1. **Composer, no visible change.** Add `ns.GuideStepPresentation`; make
   `GuideStepDescription`, `RouteContext`, `GuideStepHint` wrappers over
   it. Tests (§10) pass with identical output except dedup collisions,
   which are the bug.
2. **Tooltip from fields.** `updateTooltip` and the three other tooltip
   sites render §4.2. Duplicates disappear here.
3. **Card hierarchy.** `what`/`why`/`state` lines, kind icon in the box,
   colours. Delete the §6 strings.
4. **Travel legs borrow the card** (§5), including the landing-name rule.
5. **Chrome.** Scan guide to the title bar, Solid/Stop captions and
   tooltips, step line format.
6. **Peek line** behind `guidePeek`.
7. **Guide list rows** (§4.4).

Do not merge 3 before 2: the card is the place where clutter was hidden.

---

## 10. Verification

- New `data-tools/tests/presentation_tests.lua` (harness: construct stops
  by hand, stub `ns.CatalogueQuest`, `ns.GuideDestinationDecision`,
  `ns.TravelPathSummary`): assert the fields for (a) a quest pickup from
  an NPC, (b) a quest pickup from a ground object, (c) a kill objective
  with progress, (d) a turn-in, (e) a teleport leg borrowing the card,
  (f) a hearth leg, (g) a Later step (why nil, status Later), (h) a Done
  step. Assert: no field contains a forbidden word (§3 list), card fields
  have no trailing period, tooltip has ≤ 6 lines and repeats no card line
  (compare as sets after trimming punctuation).
- Add to `catalogue_tests.lua` a grep-style assertion that the §6 strings
  are gone from the three files.
- Paste three before/after cards in the PR (§11), produced from the real
  stops in the testers' screenshots, rendered by the test harness.
- `/wt probe` keeps showing the reason code and evidence; nothing moves
  out of the probe.

---

## 11. Acceptance: the three screenshots, after

**A. Defensive Magics 101 (object pickup, any-of group, level 35 at level 26)**
```
Defensive Magics 101                          Step 7 of 31 • Mage class quests
[!]  Read the Manual (ground object) to start Defensive Magics 101
     One of 40 options that unlock Research Access; this is the nearest for you
     Optional, on the way • 212 yd, ~30 s
tooltip: Alterac Mountains • 48.5, 57.7
         Reason: chosen-branch
```

**B. Assassination Plot (teleport leg borrowing the card)**
```
Assassination Plot                            Step 12 of 48 • Horde / The Barrens
[⌖]  Cast Teleport: Orgrimmar
     Required for Protect Kanati Greycloud later in this guide
     Required • ~14 min 39 s • route re-plans after you land
tooltip: Then: loot the quest item from Galak Messenger and use it to start the quest (Orgrimmar • 38.6, 85.9).
         Travel: teleport, then walk ~2 min. Lands in Orgrimmar.
         Reason: useful-prerequisite
```

**C. Speak with Deino after Waters of Xavian (must not be current)**
Not a card: the step is hidden with pickup reason `breadcrumb-superseded`.
If a tester sees it as current, that is a routing bug, not a text bug.

Acceptance is: every current step in a 30-minute play session passes the
four questions (CODEX_STEP_TEXT.md), no tooltip exceeds six lines, no line
appears twice on card + tooltip, none of the §6 strings is visible, and
the suite in §10 passes.
