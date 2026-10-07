# Personal crafting guides

WoW Together 0.8.55 supports Alchemy, Blacksmithing, Enchanting,
Engineering, Leatherworking and Tailoring. Profession cards use the compact
browser grid. Learned professions come first when the client identifies them;
opening the profession window supplies recipes and can identify a profession
when the primary-profession APIs are unavailable. These guides are personal.

Choose a profession, preview its path, select a skill goal and Start crafting
guide. The same small guide window used for leveling and dungeon preparation
now displays a profession step. It directs learning/rank training to a named
friendly trainer, shows a next-batch material list and suggests what to craft.
Next recipe tries another option at the current skill. Materials opens the
shopping list, with Next batch and To skill goal. Refresh rereads available profession data. Stop and Exit use
the existing guide behavior; the profession/goal and unfinished batch resume on login.
Starting a guide with its profession window closed offers **Scan current
progress**. A manual click attempts `C_TradeSkillUI.OpenTradeSkill(skillLineID)`;
availability is probed and its Forever behavior still needs testing. If it cannot
open, open the profession window yourself. Recipe events refresh the guide;
opening is not treated as proof that data loaded. **Later** keeps the guide running
from available data. **Scan guide** offers another fresh read after training.
Loading reads retain confirmed learned recipes, and preparation crafts use the
opened client's reagent schematics too. Gathering/training steps show estimated
craft counts and the actual skill milestone. `/wt probe` includes learned status,
refresh state and up to eight material requirement/owned/missing counts.

No skills, recipes or purchases are performed automatically.

## What decides the next craft

- Profession **skill**, not character level, determines eligible recipes.
  Character level gates rank training. Training and recipe acquisition are
  separate steps; reaching a cap does not count as finishing a higher goal.
- Every active batch has a skill milestone: the next known recipe unlock,
  difficulty threshold, rank cap or chosen goal. Buy/gather work targets at most
  five skill points before that milestone. The approximate quantity uses this
  recipe's current estimated skill-up chance and native points per successful
  skill-up, rather than a fixed craft count. As soon as bags cover some crafts,
  show that affordable count: four Light Leather can become four Light Armor
  Kits without buying the rest. The scarcest required reagent limits the count.
  Preparation crafts also use partial stock; available final ingredients take
  priority. The full milestone estimate is retained separately. Shopping amounts
  use `~` for estimates; crafting instructions say when to stop at the skill target.
  Failed skill-ups leave the gap unchanged; fresh skill/color reads recalculate
  the amount. Reaching the milestone ends the step even if estimated crafts
  remain. Personal professions/batch-size settings are removed. Actual skill and
  next work target stay visible during crafting, gathering and training.
  Reaching skill 11 after ten successful skill-ups from
  skill 1 is normal; further crafts remain useful until a later milestone.
- Matching public player `UNIT_SPELLCAST_SUCCEEDED` casts trigger a fresh skill/
  stock read, including crafts made while gathering materials. Successfully
  produced items do not imply skill gains. Bags cover only the work still needed
  from actual skill; consumed ingredients cannot count as owned. Preparation
  crafts update stock and actual skill without pretending the final recipe was
  crafted. The profession, goal and milestone resume across reloads.
- Recipes are reassessed when skill, stock, recipes, cap/goal or prices change.
  Fresh auction prices can replace an unfinished batch; actual skill
  and bags retain completed work. Fresh primary skill-line reads take priority over
  an older recipe-window skill snapshot. Recipe colors stay scoped to their
  snapshot skill. Explicit Next recipe still changes the active recipe.
- Public learned recipes, current skill-up colors and material schematics from
  the opened client window take priority over the reference. Stale colors are
  not applied to a newly changed skill. Grey or explicitly non-skill-up recipes
  are excluded. Unreadable native material data pauses the craft instruction.
- Without observed prices, a resource-count heuristic balances material use,
  estimated skill-up reliability, preparation work and a small training penalty
  amortized across a batch. Bag stock can favor a recipe already affordable.
  This does **not** establish the cheapest gold cost.
- Manual AH commodity/item-auction results and ordinary merchant listings can provide prices
  with a six-hour market-scoped cache. Missing prices stay unknown; vendor stack prices are divided
  by purchase quantity. Extended-currency items are excluded. No auction search,
  buying, crafting or training is automated. Vendor names are retained for the
  material list; there is no complete independent vendor database.
- Orange is estimated at one skill gain; live yellow/green use 0.65/0.25 chance
  estimates. Reference thresholds use a linear yellow-to-grey estimate. These
  are planning approximations, **not a verified Forever skill-up formula**.
  Extra skill-ups reported by the client are considered for next-craft scoring.
- Same-profession intermediates expand into preparation crafts when a known or
  trainer recipe can make them and no direct purchase price is known. Output
  quantity and a shared stock ledger prevent double-spending owned reagents.
  Expansion is bounded and cycle guarded. Tools/rods/workstations still need
  checking in the actual recipe window; general reminders remain visible.
- Vendor/drop/reputation/favor/unknown-acquisition recipes enter recommendations
  only after the client confirms they are learned. Source faction restrictions
  gate acquisition; an actually learned recipe overrides that reference gate.
  Unknown skill thresholds cannot become invented eligibility.

The future path is an independently generated, approximate dynamic-programming
path through skill states. It estimates resources/crafting work without spending
current inventory repeatedly. It is a preview, not a commitment to those recipes;
actual next batches adapt as skills and bags change. It does not infer vendor
stock, recipe drop rates or precise travel time for each craft. New intermediate
recipes absent from the snapshot can be suggested from live public schematics,
though their later skill thresholds remain unknown. Craft counts and future
costs are estimates; actual progress drives completion.

## Materials and auction searches

Next batch lists remaining materials for current work. When crafting is already
affordable, it shows the ingredients for that craft portion; otherwise it forecasts
the small buy/gather step. Smaller purchases can immediately unlock crafting.
To skill goal estimates
the preview path, rounds expected crafts up and carries one stock ledger through
its steps. Earlier planned outputs feed later recipes. Intermediate purchases
are compared with known raw ingredient costs plus preparation time. Unknown
prices retain a reference fallback. Skill-up variance, preparation skill gains
and future recipe choices can change totals; buy for the next batch first.
Partial paths or unreadable bags are labelled incomplete. Calculations yield
and cancel when superseded.

The auction-house panel sits to the left with goal selection and expandable
recipe boxes in planned crafting order. Each shows approximate crafts, skill
range, required intermediate preparations, missing Buy amounts and estimated
cost. Per-recipe Search uses that part's amount. Boxes and the aggregate share
one ledger, so bag stock and earlier planned outputs are not deducted twice.
These are estimates for sequential crafting, not independently funded plans.
After buying/crafting, fresh skill and bag reads reassess the remaining work.
The panel uses the active
crafting guide, or the open profession materials window when no guide is active.
Only the addon's panel is positioned or moved; Blizzard's anchors and parent
remain untouched. Small-screen placement/scale needs beta tests.

After a material Search, selecting the matching commodity can fill its public
buy quantity once. The supported native display must be visible, unprotected,
have loaded results and still have the initial quantity of one. Fresh bag
additions reduce the request; the native setter enforces available stock.
Manual quantity edits are retained. The request expires after a minute and
clears on close, new searches/scans or guide/goal changes. Unsupported controls
and non-commodity listings keep manual quantities. Nothing buys automatically.
The public `GetItemID` / `SetQuantitySelected` / `GetQuantitySelected` contract
was checked against Blizzard's
[commodity display source](https://github.com/Gethe/wow-ui-source/blob/live/Interface/AddOns/Blizzard_AuctionHouseUI/Shared/Blizzard_AuctionHouseCommoditiesBuyFrame.lua).
Its presence and behavior still need Forever beta testing.

**Scan auction house** explicitly starts a bounded queue for this profession's
selected goal. It includes viable learnable recipe alternatives and ingredients
of intermediate preparations: pricing only the old selected path cannot compare
alternatives. It never scans the whole AH. Modern APIs are capability-probed:
`MakeItemKey`, `SendSearchQuery`, throttle readiness and item/commodity result
events. Queries use exact IDs, one pending request, >=1 second pacing, up to
three result pages per item, a five-second metadata wait, a 20-second response
timeout and a bounded busy
wait. Price sorting is used when its enum is exposed. No API success return
alone proves delivery; match the response to the pending item. Unknown/private
and timed-out replies don't become zero prices. Missing support leaves manual
Search buttons available. Native exact-query behavior still needs Forever tests.
Item-name requests and rejected queries are guarded. A response watchdog is
installed before the query and survives panel refresh errors; item details
never loaded and silent queries are skipped with a count. Current/failed IDs
and reasons stay in diagnostics, not the normal shopping UI. A new explicit
scan can retry unresolved metadata; older cached prices are retained on failure.

Stop scan, closing the AH, native browsing, a manual material search, or changing
the selected profession/goal cancels further queries. Combat pauses new queries;
public result reads can finish and queue planning after combat. Closing/switching
also cancels stale forecasts. Searches and scans never buy, bid, train or craft.

Quotes persist for this character's realm/region/faction/build, expiring after
six hours. A missing server clock or market identity prevents persistence.
Initialization waits for known faction, so early login reads don't erase a valid
cache. Saved quotes are bounded to 256 items, each up to 40 price/quantity tiers.
Native reads inspect up to 200 result rows; item/legacy buyouts are divided by
stack size, bid-only and private prices are rejected, and owned/account offers
are excluded where public ownership data identifies them. Legacy manual searches
read up to 50 listings. Full empty results invalidate earlier prices. Books
weight cost by requested quantity when observed supply covers it; otherwise
price remains an estimate. A saved snapshot isn't a guarantee of availability.

New quotes immediately reconsider unfinished crafts and the full goal preview.
Fully priced choices/paths take priority over unknown-price heuristics after
market observations. The balance compares copper/100 with expected crafting
seconds; cached `C_Spell.GetSpellInfo(...).castTime` supplies craft time, with a
four-second estimate when absent. Preparation time is included. This is a
cost/time heuristic with estimated skill-up probabilities, not proof of the
cheapest possible shopping route or future trainer/recipe availability. Actual
skill continues to determine milestones and guide progress.

The native API contracts were checked in Blizzard's generated Mainline
[AuctionHouse documentation](https://github.com/Gethe/wow-ui-source/blob/live/Interface/AddOns/Blizzard_APIDocumentationGenerated/AuctionHouseDocumentation.lua);
presence and return behavior must still be retested in the current Forever beta.

Recipe training uses the current cap; reaching the skill requirement for a later
rank alone does not force a distant rank-training detour. If the chosen trainer
also supports an unlocked rank needed by the goal, the step explains that useful
combined visit. At the actual cap, it explains why raising the cap is necessary.
Positive available/used offerings from an opened profession trainer are saved
for this character and client build (up to 64 trainer observations). Matching
recipes or explicitly identified ranks override older trainer facts. Both public
trainer return shapes are supported; localization/cache gaps and unavailable/
private services cannot establish a new rank. No trainer filters or purchases are
changed. Approximate observed positions use the player's location at the NPC.

Goals are 75, 150, 225 and 300. The compared beta guides currently document
1–225 leveling; a 300 preview is **not proof of beta rank availability**.
Training advice must be checked against the current build/trainer. Native skill
caps and current progress control the active guide. Missing paths stay pending.

## Sources and reproducibility

Captured 7 October 2026. Compared all five supplied references:

- https://www.wowhead.com/forever/guides/professions
- https://mobalytics.gg/wow-forever/professions
- https://www.wow-professions.com/forever
- https://classicwowforever.com/professions/
- https://www.icy-veins.com/wow-forever/professions-overview

`ProfessionData.json` records exact fact-page URLs and SHA256 checksums. Its
2,009 recipe records retain IDs, names, native icon filenames, reagents, output
quantities when reported, skill/color thresholds, acquisition category, faction
and numeric trainer fee when reported. Its 150 trainer locations and rank
requirements come from the six Icy Veins profession pages. No guide sequence,
editorial instructions, website code, screenshots or external artwork is copied.
Standard healing potion recipes moving into First Aid is one reason not to reuse
a Vanilla profession path; Cooking/First Aid are outside this release's six
primary crafting guides. Existing personal profession quest helpers remain.

Save the six recipe pages as `facts-<profession>.html` and Icy Veins pages as
`icy-<profession>.html`, then run:

```sh
/workspace/.wow-together-tests/bin/python tools/import_professions.py --cache /path/to/pages
```

The importer reads structured factual recipe rows and trainer/rank tables without
executing page scripts. It fails on missing/ambiguous tables. Each profession's
nested details remain packed until accessed; the six browser cards don't unpack
all recipes at startup. Recipe and bag events coalesce; preview calculations
yield between small batches and stale previews are cancelled.

`/wt probe` lists the available recipe APIs, GetProfessions/GetProfessionInfo,
merchant readers and data compartment counts. Primary-profession IDs are the
seventh GetProfessionInfo return; all used public fields are checked. Saved
skill/recipe IDs are a last-known fallback and colors are never persisted as live
facts. Retest the native APIs and six professions on the build being played.
Host Lua 5.1 checks establish algorithms/UI logic, not beta API behavior.
The documented spell-success event is optional and guarded during registration;
secret unit/cast/spell fields are ignored. `/wt probe` reports registration and
matching casts observed. Retest delivery and recipe spell IDs on Forever; without
matching public events, skill and bag events still drive the plan, but the count
of successful craft casts may be incomplete. No crafting action is performed by
the addon.
