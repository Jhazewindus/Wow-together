# Codex brief: Wow Together app redesign — same functions, half the reading, fewer clicks

This supersedes the layout parts of CODEX_UI_PRESENTATION.md (its step
composer, icon table and Glance mode stay) and the panel sketch in the
party brief. Nothing functional is removed. Every existing `ns.*` function
keeps working; frames that store positions keep their global names.

---

## 0. The problem, from the inventory

Today the addon exposes its features through **22 named windows**, a
**dropdown** to switch between seven views in the main window, **four
pop-up prompts** (activity, dungeon entry, party route, session
checkpoint), a settings window with **54 options in 9 sections**, each
with a paragraph of help text, and **17 slash commands**. The main window
opens with an eyebrow line, a title, a subtitle and three metric boxes
before the first button. A new player reads for a minute and still has
not pressed anything that moves them.

The design target is simple to state: **one thing on screen while
playing, one place for everything else, nothing that interrupts.**

---

## 1. Information architecture

```
HUD  (always on while a guide is active; the only thing on screen)
 ├─ step card (CODEX_UI_PRESENTATION §4.1 / Glance §2b)
 ├─ action bar: ‹  Skip step  Skip quest  ›   ⏸   ☰
 └─ suggestion chips (replace all pop-ups)

HUB  (one window, ☰ or /wt or minimap button; opens on the Play tab)
 ├─ Play     what to do next: current guide + suggestions, each with one button
 ├─ Group    party plan, members, missing quests, share, catch-up
 ├─ Browse   Leveling · Class · Dungeons · Professions · Quests  (filter row + search)
 ├─ Settings grouped by what the player sees, presets, search, hover help
 └─ footer:  sync state · data age · version · [Report a problem]

TOOLS (separate windows, opened from Browse or a chip, never on their own)
 ├─ Dungeon viewer (maps) — tabs Map · Quests · Approach, one Start button
 ├─ Profession workbench — tabs Guide · Materials · Auction
 └─ Advanced: Diagnostics, Lua console, exports (Settings › Advanced › Tools)
```

Everything else (tracker, guide quest list, dungeon quest list, shopping,
auction materials, group finder roles, approach map, prompts) becomes a
tab, a card or a chip inside those three. The named frames stay as
hidden containers for one release so saved positions migrate.

---

## 2. The HUD

The step card from CODEX_UI_PRESENTATION §4.1 (three lines) or Glance
(one line), plus:

```
┌ Horde / The Barrens · step 12 of 48 ──────────────── ⏸  ☰  × ┐
│ [⚔]  Kill 8 Laughing Sisters  3/8                               │
│      Required for Protect Kanati Greycloud                      │
│      Required · 210 yd, ~30 s · with Bob                        │
│ ‹      Skip step      Skip quest      ›                         │
│ ▸ Dungeon entrance nearby — Open map · Not now                  │  ← chip
└─────────────────────────────────────────────────────────────────┘
```

- **Title bar**: guide name and step counter only. `⏸` pause (personal),
  `☰` opens the Hub on Play, `×` hides the HUD (the Hub keeps a "Show
  guide window" button and the minimap button restores it). "Solid" and
  "Stop" leave the title bar: Solid is a setting (and right-click on the
  title bar); Stop is on the Hub's Play tab as "Stop this guide".
- **Action bar**: four controls, always the same place. "Continue anyway"
  appears in place of Skip step only when the current step is a Later
  step the player forced.
- **Suggestion chips** replace every pop-up. One line, muted, below the
  action bar, at most one visible at a time, newest wins, auto-expires
  after 30 s or when no longer true. Two tappable words at most:
  - `Dungeon entrance nearby — Open map · Not now` (was DungeonEntryPrompt)
  - `Bob started a route — Follow · Keep mine` (was PartyRoutePrompt;
    automatic in party mode, chip only when the answer is "ask")
  - `Save & pause before logging out? — Save · Dismiss` (was
    SessionCheckpoint; shown only when the player opens the logout dialog)
  - `3 collection quests here — Show plan · Later` (was ActivityPrompt)
  - `Class trainer in range: level 26 skills — Route · Done` (training)
  - `Vendor nearby: 18 free slots, 85% durability — Route · Skip` (services)
  - `Flight master nearby: unlock it (+40 s) — Route · Skip` (discovery)
  Chips never block input, never steal focus, never stack. A dismissed
  chip of the same kind does not return for that trigger.
- **Glance toggle**: click the step counter.
- Resizable width only; height follows content.

---

## 3. The Hub

One window, four tabs on a left rail, 860 × 520 default, resizable.
Opens on **Play**. No eyebrow, no subtitle, no metric boxes; the footer
carries the numbers.

### 3.1 Play — "what should I do next"
```
┌ Wow Together ────────────────────────────────────────────── ⚙ × ┐
│ Play   │ ► Horde / The Barrens · step 12 of 48 · 2.1 levels left │
│ Group  │   [Continue]  [Change order…]  [Stop this guide]          │
│ Browse │                                                           │
│ Settings│ Next for you                                             │
│        │  [!] Class quest ready: Waters of Xavian (Orgrimmar) [Follow]│
│        │  [⛩] Razorfen Kraul prep: 3 of 5 quests collected  [Follow]│
│        │  [➤] Next zone at 29: Hillsbrad Foothills (4 min)  [Follow]│
│        │  [⚒] Tailoring 112/150 — 2 recipes to learn       [Open]  │
│        │                                                           │
│        │ Party: 3 synced · plan rev 7                       [Group]│
├────────┴───────────────────────────────────────────────────────────┤
│ sync ok · quest data 2 days old · 0.8.102              [Report a problem] │
└────────────────────────────────────────────────────────────────────┘
```
- First row: the active guide, progress, remaining XP (Brief 04 when
  enabled; levels otherwise), three buttons. "Change order…" opens the
  guide's step list (today's GuideQuestList) as a side panel inside the
  Hub, not a window.
- "Next for you": up to five suggestion cards computed from what the
  addon already knows (recommended guide, class quests available, dungeon
  prep state, zone exit, professions with learnable recipes, catch-up
  with party). Each card has **one** button. Cards are ordered by the
  cost model's benefit; no card without a specific benefit.
- No guide active → the first row is the recommended guide with
  [Follow]; nothing else changes.
- "Report a problem" copies the tester template with the probe pre-filled
  to a copy box (replaces `/wt probe` for players; the command stays).

### 3.2 Group — the party plan (party brief §4.2)
Panel from the party brief, inside this tab: member rows (level, zone,
ETA, next step, Waypoint), "Missing vs plan" with the fix, share state,
`Plan for the group` / `My own plan`, `Catch-up details` (today's
tracker rows). Party mode ask/always/never lives here too as a one-line
control, mirrored in Settings.

### 3.3 Browse — find a guide or a quest
Filter row instead of the dropdown: `Leveling · Class · Dungeons ·
Professions · Quests`, plus a search box that matches guide names, zone
names and quest titles across all five. Cards keep their layout; each
card's primary button is **Follow** (today: Start questline / Start route
/ Start quest route / Route to pickup — four labels for one action).
Secondary actions on a card go in a `…` menu: Preview on map, Quest list,
Open viewer (dungeons), Materials (professions).

- Dungeons card `Open viewer` opens the Dungeon viewer tool.
- Professions card `Open` opens the Profession workbench tool.
- Quests = today's "Quest log" review + "All quests" library merged, with
  the search box doing the filtering; "Quest details" is a side panel.

### 3.4 Settings — grouped by what the player sees
Six groups, every option on one line, help on hover (and a `?` for touch),
a search box at the top, three presets at the top.

```
Presets:  ( ) Simple   (•) Standard   ( ) Everything          Search: [____________]

Guide window    Show the guide window · Glance mode · Solid background · Next-step preview
                Separate arrow · Route on the minimap · Distance units [yd/m]
Automation      Accept guide quests · Turn in (no reward choice) · Select suggested flights
                Share quests with party · Track plan quests · Open guide quests at NPCs
Routing         Mapped travel routes · Learn roads · Hearthstone & teleports
                Flight suggestions [off / faster only / also nearby masters] · Inns · Corpse
                Nearby quest detours [slider] · Suggest the next zone
Map markers     Quest NPCs & items · Beside nameplates · Star guide givers · Patrols
                Elite spawns · Enemy marker style
Party           Party mode [ask/always/never] · Share observations · Show positions
                Wait prompts · Group finder filters · Panel background
Advanced ▸      Fixed zone guide order · Recheck skipped quests · Class training reminders
                Dungeon prompts & maps · Profession scan · Highlight current quest
                Tools: Diagnostics · Lua console · Export quest data · Export findings · Reset skips
```
- 54 options stay 54 options; what changes is grouping, one-line labels,
  hover help, and that Advanced is collapsed by default (18 of them).
- Presets set groups of defaults; changing any option switches the preset
  indicator to "Custom". Simple = automation on, markers minimal,
  Glance on. Everything = all on.
- Every option label is a verb phrase or a noun, ≤ 32 characters; help
  text ≤ 110 characters, shown on hover only.

### 3.5 Footer
`sync: 3/3 synced` or `solo` · `quest data: 2 days old` (red over 21) ·
version · `[Report a problem]`. Replaces the three metric boxes and the
status line.

---

## 4. Tools (secondary windows)

### Dungeon viewer
Keep the map renderer; collapse nine buttons into: tabs `Map · Quests ·
Approach`, a `Locate me` toggle, one `Follow` (start quest route). "BG"
→ setting "Solid background" shared with the HUD. "Open map"/"Not now" →
chip. The dungeon quest list and dungeon map quests windows become the
Quests tab.

### Profession workbench
One window, tabs `Guide · Materials · Auction`; "Refresh bags / prices"
and "Search AH" stay as the two buttons on their tabs. Shopping and
auction materials windows fold in.

### Group finder roles
Stays attached to Blizzard's LFG frames (it is a filter panel); its
on/off is the Party setting. No Hub presence beyond that.

### Advanced tools
Diagnostics, Lua console and exports open from Settings › Advanced ›
Tools and from their slash commands. Unchanged inside.

---

## 5. Click budget (acceptance)

| task | today | target |
|---|---|---|
| start the recommended guide from nothing | open window, dropdown Recommended, find card, Start questline (4) | ☰ → Follow (2), or chip "Follow" (1) |
| switch to a class quest that just became available | dropdown Class quests, scroll, Start (3+) | Play card → Follow (2), chip (1) |
| see who in the party lacks what | /wt tracker or window + read | Group tab (1) and "with Bob" on the HUD (0) |
| open the dungeon map when near an entrance | pop-up → Open map (1, but modal) | chip → Open map (1, non-modal) |
| skip a step | 1 | 1 |
| change one setting | Settings, section, scroll, read paragraph (3+) | Settings, type in search, click (2) |
| pause / resume | 1 | 1 |
| report a problem | /wt probe, select all, copy, paste, explain | Report a problem → copy (2) |
| find a quest by name | All quests, scroll | Browse, type (2) |

Also: zero modal prompts during play; no screen opens with text the
player must read before the first button; every primary action is the
same word everywhere (**Follow**).

---

## 6. Copy rules (short)

- Buttons are verbs, one word where possible: Follow, Continue, Stop,
  Skip step, Skip quest, Open, Route, Share, Dismiss.
- No product copy in the UI (no eyebrows, slogans, "your next adventure").
- Titles state function: "Wow Together", "Horde / The Barrens", "Dungeon
  viewer", "Settings".
- Status in the footer only; never a status line inside a content area.
- Step text per CODEX_STEP_TEXT.md.

---

## 7. First run

One screen inside the Hub on first login (and from Settings › "Show
first-run"):
```
What are you here for?   [Leveling]  [Class quests]  [Dungeons]
Playing with friends?     Party mode: (•) ask  ( ) always  ( ) never
Automation?               (•) Accept and turn in guide quests for me   ( ) I'll do it
                                                         [Start]
```
Three decisions, one button. Everything else is a default.

---

## 8. Migration plan (one PR each, each shippable)

1. **Chips instead of prompts.** Add the chip bar to the HUD; route the
   four prompts and the three "nearby" tips through it. Delete the four
   prompt frames. Biggest felt improvement, smallest risk.
2. **HUD action bar.** `⏸ ☰ ×` in the title bar; Solid → setting/right-
   click; Stop → Play tab. Keep frame names.
3. **Hub shell.** Left rail with Play / Group / Browse / Settings; move
   the existing card list under Browse with the filter row; Play tab with
   the active-guide row and suggestion cards; footer. Dropdown removed.
4. **Settings regroup.** Groups, one-line labels, hover help, search,
   presets, Advanced collapsed. Automated check: every default key
   appears exactly once in the groups.
5. **Group tab** per the party brief (lands with brief 09 steps 1–3).
6. **Tools consolidation.** Dungeon viewer tabs; Profession workbench;
   delete the folded windows.
7. **First run** and "Report a problem".

Do not start 3 before 1 and 2 are in a release: the HUD is what people
see; the Hub is where they go when the HUD is not enough.

---

## 9. Tests and checks

- `presentation_tests.lua` (existing plan) covers card text; add
  `chips_tests.lua`: each prompt source produces one chip, newest wins,
  expiry, dismissed-does-not-return, no two visible.
- Settings coverage: parse `Config.lua` defaults vs groups → every key
  once, every label ≤ 32 chars, every help ≤ 110 chars.
- Click budget table verified by hand per release and pasted in the PR.
- Frame names: `WowTogetherWindow`, `WowTogetherRouteArrow`,
  `WowTogetherStandaloneArrow`, `WowTogetherTracker`, `WowTogetherSettings`,
  `WowTogetherDungeonViewer` keep their names; saved positions survive
  (test by setting a position in old saved variables and loading).

---

## 10. What this does not change

Routing, eligibility, data, guide building, sync protocol, the step
composer, icons, Glance. Every slash command keeps working. `/wt` with no
argument toggles the Hub; `/wt help` lists the commands.
