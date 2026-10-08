# Combined guide-branch validation, 8 October 2026

Data tested at guides/coverage 309dc81b3e83a0b0db42da47ab3493e180ab65a1,
including main 09155ca265278572649a3529b8ce7ea1b4eb8431 / addon 0.8.61.
The isolated worktree is /workspace/Wow-together-guides; the main developer's
shared checkout remains unchanged. Subsequent final-documentation updates do
not change tested runtime, quest data, corrections or audit tooling.

The complete Lua 5.1 host suite runs **1,563 tests in 540.228 seconds**:
**1,562 pass; one fails**. The sole failure is
`test_0829.PackedDataTests.test_all_source_fields_match_pre_packing_fingerprints`,
field `catalogue`. The historical fixture is unchanged from main and its baseline
failure was already recorded by onboarding/integration reviews. The new catalogue
has researched changes; no historical digest is rewritten to conceal the failure.
All 64 zone regressions pass within this full run. All 86 TOC Lua files compile
under Lua 5.1/interface 16001. Entity data, world completion checks and XP baseline
compare equal to main. Exact tested source hashes remain unchanged through the run.

The global invariant audit checks **152 sections in 44 zone labels** and
**11,833 source points**. It retains **33 recorded gap-free sections** and
**390 unresolved ordinary quest records**. Endgame quarantine removes those
records from ordinary guide needs while retaining their unresolved facts in
Tanaris research. Hinterlands coordinates close, but all four chapters retain
prerequisite-review flags and are not certified source-gap-free. Count changes
are distinguished from route quality, complete source coverage and native play.

Whole-zone comparisons and player checklists accompany each zone review in
[research/README.md](../README.md). Swamp and Hinterlands preserve actions/endpoints
and unchanged same-facts metrics. Other zones retain concrete coordination items:
route/reward tradeoffs, a changed Horde Stranglethorn endpoint, Green Hills
completion dependencies, omitted useful dungeon/cross-zone handoffs, source-mask
conflicts and hidden single-quest elite chapters. No shared runtime routing,
eligibility, lifecycle or UI changes were authored by the guide agent.

PR #2 remains draft, guides/coverage → main. Native beta offers, item-use/testing,
actual hand-ins, persistence APIs, faction/class variants, escort recovery,
elevated approaches, entrances and personal transport access require the player
checklists. Host checks do not establish these facts or terrain-optimal routing.
No release bump, tag, archive upload or Discord message was published.

Reproduce from the worktree using the configured test environment:

```sh
/workspace/.wow-together-tests/bin/python tools/apply_quest_stage_corrections.py
/workspace/.wow-together-tests/bin/python tools/audit_quest_guides.py
/workspace/.wow-together-tests/bin/python tools/guide_source_queue.py
/workspace/.wow-together-tests/bin/python -m unittest discover -s tests -q
```

The correction command reports no changed records with these reviewed inputs.
The last command retains the documented historical fingerprint failure. Exact
run output, source hashes and structured results are alongside this document.
