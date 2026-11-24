local addonName, ns = ...

-- The skilling path: which recipe to craft at every skill point from where
-- the character is to the chosen goal, at the lowest expected cost.
--
-- What "cost" means here, per skill point gained:
--
--   materials   each reagent at the cheapest known way to get it: an auction
--               or vendor quote, or crafting it from its own reagents with a
--               recipe of the same profession (bolts, bars, stones, parts)
--   - resale    what a vendor pays for the crafted item (read from the
--               client, so Forever's reduced vendor prices are respected)
--   + time      crafting seconds, weighted by the player's preference
--   / gain      the chance of a skill point from this craft, plus the
--               points the intermediate crafts themselves are expected to
--               give (making Bolts of Linen Cloth levels Tailoring too)
--
-- and, once per recipe the character does not know yet, what it costs to
-- learn: the trainer's fee, and a visit. A recipe that is two silver cheaper
-- per point is not worth a three-gold training fee for five points; the plan
-- weighs that instead of looking at one skill point at a time.
--
-- Skill-up chance follows the recipe's colour thresholds from the game
-- files: certain below yellow, then falling in a straight line to nothing at
-- grey. Blizzard has not published the formula for Forever; this is the
-- Classic rule, and the client's own colours override it for the step being
-- crafted. Crafts are therefore expectations: every step also carries a
-- "safe" count that covers about 85 runs in 100.
--
-- Nothing here buys, trains or crafts. It only decides what to suggest.

local UNKNOWN_UNIT = 1000        -- stand-in copper for one reagent with no known price
local TIME_VALUE = {gold = 0, balanced = 100, speed = 1000}  -- copper a second of crafting is worth
local VISIT = {trainer = 20, vendor = 120}                   -- seconds a new recipe's errand is worth
local PERK = 1.10                -- Legacy perk "Working Overtime": 10% better chance of a skill point
local SAFE_Z = 1.04              -- about the 85th percentile of the crafts needed
local DEPTH = 2                  -- how deep intermediates are expanded

local sellCache, sellRequested = {}, {}

-- What a vendor pays for one of this item, in copper; nil while the client
-- has not loaded the item.
function ns.ProfessionSellValue(itemID)
    if not ns.GuideInteger(itemID) or itemID <= 0 then return nil end
    local cached = sellCache[itemID]
    if cached ~= nil then return cached or nil end
    local reader = C_Item and C_Item.GetItemInfo or GetItemInfo
    if type(reader) ~= "function" then return nil end
    -- The sell price is the eleventh return; ns.ReadPublic passes on only
    -- the first five, so this read is guarded here instead.
    local okay, _, _, _, _, _, _, _, _, _, _, price = pcall(reader, itemID)
    if okay and ns.Public(price) and type(price) == "number" and price >= 0 then
        sellCache[itemID] = price
        return price
    end
    -- Not loaded yet: ask the client for it once, so a later plan has it.
    if not sellRequested[itemID] and C_Item and type(C_Item.RequestLoadItemDataByID) == "function" then
        sellRequested[itemID] = true
        pcall(C_Item.RequestLoadItemDataByID, itemID)
    end
    return nil
end
function ns.InvalidateProfessionSellValues() sellCache, sellRequested = {}, {} end

local function option(name, fallback)
    local value = ns.Option and ns.Option(name)
    if value == nil then return fallback end
    return value
end

function ns.ProfessionPathOptions()
    local mode = option("professionPathMode", "balanced")
    if not TIME_VALUE[mode] then mode = "balanced" end
    return {
        mode = mode, timeValue = TIME_VALUE[mode],
        recoup = option("professionVendorResale", true) == true,
        perk = option("professionPerk", false) == true,
        vendorRecipes = option("professionVendorRecipes", false) == true,
    }
end

-- Chance of a skill point from one craft, with the Legacy perk if the player says they have it.
local function chance(env, id, recipe, skill, options)
    local value = ns.ProfessionSkillChance(id, recipe, skill, false, options.widen)
    if value > 0 and value < 1 and options.perk then value = math.min(1, value * PERK) end
    return value
end

local recipeCost

-- The cheapest known way to hold one of an item at this skill: buy it, or
-- make it. Returns copper, whether that figure rests on known prices only,
-- the crafting seconds and expected skill points making it involves, and the
-- recipe used when it is crafted.
local function unitCost(env, id, item, skill, options, depth, visiting)
    local direct = env.price(item)
    local best, priced, seconds, gain, via = direct, direct ~= nil, 0, 0, nil
    if depth < DEPTH and not visiting[item] then
        local data = env.index(id)
        local craftedTotal
        for _, recipe in ipairs(data and data.producers[item] or {}) do
            if env.craftable(id, recipe, skill) then
                visiting[item] = true
                local cost, complete, innerSeconds, innerGain = recipeCost(env, id, recipe, skill, options, depth + 1, visiting)
                visiting[item] = nil
                local made = math.max(1, recipe.outputQuantity or 1)
                local madeSeconds = (innerSeconds + env.seconds(recipe)) / made
                local madeGain = (innerGain + chance(env, id, recipe, skill, options)) / made
                -- Compare like with like: gold plus the time making it takes.
                local total = cost / made + madeSeconds * options.timeValue
                -- A known price is only beaten by a fully priced craft. With
                -- no price for the item itself, making it is the estimate:
                -- an unknown price must never look cheaper than the parts.
                if (direct == nil or complete and total < direct) and (not craftedTotal or total < craftedTotal) then
                    craftedTotal = total
                    best, priced, seconds, gain, via = cost / made, complete, madeSeconds, madeGain, recipe
                end
            end
        end
    end
    if best == nil then return UNKNOWN_UNIT, false, 0, 0, nil end
    return best, priced, seconds, gain, via
end

-- One craft of a recipe: reagent copper, whether every reagent was priced,
-- and the seconds and expected skill points of any intermediates crafted.
function recipeCost(env, id, recipe, skill, options, depth, visiting, prepared)
    local total, complete, seconds, gain = 0, true, 0, 0
    for _, material in ipairs(recipe.materials) do
        local item, quantity = material[1], material[2]
        local unit, priced, unitSeconds, unitGain, via = unitCost(env, id, item, skill, options, depth, visiting)
        total, complete = total + unit * quantity, complete and priced
        seconds, gain = seconds + unitSeconds * quantity, gain + unitGain * quantity
        if via and prepared then
            local entry = prepared[via.id] or {name = via.name, amount = 0}
            entry.amount = entry.amount + quantity / math.max(1, via.outputQuantity or 1)
            prepared[via.id] = entry
        end
    end
    return total, complete, seconds, gain
end

-- What one skill point costs with this recipe at this skill.
local function point(env, id, recipe, skill, options)
    local own = chance(env, id, recipe, skill, options)
    if own <= 0 then return nil end
    local prepared = {}
    local cost, complete, prepSeconds, prepGain = recipeCost(env, id, recipe, skill, options, 0, {}, prepared)
    local resale = 0
    if options.recoup and recipe.outputID then
        local value = ns.ProfessionSellValue(recipe.outputID)
        if value then resale = value * math.max(1, recipe.outputQuantity or 1) end
    end
    local gold = math.max(0, cost - resale)
    local seconds = env.seconds(recipe) + prepSeconds
    local gain = own + prepGain
    return {
        score = (gold + seconds * options.timeValue) / gain,
        gold = gold / gain, seconds = seconds / gain, crafts = 1 / gain,
        -- For the spread of crafts needed: a point arrives with at most certainty.
        chance = math.min(1, gain), priced = complete, prepared = prepared,
    }
end

-- What learning a recipe costs once: copper, how it is obtained, and whether
-- that copper figure is known.
local function acquisition(env, id, recipe, options)
    local live = env.live(id, recipe)
    if live and live.learned then return 0, nil, true end
    if recipe.source == "start" then return 0, nil, true end
    if recipe.source == "trainer" then
        local fee = ns.GuideInteger(recipe.trainingCost, 100000000) and recipe.trainingCost or nil
        return (fee or 0) + VISIT.trainer * options.timeValue, "trainer", fee ~= nil, fee
    end
    return VISIT.vendor * options.timeValue, recipe.source or "unknown", false
end

-- Where the client says an unlearned recipe comes from, when it offers that.
function ns.ProfessionRecipeSource(recipeID)
    local reader = C_TradeSkillUI and C_TradeSkillUI.GetRecipeSourceText
    if type(reader) ~= "function" then return nil end
    local text = ns.ReadPublic(reader, recipeID)
    if not ns.Public(text) or type(text) ~= "string" or text == "" then return nil end
    text = string.gsub(text, "|c%x%x%x%x%x%x%x%x", "")
    text = string.gsub(text, "|r", "")
    text = string.gsub(text, "|n", " ")
    text = string.gsub(text, "%s+", " ")
    return string.sub(text, 1, 120)
end

-- A preference changed: every path on screen was calculated with the old one.
function ns.ProfessionPathOptionsChanged()
    ns.professionRevision = (ns.professionRevision or 0) + 1
    if ns.ProfessionPricesChanged then ns.ProfessionPricesChanged() end
    if ns.RefreshProfessionViewer then ns.RefreshProfessionViewer(true) end
end

function ns.ProfessionPathDiagnostics(output)
    local options = ns.ProfessionPathOptions()
    output("Skilling path: prefers " .. options.mode .. "; vendor value of crafts " .. (options.recoup and "counted" or "ignored")
        .. "; vendor-sold recipes " .. (options.vendorRecipes and "allowed" or "only where no trainer recipe exists")
        .. "; Working Overtime perk " .. (options.perk and "on" or "off") .. "; "
        .. tostring(ns.professionHotfixesApplied or 0) .. " published hotfix change(s) applied to the recipe reference.")
    output("Skilling path sources: recipe source text from the client "
        .. (C_TradeSkillUI and type(C_TradeSkillUI.GetRecipeSourceText) == "function" and "available" or "unavailable")
        .. "; vendor sell prices " .. ((C_Item and type(C_Item.GetItemInfo) == "function" or type(GetItemInfo) == "function") and "readable" or "unreadable") .. ".")
end

-- For tests and diagnostics: what one skill point costs with a recipe, and what learning it costs.
function ns.ProfessionPathPoint(id, recipe, skill, widen)
    local options = ns.ProfessionPathOptions()
    options.widen = widen == true
    return point(ns.professionPathEnv, id, recipe, skill, options)
end
function ns.ProfessionPathFee(id, recipe)
    return acquisition(ns.professionPathEnv, id, recipe, ns.ProfessionPathOptions())
end

local function solve(env, id, start, target, base, widen, cooperative)
    local options = {}
    for key, value in pairs(base) do options[key] = value end
    options.widen = widen == true
    -- continued[r][s]: the cheapest way to stand at skill s having crafted
    -- recipe r for the point before it, its fee already paid.
    local best, bestRecipe = {[start] = 0}, {}
    local continued, since, facts = {}, {}, {}
    for skill = start, target - 1 do
        local here = best[skill]
        local list = env.candidates(id, skill, widen)
        local nextBest, nextRecipe
        local alive = {}
        for _, recipe in ipairs(list) do
            local fact = point(env, id, recipe, skill, options)
            if fact and here then
                local key = recipe.id
                local fee = acquisition(env, id, recipe, options)
                local carry = continued[key] and continued[key][skill]
                local fresh = here + fee
                local base, from = fresh, skill
                if carry and carry <= fresh then base, from = carry, since[key][skill] end
                continued[key] = continued[key] or {}
                since[key] = since[key] or {}
                continued[key][skill + 1], since[key][skill + 1] = base + fact.score, from
                facts[key] = facts[key] or {recipe = recipe}
                facts[key][skill] = fact
                alive[key] = true
                if not nextBest or continued[key][skill + 1] < nextBest then
                    nextBest, nextRecipe = continued[key][skill + 1], key
                end
            end
        end
        -- A recipe that could not be crafted at this skill does not carry on.
        for key, row in pairs(continued) do if not alive[key] then row[skill + 1] = nil end end
        best[skill + 1], bestRecipe[skill + 1] = nextBest, nextRecipe
        if cooperative and skill % 8 == 0 then coroutine.yield() end
    end
    -- Walk back from the highest skill reached, one block of crafts at a time.
    local reached = start
    for skill = target, start + 1, -1 do if best[skill] then reached = skill; break end end
    local blocks, skill = {}, reached
    while skill > start do
        local key = bestRecipe[skill]
        local from = since[key][skill]
        table.insert(blocks, 1, {key = key, start = from, finish = skill})
        skill = from
    end
    return blocks, facts, reached
end

-- The plan from `start` to `target`. `widen` also considers recipes sold by
-- vendors (see the caller); the result has the shape the shopping forecast
-- and the viewer already read, with the cost breakdown added.
function ns.ProfessionPathPlan(id, start, target, cooperative)
    local env = ns.professionPathEnv
    local options = ns.ProfessionPathOptions()
    local blocks, facts, reached = solve(env, id, start, target, options, options.vendorRecipes, cooperative)
    local widened = false
    if reached < target and not options.vendorRecipes then
        -- No trainer recipe covers the whole way. Rather than stop, show how
        -- recipes a vendor sells would continue it, and say so.
        local wideBlocks, wideFacts, wideReached = solve(env, id, start, target, options, true, cooperative)
        if wideReached > reached then blocks, facts, reached, widened = wideBlocks, wideFacts, wideReached, true end
    end
    local steps, gold, fees, seconds, priced = {}, 0, 0, 0, true
    for _, block in ipairs(blocks) do
        local recipe = facts[block.key].recipe
        local crafts, variance, stepGold, stepSeconds, stepPriced, prepared = 0, 0, 0, 0, true, {}
        for skill = block.start, block.finish - 1 do
            local fact = facts[block.key][skill]
            crafts, stepGold, stepSeconds = crafts + fact.crafts, stepGold + fact.gold, stepSeconds + fact.seconds
            variance = variance + (1 - fact.chance) / (fact.chance * fact.chance)
            stepPriced = stepPriced and fact.priced
            for recipeID, entry in pairs(fact.prepared) do
                local total = prepared[recipeID] or {name = entry.name, amount = 0}
                total.amount = total.amount + entry.amount * fact.crafts
                prepared[recipeID] = total
            end
        end
        local _, how, feeKnown, fee = acquisition(env, id, recipe, options)
        if how == nil then feeKnown = true end
        local step = {
            recipe = recipe, start = block.start, finish = block.finish, crafts = crafts,
            safe = math.ceil(crafts + SAFE_Z * math.sqrt(variance) - 1e-9),
            gold = stepPriced and math.ceil(stepGold) or nil, seconds = stepSeconds, priced = stepPriced,
            acquire = how, fee = fee, feeKnown = feeKnown, prepared = prepared,
            source = how and how ~= "trainer" and (recipe.id > 0 and ns.ProfessionRecipeSource(recipe.id) or recipe.note) or nil,
        }
        steps[#steps + 1] = step
        gold, seconds, fees = gold + stepGold, seconds + stepSeconds, fees + (fee or 0)
        priced = priced and stepPriced and (how == nil or feeKnown)
    end
    return {
        steps = steps, missing = target - reached, start = start, target = target,
        gold = priced and math.ceil(gold) or nil, fees = fees, seconds = seconds, priced = priced,
        mode = options.mode, recoup = options.recoup, perk = options.perk,
        vendorRecipes = options.vendorRecipes or widened, widened = widened,
    }
end
