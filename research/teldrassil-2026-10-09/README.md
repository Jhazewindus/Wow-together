# Teldrassil factual review — 9 October 2026

Refreshed addon 0.8.61 at guides/coverage `828b1bd560031f8d811367be1f277c37008ad980`; main `09155ca265278572649a3529b8ce7ea1b4eb8431`. The supplied 0.8.59 baseline is historical. This review inventories 62 direct category records, 61 distinct compiled IDs, both Alliance chapters (48/26 quests, 157/84 actions), class continuations and cross-zone destinations. Welcome! and level-60 Tyrande and Remulos are retained outside these compiled chapters. Horde profiles expose no Teldrassil guide; Night Elf warrior/hunter/priest/druid and Skyborn profiles retain both chapters. Existing class settings and identity gates are unchanged.

Thirteen guarded data corrections distinguish supplied inputs from filled outputs, replace phial gathering with explicit use at existing moonwells, remove redundant Timberling Seed/looted Heart farming, interact with Denalan's Planter, retain three Forever delivery inputs, and remove the necklace container from Ferocitas hand-in requirements. Seven Mystic kills, actual necklace acquisition, jewel requirement and every actual parent hand-in remain. No supplied count is fabricated when unpublished. Ban'ethil escape work is now explicitly incomplete; its path/trigger is unknown.

## Evidence and limits

[pinned-facts.json](pinned-facts.json) retains selected literal fields, per-field origin, entity relations and all 24 verified source hashes from [QuestieDB revision e0a6eaa](https://github.com/Questie/QuestieDB/tree/e0a6eaa86f181ac99262e34126bcd2ed1a1712d6). [source-joins.json](source-joins.json) records exact name/level/minimum matches and decisions. Converted-baseline facts are distinguished from beta observations/deltas. Existing captured positions are preserved. No third-party quest prose, engine, or routing code is copied. The verified cache remains available; repeated web denials in earlier research prevent claims of newly checked comments/forums or exhaustive public-source access.

Pickup and return gaps for 934 remain. Objective gap 2459 remains, and newly identified escape gap 99053 raises the compiled distinct gap union from two to three. No gap was closed. Existing uncertain pickup/quantity lists remain empty; this does not establish actual beta offers or supply counts. Crown 935's alternative 934/7383 parent remains despite the pinned 7383-only field. Missing narrative dependencies in the new aid chain are not inferred from titles. [coordination-proposal.json](coordination-proposal.json) records facts and shared behavior requiring evidence/review.

## Full-scope route review

Both orders are repriced with identical corrected facts in [repriced-flow.json](repriced-flow.json). All eight starting states retain valid actions, parent hand-ins and onward endpoints. At 1–10, estimated distance falls 98,930.96 to 74,343.33; log peak rises 11 to 12, uncertain legs 31 to 32, and work rewards are delayed for 923/930/931/2498/99053. The optimization guard therefore says REVIEW REQUIRED. At 11–20, distance falls 85,114.25 to 81,954.19 with unchanged peak 6/uncertainty 22/reward timing; four states pass. These are source corrections and host estimates, not a terrain-optimal route claim. Shared engine/routing/eligibility/UI remains unchanged.

## Player checklist

- Start a fresh Night Elf and applicable Skyborn character; inspect both chapters and class setting on/off. Follow starter-to-Dolanaar progression, scan/reload/zone-entry and fixed automatic progress.
- Hand in the Seed, Heart and real prerequisite quests before follow-ups. Confirm no duplicate post-acceptance farming; loot Blackmoss's starter first. Interact with Denalan's Planter.
- Use each empty phial at its own moonwell, retain filled output and verify actual hand-in. Record exact offers for 934/7383/935 rather than treating matching names as interchangeable.
- Kill seven Mystics, loot Ferocitas's necklace and open it for the jewel. Confirm the necklace is not independently required at hand-in; inventory opening remains an unresolved guide stage.
- Verify Eralya/Byancie salve delivery, six fronds/water/vial preparation and actual unlock hand-ins. Escort Lynessa through Ban'ethil; record path, completion trigger and scan/reload behavior. Accepted or deferred unfinished escape work must not report Guide complete.
- Test Rageclaw kill followed by charm use, Mist escort adjacency and cave approaches. Confirm Darnassus interiors, portal and Rut'theran departure/boat arrival separately; graph points do not prove roads, ship schedules or unlocked flight connections.
- Keep group/elite work visible and optional. Check higher-level remaining quests, temporary deferrals returning after an actual offer, and manual skips staying personal.

Host checks cannot establish native beta completion, offer restrictions, map rendering, safe terrain or transport. This is a review candidate; no release publication.

Validation: all 115 zone regressions (including six focused Teldrassil checks), 122 transport/class/offer/session checks and 49 importer/source checks pass; all 86 TOC Lua files compile under Lua 5.1/interface 16001. Guarded corrections reapply with no changes, and entity/world-completion/XP data remain byte-equivalent as parsed. Exact logs accompany this review. No new full-suite run is claimed; the previously documented historical catalogue fingerprint failure remains separate.

Global regeneration changes only the two Alliance Teldrassil audit rows: 152 sections / 11,829 points, 33 recorded gap-free sections and 374 unresolved ordinary records.
