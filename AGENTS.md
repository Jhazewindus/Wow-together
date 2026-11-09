# Brief — Project agents for Wow Together (AGENTS.md + .codex/agents)

Goal: make the process we already run by hand (brief → implement → test →
review → scribe → release) something Codex orchestrates itself with narrow
subagents, in parallel where file ownership allows. Applies to both
environments; B gets the same agents with the Gold boundary baked in.

Validate every file below against the current schema at
https://developers.openai.com/codex/subagents before relying on it: the
shape is right, individual field names may have moved. Project agents load
only for a trusted repo.

---

## 1. `AGENTS.md` (repo root) — the standing rules, finally where Codex reads them

```md
# Wow Together — how work is done here

## Ground rules
- One brief per change (`docs/briefs/`). Read the brief, then only the
  files it names. If you need another file, stop and say which and why.
- Data over code: a correction with a source beats a rule; a rule beats a
  special case; a special case for one quest ID in guide code is rejected.
- Never reassign an `ns.*` function defined in another file. Extend through
  `ns.hooks`. Never edit generated Lua (`*Data.lua`, `QuestCatalogue.lua`);
  edit the JSON inputs and rebuild.
- Every client read goes through `ns.ReadPublic`; every optional API is
  feature-detected and reported in `/wt probe`.
- A per-record function may not call a per-guide function (see
  PERFORMANCE.md). Add a timing test when touching a policy loop.
- Player-facing text follows docs/CODEX_STEP_TEXT.md: verb first, no addon
  vocabulary, no hedges, no reason codes on cards or tooltips.
- Every PR adds exactly one `changes/<branch>.md` fragment with a release-name
  heading, `For players` (≤3 lines), `Please check` (≤3 items), and developer
  notes; use `internal: true` when there is no player-visible change. PRs never
  edit the TOC version or `CHANGELOG.md`.
- Release versions come from the last `v*` tag. CI stamps the version and
  release name into packaged TOCs only; `CHANGELOG.md` is frozen at 0.8.110.
- Branches `core/<topic>` (A) and `gold/<topic>` (B); squash-merge via PR.
  You never merge. Build and release happen in CI; never build zips by hand.
- Module boundary: docs/MODULE_BOUNDARY.md. B edits only `WowTogether_Gold/`
  and `tools/gold/`; A edits everything else. A missing core function is a
  report, not a patch.

## Verify before claiming done
`python3 tools/syntax_check.py`, the host test suite, `python3
tools/boundary_check.py`, `python3 tools/build_release.py --output /tmp/b`.
Say "needs play-test" or "checks sufficient" in the PR.

## Orchestration
For a brief: implementer → tester → reviewer → release-scribe, in that
order; stop at the first failure and fix. Two briefs may run in parallel
only when their file lists do not overlap (use the symptom→file table in
docs/CODEX_APP_REDESIGN.md §1 and the module boundary). Use
data-researcher for any fact you do not have; never invent coordinates,
levels, prerequisites or drop rates. Use perf-auditor on any change to
GuidePolicy, GuideOptimizer, QuestFlow, Routes, TravelNetwork or Sync.
```

---

## 2. Agents — `.codex/agents/*.toml`

Common shape (adjust names to the current schema):
```toml
name = "reviewer"
description = "Read-only review of a PR against its brief and the repo rules."
model = "<strongest available>"
model_reasoning_effort = "high"
sandbox_mode = "read-only"
developer_instructions = """
...role text...
"""
nickname_candidates = ["Argus", "Lens", "Scribe"]
```

### reviewer (read-only, strong model)
Checks: only the brief's files changed; no `ns.*` reassignment across files;
no forbidden strings (list in docs/CODEX_UI_PRESENTATION.md §6); exactly one
valid branch fragment and no TOC version/`CHANGELOG.md` edits; tests exist for
each behaviour named in the brief; module boundary respected; player text
rules. Output: the checklist with pass/fail per line and file:line for each
fail. Never edits, never suggests "acceptable for now".

### tester (sandboxed commands, no file edits)
Runs the four commands from AGENTS.md plus any test the brief names.
Reports each failure with the first assertion message and file:line. If a
test is missing for a behaviour in the brief, reports that as a failure.

### perf-auditor (read-only)
Finds per-record loops calling per-guide functions (`levelingValue`,
`LevelingQuestEnabled`, record iterations in builders) and functions
without a memo that are called inside them; runs timing tests; reports the
call chain like the watchdog trace. Model: strong, effort high.

### lua-implementer (edits allowed)
Implements one brief. Developer instructions: "Edit only the files the
brief names. Write the test first when the brief names a behaviour. Follow
AGENTS.md. When blocked by a missing function or fact, stop and report the
exact signature or fact needed." Model: strong for routing/sync/policy
briefs; a cheaper model for mechanical ones (the orchestrator picks).

### ui-implementer (edits allowed, UI files only)
Files: UI.lua, Navigation.lua, StandaloneArrow.lua, GuideQuestList.lua,
Config.lua (presentation), GuideText.lua, SuggestionChips.lua. Builds
behind `uiNext` per docs/CODEX_APP_REDESIGN.md; keeps frame names; follows
the icon table and copy rules; pastes three before/after cards in the PR.

### data-researcher (read + web, no Lua edits)
Follows docs/CODEX_GUIDE_QUALITY.md §4: source ranking, capture with
provenance, corrections with a source sentence, dead ends recorded in the
source queue, licence check before any import. Writes only under
`data-tools/` (or `tools/`) JSON inputs; never Lua. Reports facts with
confidence and source.

### release-scribe (edits: one `changes/<branch>.md` file only)
Writes a release-name heading, `For players` (plain language, ≤3 lines),
`Please check` (≤3 items), and developer notes from the diff and brief. For
no player-visible change, write `internal: true`. Never edits the TOC version
or `CHANGELOG.md`.

### gold-worker (environment B only; edits WowTogether_Gold/ and tools/gold/)
The lua-implementer with the boundary baked in: any reference outside the
public `WowTogetherModuleAPI` is a stop-and-report. Runs
`tools/boundary_check.py` before claiming done.

---

## 3. Skills (optional, `.agents/skills/` or `.codex/skills/` per current docs)
- `new-brief`: scaffold `docs/briefs/NN_<topic>.md` with the four blocks
  (why / what changes / tests / acceptance).
- `pr-review`: run reviewer + tester + perf-auditor and assemble one report.
- `release-notes`: run release-scribe on the current branch.

---

## 4. What not to do
- No agent with broad edit rights and a vague job ("improve the addon").
- No parallel implementers on overlapping files; the boundary and the
  symptom→file table decide.
- No agent that merges, tags, builds zips or posts to Discord; CI does that.
- Don't spawn subagents for one-line fixes; the overhead is real.

## 5. Acceptance
- `codex` in the trusted repo lists the custom agents; a prompt "review PR
  #N" runs reviewer+tester and returns the checklist without edits.
- A brief with two disjoint file lists runs two implementers in parallel
  and one tester afterwards.
- reviewer rejects a PR that reassigns an `ns.*` function, lacks one valid
  fragment, edits the TOC version/`CHANGELOG.md`, or omits `For players`; tester
  rejects one whose timing test fails.
