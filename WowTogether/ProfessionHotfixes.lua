local addonName, ns = ...

-- Blizzard's post-launch hotfixes that change bundled profession facts.
-- The recipe reference was captured on 7 October 2026, before launch; these
-- are the changes since then that Blizzard has published and that move a
-- threshold or a reagent count. The client's own recipe window still
-- overrides the reference for anything it shows, so this only matters for
-- recipes not learned yet and for the path beyond the current step.
--
-- Source: "WoW: Forever Hotfixes" (Blizzard), entries of 10 and 11 November 2026.
local HOTFIXES = {
    [164] = { -- Blacksmithing
        -- Coarse Grinding Stone now provides skill-ups to 90 (was 75).
        {name = "Coarse Grinding Stone", was = {grey = 75}, set = {grey = 90, green = 70}},
    },
    [197] = { -- Tailoring: five bags need one more bolt of cloth (and hold more).
        {name = "Green Woolen Bag", reagent = 2997, was = 4, now = 5},
        {name = "Red Woolen Bag", reagent = 2997, was = 4, now = 5},
        {name = "Green Silk Pack", reagent = 4305, was = 4, now = 5},
        {name = "Black Silk Pack", reagent = 4305, was = 5, now = 6},
        {name = "Red Mageweave Bag", reagent = 4339, was = 4, now = 5},
    },
}

local applied = {}

-- Applies each hotfix once per loaded reference, and only where the bundled
-- value is still the pre-hotfix one: a refreshed data file is left alone.
function ns.ApplyProfessionHotfixes(id)
    local facts = ns.ProfessionFacts and ns.ProfessionFacts(id)
    local list = HOTFIXES[id]
    if not facts or not list or applied[id] == facts then return 0 end
    applied[id] = facts
    local changed = 0
    for _, recipe in ipairs(facts.recipes) do
        for _, fix in ipairs(list) do
            if recipe.name == fix.name then
                if fix.set then
                    local stale = true
                    for key, value in pairs(fix.was) do if recipe[key] ~= value then stale = false end end
                    if stale then
                        for key, value in pairs(fix.set) do recipe[key] = value end
                        changed = changed + 1
                    end
                else
                    for _, material in ipairs(recipe.materials) do
                        if material[1] == fix.reagent and material[2] == fix.was then
                            material[2] = fix.now; changed = changed + 1
                        end
                    end
                end
            end
        end
    end
    ns.professionHotfixesApplied = (ns.professionHotfixesApplied or 0) + changed
    return changed
end
