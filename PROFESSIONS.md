# Personal crafting guides

WoW Together 0.8.36 starts with Alchemy, Blacksmithing, Enchanting,
Engineering, Leatherworking and Tailoring. Profession cards use the compact
browser grid. Learned professions come first when the client identifies them;
opening the profession window supplies recipes and can identify a profession
when the primary-profession APIs are unavailable. These guides are personal.

Choose a profession, preview its path, select a skill goal and Start crafting
guide. The same small guide window used for leveling and dungeon preparation
now displays a profession step. It directs learning/rank training to a named
friendly trainer, shows a next-batch material list and suggests what to craft.
Next recipe tries another option at the current skill. Materials opens the
shopping list. Refresh rereads available profession data. Stop and Exit use
the existing guide behavior; the profession/goal checkpoint resumes on login.
No skills, recipes or purchases are performed automatically.

## What decides the next craft

- Profession **skill**, not character level, determines eligible recipes.
  Character level gates rank training. Training and recipe acquisition are
  separate steps; reaching a cap does not count as finishing a higher goal.
- Public learned recipes, current skill-up colors and material schematics from
  the opened client window take priority over the reference. Stale colors are
  not applied to a newly changed skill. Grey or explicitly non-skill-up recipes
  are excluded. Unreadable native material data pauses the craft instruction.
- Without observed prices, a resource-count heuristic balances material use,
  estimated skill-up reliability, preparation work and a small training penalty
  amortized across a batch. Bag stock can favor a recipe already affordable.
  This does **not** establish the cheapest gold cost.
- Manual AH commodity results and ordinary merchant listings can provide prices
  for the session. Missing prices stay unknown; vendor stack prices are divided
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
