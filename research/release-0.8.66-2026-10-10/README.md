# Native Forever finder integration — 10 October 2026

## Reports and evidence

The user confirms 0.8.65 role/class filters work but requests in-header controls
and filtering of Blizzard's own Players list. Their supplied 0.8.65 probe on
Forever 1.60.1 / build 70291 reports RFC instance 389, matching world-map ID 389,
but no usable public X/Y and no matching native player floor. That distinguishes
instance recognition from position availability. No NPC or entrance point can
substitute for the missing live position.

[HiddenMaps](https://www.curseforge.com/wow/addons/hiddenmaps) explicitly says:
“Live player tracking is available in supported pre-instance areas, but not
inside the instances themselves. Dungeon interiors currently use static maps.”
Its code was not copied. Its description does not establish a missing API path
for RFC interiors. The old pre-entrance 213 map lookup is not an interior floor.

## Native finder interface facts

Continue using [Gethe/wow-ui-source revision
9465cb273b5513495d8ecc12fbb19930dd6b8957](https://github.com/Gethe/wow-ui-source/tree/9465cb273b5513495d8ecc12fbb19930dd6b8957),
particularly Interface/AddOns/Blizzard_GroupFinder_VanillaStyle/
Blizzard_LFGVanilla_Browse.lua and Classic/Blizzard_LFGVanilla_ParentFrame.xml.
The implementation is independent; these are frame/provider/API facts:

- LFGBrowseFrame has CategoryDropdown, ActivityDropdown, ScrollBox, results,
  selectionBehavior and UpdateResults/UpdateButtonState. The native sorted
  result IDs stay in results. Solo/Group divider IDs are 1/2.
- Native trees contain dividerType headers and index/resultID/category rows.
  Actual native row selection and invitation use resultID. Keep the original
  index and ID even after filtering; never rewrite C_LFGList return values.
- CreateTreeDataProvider and ScrollBox SetDataProvider accept that structure.
  Post-hook UpdateResults only invalidates addon state; an owned controller
  applies the filter later, outside the native call stack. Do not replace native
  UpdateResults, searches or action handlers. Defer changes during combat and
  reject protected/unsupported providers. All/All restores the original tree.
- Only solo Players are filtered; recruitment roles on Groups mean something
  different, and self-listings remain. Roles/classes must match the same player.
- Unsupported or private facts are not guessed. No automatic social actions.

## Review and limits

Tests test_0866.py exercise list intersection, original IDs/order, selection,
refresh, no idle rebuild, settings/tab changes, combat deferral, missing/private
facts, provider failure/protection, and the exact RFC nil-X/Y report. Existing
0.8.64/65 player adapters and secret-aura mitigation remain covered.
Live header layout, scrolling, context menus/invites and taint still need beta
verification. Host mocks are not proof that the current client permits every
unprotected provider mutation without downstream taint.

Guide branch commits through 53d5e12 are retained as research in merge 8e694cf.
Seven updates refresh audits only. Felwood/Feralas data candidates and their
candidate tests are explicitly deferred: their full-route guards fail reward
or difficulty preservation, and Felwood's short comparison is invalid with
changed endpoints. Shipped data/corrections/exclusions retain 0.8.65 contents.
Research coverage numbers refer to candidates, not a new coverage claim.

## Release validation

- New native-filter/RFC regressions: 17/17 pass.
- Retained 0.8.65 adapter regressions: 15/15 pass.
- 0.8.64, dungeon-player and Discord-release regressions: 42/42 pass.
- Final Winterspring audit regressions: 7/7 pass.
- All 88 TOC modules compile in Lua 5.1; interface remains 16001.
- Shipped catalogue, coverage, correction and exclusion files are byte-identical
  to 0.8.65. New branch research does not alter live quest data.
- ZIP integrity, matched version/docs and multipart dry run pass.
- The supplemental aggregate zone run lost its terminal result after session
  reconnection; it is not counted as a completed suite. Native beta checks remain
  in TESTING.md.
