# Module boundary: WowTogether_Gold and parallel development

Two agents (or two environments) on one repository work only if the
seams are drawn before the first commit. This file is the seam.

## 1. Layout
```
WowTogether/                 core (leveling, routing, sync, UI) — owner: environment A
WowTogether_QuestData/       data add-on (unchanged)
WowTogether_DungeonData/     data add-on (unchanged)
WowTogether_ProfessionData/  data add-on (unchanged)
WowTogether_Gold/            gold module — owner: environment B
  WowTogether_Gold.toc       ## LoadOnDemand: 1, ## Dependencies: WowTogether,
                             ## SavedVariables: WowTogetherGoldDB
  GoldPrices.lua GoldObservations.lua GoldValue.lua GoldSuggest.lua GoldUI.lua
  GoldSeedData.lua           promoted observations with provenance
tools/                       repo tooling (build_release.py, tests, data pipeline) — owner: A
  gold/                      gold pipeline: import_priors.py, ingest/promote extensions, tests — owner: B
```
Environment B edits only `WowTogether_Gold/` and `tools/gold/`.
Environment A edits everything else, including `tools/build_release.py`
(which must learn the fifth folder) and `tools/boundary_check.py`. Cross-boundary changes go through
the interface below and are made by A on request (a GitHub issue with
the exact function signature wanted).

## 2. Interface the core exposes (stable, versioned `ns.GoldAPIVersion = 1`)
Core provides, for the module to call:
- `ns.RegisterModule(name, {tab = {title, render}, settingsGroup, slash, probe})`
  — registers a Hub tab, a Settings group, a `/wt gold …` handler and a
  probe section. Core renders; the module supplies content.
- `ns.FindTravelPath(origin, goal, useFlights)`, `ns.TravelPointDistance`,
  `ns.PlayerPoint`, `ns.TrailLoop(points)` (TSP over proven ground;
  **new**, A implements) — routing.
- `ns.RouteCostModel()` — the cost model (brief 03).
- `ns.PushGuideStop(stop)` / `ns.ClearModuleStops(name)` — a module may
  add stops of kind `farm` to the live route; the HUD renders them with
  the icon table (`ns.STEP_SYMBOLS.farm` added by A).
- `ns.RegisterSyncKind(letter, handler)` — reserves a message kind. **Gold
  reserves `M`.** Core refuses duplicates at load.
- `ns.CatalogueQuest`, `ns.catalogue.*` read access; `ns.ReadPublic`,
  `ns.Public`, `ns.GuideInteger`, `ns.SafeTitle`, `ns.Option`,
  `ns.SetOption`, `ns.Print`, `ns.On` — utilities.
- `ns.ResearchExportHook(fn)` — the module appends its event kinds to
  `/wt research`.

### Loading and handoff
`WowTogether_Gold` is a separate load-on-demand addon, so its private addon
namespace is not the core's `ns`. After the core loads, `ModuleAPI.lua`
publishes `_G.WowTogetherGoldAPI`, a limited proxy containing the §2 surface.
Each Gold Lua file begins:

```lua
local addonName, private = ...
local ns = _G.WowTogetherGoldAPI
```

The first loaded Gold file checks `ns` and `ns.GoldAPIVersion` before
registration, and prints a clear disabled message if the API is missing or
too old. Gold never uses `_G.WowTogetherSharedNamespace`; that short-lived
handoff belongs to the data add-ons. `tools/build_release.py` checks the
limited handoff header before packaging Gold. The proxy exposes only the
listed root fields, and only `Price`, `Suggestions` and `SessionCard` can be
published through `ns.Gold`. `ns.catalogue` is live core data and is for
reading only.

For v1, `settingsGroup` is `{title, description, entries, get, set}`; entries
are `{key, label, help, default, choices?}` and Gold keys begin with `gold.`.
The `get` and `set` callbacks use `WowTogetherGoldDB`, keeping Gold settings
in the Gold addon's own saved variables. `tab.render(page)` draws in its
provided page; `slash(text)` receives the text after `/wt gold`; and
`probe(output)` writes lines to the Gold diagnostics section.

`TrailLoop(points)` returns a closed `{points, legs, seconds}` route or `nil`
if the walking route cannot be completed. It uses exact route ordering for
up to ten points and a bounded nearest-neighbour ordering for 11–24 points.
`PushGuideStop(stop)` requires a registered `stop.module`, `kind = "farm"`,
and a valid map point; `ClearModuleStops(name)` removes that module's stops.
`RegisterSyncKind(letter, handler)` calls `handler(message, sender)` only
after core packet validation; the handler returns an accepted boolean and
optional reason. `ResearchExportHook(fn)` calls `fn()` during manual export;
the hook returns an array of event tables with an `event` string.

The module must not touch `ns.db`, `ns.char`, `Sync.lua` internals,
frames it did not create, or any `ns.*` not listed here. A lint in
`tools/boundary_check.py` (created by A) greps the module for forbidden
references and fails the PR.

## 3. What the module exposes to the core
- `ns.Gold.Price(itemID)`, `ns.Gold.Suggestions(filters)`,
  `ns.Gold.SessionCard()` — read-only; the core may show the price in
  item tooltips later. Nothing else.

## 4. Settings, saved variables, probe
- Settings: one group "Gold" via `RegisterModule`; keys prefixed `gold.`.
- Saved variables: `WowTogetherGoldDB` only (account-wide; per-character
  state, if any, under `WowTogetherGoldDB.characters[name-realm]`).
- Probe: one section "Gold" via the registration; no edits to
  `Core.lua Diagnostics`.

## 5. Branching and merging
- `main` is always releasable. A works on `core/<topic>` branches, B on
  `gold/<topic>` branches. Squash-merge via PR.
- PR gate for both: the test runner in `tools/`, `tools/boundary_check.py`,
  and `tools/build_release.py` producing the zip.
- Interface changes: A bumps `ns.GoldAPIVersion`; B's module checks it
  at load and disables itself with a chat line if too old. Never a
  silent partial load. Until `ns.GoldAPIVersion` exists on `main`, B does
  not create a TOC or register anything (see §7).
- Release: one TOC version for the core; the module carries its own
  version and the minimum core version it needs
  (`## X-WowTogether-Min: 0.8.110`). `tools/build_release.py` learns the
  fifth folder (A).
- Conflicts are a process smell: if two PRs touch the same file, the
  seam is wrong — fix the seam (move the function behind the interface),
  do not resolve the conflict by hand twice.

## 6. Working agreement for environment B
- Read GOLD_FARMING_DESIGN.md, CODEX_GUIDE_QUALITY.md §4 (research
  protocol) and §6 (change discipline), CODEX_STEP_TEXT.md.
- Every rate, price and suggestion carries provenance and a sample
  size; the UI never shows a number without its confidence.
- No scraping drop rates; observations only. Licenses noted before import.
- Tests in `tools/gold/tests/` with a harness that replays loot and cast
  events; a PR without a test for the changed behaviour is not merged.
- A lint in `tools/boundary_check.py` (A creates it) greps the module for
  forbidden references and fails the PR.
- Weekly: `ingest → promote → GoldSeedData.lua` with the observer count
  in the changelog.

## 7. Order of work across the two environments
The §2 interface may be written by **either** environment, but always as a
standalone PR merged before any module code:
- a new file `WowTogether/ModuleAPI.lua` holding exactly the §2 functions,
  one TOC line, the fifth folder in `tools/build_release.py`, and
  `tools/boundary_check.py`; tests for each function;
- no edits to other core files beyond the hooks ModuleAPI registers
  through; no gold-specific logic in it;
- reviewed by the core owner before merge. After merge the file belongs
  to A; B requests changes by issue.
When A is busy (e.g. the sync hotfix), B writes this PR on a branch
`gold/module-api`. Until it is on `main`, B's other work is
**load-independent** only:
- `tools/gold/import_priors.py` (brief 13b) with tests and notices;
- `WowTogether_Gold/GoldPrices.lua` data model as pure Lua with harness
  tests — no TOC, no registration, nothing the client loads.
Then B:
1. Skeleton: TOC, `RegisterModule` call, empty Gold tab, probe section,
   `boundary_check.py` passing, module in the release zip.
2. Brief 12 (prices) with the TSM bridge behind a feature probe.
3. Brief 13 (observations) recorders and the `M` share kind.
Only then the value model: numbers without data are noise.
If B finds a missing core function, it stops and reports the signature
it needs — exactly what happened on 2026-11-09 — rather than adding it.
