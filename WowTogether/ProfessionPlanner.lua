local addonName, ns = ...

-- Personal crafting plans: only skill, inventory and public recipe facts enter
-- this planner. No craft, train, buy or auction-search action is executed here.
local order = {171, 164, 333, 202, 165, 197}
local indexed, excluded = {}, {}
local stockCache, nameCache, cachedRevision = {}, {}, nil
local workstations = {[164] = "Use an anvil and bring a Blacksmith Hammer.",
    [202] = "Check the recipe's tools; some crafts need an anvil.",
    [333] = "Bring the enchanting rod required by this recipe."}
local lastCraftGUID
ns.professionCraftsObserved = 0

function ns.ProfessionFacts(id)
    return ns.professionGuideData and ns.professionGuideData.professions[id]
end

local function index(id)
    local data = ns.ProfessionFacts(id)
    if not data then return end
    if not indexed[id] or indexed[id].data ~= data then
        local byID, producers = {}, {}
        for _, recipe in ipairs(data.recipes) do
            byID[recipe.id] = recipe
            if recipe.outputID then
                producers[recipe.outputID] = producers[recipe.outputID] or {}
                table.insert(producers[recipe.outputID], recipe)
            end
        end
        indexed[id] = {data = data, byID = byID, producers = producers}
    end
    return indexed[id]
end

function ns.SaveProfessionState(id)
    local info = ns.professionData[id]
    local saved = ns.professionSaved
    if not info or not saved then return end
    local known = {}
    for spell, recipe in pairs(info.known or {}) do if recipe.learned then known[spell] = true end end
    saved.skills[id] = {skill = info.skill, maximum = info.maximum, name = info.name, known = known}
end

function ns.ReadProfessionSkills()
    if type(GetProfessions) ~= "function" or type(GetProfessionInfo) ~= "function" then return false end
    local okay, a, b = pcall(GetProfessions)
    if not okay or not ns.Public(a) or not ns.Public(b) then return false end
    local seen = {}
    for _, slot in pairs({a, b}) do
        if ns.GuideInteger(slot) and slot > 0 then
            -- The shared public reader returns five values; this API's skill
            -- line ID is its seventh return. Guard the fields we actually use.
            local okay, name, icon, skill, maximum, abilities, offset, id = pcall(GetProfessionInfo, slot)
            if okay and ns.SafeTitle(name) and ns.GuideInteger(id) and id > 0
                and ns.GuideInteger(skill, 1000) and ns.GuideInteger(maximum, 1000) then
                if ns.ProfessionFacts(id) then
                    local info = ns.professionData[id] or {id = id, recipes = {}, known = {}}
                    info.name, info.skill, info.maximum = ns.SafeTitle(name), skill, maximum
                    ns.professionData[id], seen[id] = info, true
                    ns.SaveProfessionState(id)
                end -- Gathering professions are valid primaries, without a crafting card.
            else return false end -- An unreadable entry must not erase a learned profession.
        elseif slot ~= nil then return false end
    end
    for _, id in ipairs(order) do
        if not seen[id] then
            ns.professionData[id] = nil
            if ns.professionSaved then ns.professionSaved.skills[id] = nil end
        end
    end
    ns.professionSkillsConfirmed = true
    return true
end

function ns.InitializeProfessionState()
    if type(ns.db.professions) ~= "table" then ns.db.professions = {} end
    if type(ns.db.professions[ns.self]) ~= "table" then ns.db.professions[ns.self] = {} end
    local saved = ns.db.professions[ns.self]
    if type(saved.skills) ~= "table" then saved.skills = {} end
    if type(saved.goals) ~= "table" then saved.goals = {} end
    ns.professionSaved = saved
    for _, id in ipairs(order) do
        local old = saved.skills[id]
        if type(old) == "table" and ns.GuideInteger(old.skill, 1000) and ns.GuideInteger(old.maximum, 1000) then
            local known = {}
            for spell, learned in pairs(type(old.known) == "table" and old.known or {}) do
                if ns.GuideInteger(spell) and learned == true then known[spell] = {id = spell, learned = true} end
            end
            ns.professionData[id] = {id = id, name = ns.ProfessionFacts(id).name, skill = old.skill,
                maximum = old.maximum, known = known, recipes = {}, cached = true}
        end
    end
    ns.ReadProfessionSkills()
end

local function liveRecipe(id, recipe)
    local info = ns.professionData[id]
    return info and info.known and info.known[recipe.id]
end
local function allowed(id, recipe, skill)
    local live = liveRecipe(id, recipe)
    if recipe.faction and (not ns.profile or recipe.faction ~= ns.profile.faction) and not (live and live.learned) then return false end
    if not ns.GuideInteger(recipe.learn, 1000) or recipe.learn > skill then return false end
    if not (live and live.learned) and recipe.source ~= "start" and recipe.source ~= "trainer" then return false end
    return #recipe.materials > 0
end

function ns.ProfessionSkillChance(id, recipe, skill, current)
    if not allowed(id, recipe, skill) then return 0 end
    local live = liveRecipe(id, recipe)
    if current and live and live.learned and ns.professionData[id].recipeSkill == skill then
        if live.canSkillUp == false or ns.professionData[id].live and live.canSkillUp == nil then return 0 end
        local color = ns.ProfessionDifficultyName(live.difficulty)
        if color == "Orange" then return 1 elseif color == "Yellow" then return 0.65
        elseif color == "Green" then return 0.25 elseif color == "Grey" then return 0 end
    end
    if not ns.GuideInteger(recipe.grey, 1000) or recipe.grey <= skill then return 0 end
    if recipe.yellow and skill < recipe.yellow then return 1 end
    if recipe.yellow and recipe.grey > recipe.yellow then return math.max(0.05, math.min(1, (recipe.grey - skill) / (recipe.grey - recipe.yellow))) end
    return 0.5
end

local function owned(id)
    if stockCache[id] == nil then stockCache[id] = ns.ItemOwned(id) or false end
    return stockCache[id] ~= false and stockCache[id] or nil
end
local function price(id)
    local auction, vendor = ns.marketQuotes[id], ns.professionVendorQuotes and ns.professionVendorQuotes[id]
    if auction and vendor then return math.min(auction.unitPrice, vendor.unitPrice) end
    return auction and auction.unitPrice or vendor and vendor.unitPrice
end
local function itemName(id, item)
    if not nameCache[id] then nameCache[id] = ns.ItemName(id, item and item.name) end
    return nameCache[id]
end
function ns.InvalidateProfessionItemName(id) nameCache[id] = nil end

-- Expand intermediate bolts/powders/stones only when their recipe is already
-- learned or supplied by a trainer. A stock ledger is shared through the tree.
function ns.ProfessionMaterials(id, recipe, crafts, skill, useStock, sharedLedger)
    local data = index(id)
    local ledger, rows, preparations, visiting = sharedLedger or {}, {}, {}, {}
    local complete, total, incomplete = true, 0, nil
    local info = ns.professionData[id]
    local open = info and info.live and C_TradeSkillUI and ns.ReadPublic(C_TradeSkillUI.GetChildProfessionInfo)
    if info and info.live and (type(open) ~= "table" or not ns.GuideInteger(open.professionID) or open.professionID <= 0) then
        open = C_TradeSkillUI and ns.ReadPublic(C_TradeSkillUI.GetBaseProfessionInfo)
    end
    local nativeOpen = type(open) == "table" and ns.Public(open.professionID) and open.professionID == id
    local function reagents(r, quantity)
        local live = liveRecipe(id, r)
        if nativeOpen and live and live.learned then
            local list, _, missing = ns.RecipeMaterials(r.id, quantity)
            if not missing and #list > 0 then
                local mats = {}; for _, mat in ipairs(list) do mats[#mats + 1] = {mat.itemID, mat.need} end
                return mats
            end
            incomplete = true
        end
        local mats = {}; for _, mat in ipairs(r.materials) do mats[#mats + 1] = {mat[1], mat[2] * quantity} end
        return mats
    end
    local function stock(itemID)
        if ledger[itemID] == nil then ledger[itemID] = useStock and (owned(itemID) or false) or 0 end
        return ledger[itemID] ~= false and ledger[itemID] or nil
    end
    local function record(itemID, quantity, missing)
        local row = rows[itemID]
        if not row then
            local item = data.data.items[itemID]
            row = {itemID = itemID, name = itemName(itemID, item), need = 0,
                source = "Recipe material • vendor, gathering or auction house"}
            if useStock then row.have = owned(itemID) else row.have = 0 end
            if row.have == nil then incomplete = true end
            local vendor = ns.professionVendorQuotes and ns.professionVendorQuotes[itemID]
            if vendor and vendor.npc then row.source = "Vendor: " .. vendor.npc end
            rows[itemID] = row
        end
        row.need = row.need + quantity
        row.missing = (row.missing or 0) + missing
    end
    local consume
    consume = function(itemID, quantity, depth)
        local have = stock(itemID)
        local used = have and math.min(have, quantity) or 0
        if have then ledger[itemID] = have - used end
        local missing = quantity - used
        if missing == 0 then record(itemID, quantity, 0); return end
        local maker
        if depth < 5 and not visiting[itemID] then
            for _, candidate in ipairs(data.producers[itemID] or {}) do
                if allowed(id, candidate, skill) and candidate.id ~= recipe.id
                    and (not maker or candidate.learn < maker.learn or candidate.learn == maker.learn and candidate.id < maker.id) then maker = candidate end
            end
        end
        -- An observed direct purchase price leaves this a shopping item; otherwise
        -- make learnable intermediates from raw stock. No invented vendor prices.
        if maker and not price(itemID) then
            if used > 0 then record(itemID, used, 0) end
            visiting[itemID] = true
            local batches = math.ceil(missing / (maker.outputQuantity or 1))
            for _, mat in ipairs(reagents(maker, batches)) do consume(mat[1], mat[2], depth + 1) end
            visiting[itemID] = nil
            preparations[#preparations + 1] = {recipe = maker, crafts = batches}
            ledger[itemID] = (ledger[itemID] or 0) + batches * (maker.outputQuantity or 1) - missing
        else
            record(itemID, quantity, missing)
            local unit = price(itemID)
            if unit then total = total + missing * unit else complete = false end
        end
    end
    for _, mat in ipairs(reagents(recipe, crafts)) do consume(mat[1], mat[2], 0) end
    local list = {}; for _, row in pairs(rows) do list[#list + 1] = row end
    table.sort(list, function(a, b) return a.itemID < b.itemID end)
    return list, complete and not incomplete and math.ceil(total) or nil, preparations, incomplete
end

-- Carry owned stock and planned outputs through the entire preview. A bolt or
-- leather made earlier is available to later recipes, rather than bought twice.
function ns.ProfessionMaterialForecast(id, plan, cooperative)
    local ledger, merged, incomplete = {}, {}, plan.missing > 0
    for _, step in ipairs(plan.steps) do
        local crafts = math.ceil(step.crafts)
        local list, _, _, unreadable = ns.ProfessionMaterials(id, step.recipe, crafts, step.start, true, ledger)
        incomplete = incomplete or unreadable
        for _, row in ipairs(list) do
            local item = merged[row.itemID]
            if not item then
                item = {itemID = row.itemID, name = row.name, need = 0, missing = 0,
                    have = row.have, source = row.source}; merged[row.itemID] = item
            end
            item.need, item.missing = item.need + row.need, item.missing + row.missing
            if row.have == nil then incomplete = true; item.unreadable = true end
        end
        if step.recipe.outputID then
            local output = step.recipe.outputID
            if ledger[output] == nil then ledger[output] = owned(output) or false end
            if ledger[output] == false then incomplete = true end
            ledger[output] = (ledger[output] or 0) + crafts * (step.recipe.outputQuantity or 1)
        end
        if cooperative then coroutine.yield() end
    end
    local list, cost, priced = {}, 0, not incomplete
    for _, row in pairs(merged) do
        if row.unreadable then row.missing = nil end
        row.planned = row.have and row.missing and math.max(0, row.need - row.have - row.missing) or nil
        local unit = price(row.itemID)
        if row.missing == nil or row.missing > 0 and not unit then priced = false
        elseif row.missing > 0 then cost = cost + row.missing * unit end
        list[#list + 1] = row
    end
    table.sort(list, function(a, b) return a.itemID < b.itemID end)
    return {materials = list, estimatedCost = priced and math.ceil(cost) or nil,
        incomplete = incomplete, start = plan.start, target = plan.target, missing = plan.missing}
end

local function candidates(id, skill, current)
    local result, data = {}, index(id)
    if not data then return result end
    for _, recipe in ipairs(data.data.recipes) do
        if (not current or not excluded[id] or excluded[id].skill ~= skill or not excluded[id][recipe.id])
            and (not current or not string.match(recipe.name, "^Runed .* Rod$") or not recipe.outputID or owned(recipe.outputID) == 0)
            and (current or not string.match(recipe.name, "^Runed .* Rod$") or skill == recipe.learn)
            and ns.ProfessionSkillChance(id, recipe, skill, current) > 0 then result[#result + 1] = recipe end
    end
    -- A learned beta recipe missing from the snapshot can still be recommended.
    for _, live in pairs(ns.professionData[id] and ns.professionData[id].known or {}) do
        if live.learned and live.canSkillUp == true and not data.byID[live.id] then
            local materials, _, incomplete = ns.RecipeMaterials(live.id, 1)
            if not incomplete and #materials > 0 then
                local mats = {}; for _, m in ipairs(materials) do mats[#mats + 1] = {m.itemID, m.need} end
                local r = {id = live.id, name = live.name, learn = skill, grey = skill + 1, yellow = skill,
                    source = "live", materials = mats, outputQuantity = 1}
                if current then result[#result + 1] = r end
            end
        end
    end
    table.sort(result, function(a, b) return a.id < b.id end)
    return result
end

local function resources(list)
    local n = 0; for _, row in ipairs(list) do n = n + row.missing end; return n
end
local function score(id, recipe, skill, current, useStock)
    local chance = ns.ProfessionSkillChance(id, recipe, skill, current)
    if not current then
        local total, quantity, complete = 0, 0, true
        for _, mat in ipairs(recipe.materials) do
            local unit = price(mat[1]); quantity = quantity + mat[2]
            if unit then total = total + unit * mat[2] else complete = false end
        end
        return ((complete and total / 100 or quantity * 10) + 4) / chance, complete
    end
    local list, cost, prep = ns.ProfessionMaterials(id, recipe, 1, skill, useStock)
    local live = liveRecipe(id, recipe)
    local gain = live and live.skillUps and math.max(1, live.skillUps) or 1
    -- Copper when prices are known; a resource heuristic otherwise. Missing
    -- prices are displayed as unknown, never advertised as zero cost.
    local value = cost and cost / 100 or resources(list) * 10
    return (value + 4 + #prep * 3 + (live and live.learned and 0 or 8 / 5)) / (chance * gain), cost ~= nil
end

function ns.ProfessionNextRecipe(id, skill)
    local best, bestScore
    for _, recipe in ipairs(candidates(id, skill, true)) do
        local value = score(id, recipe, skill, true, true)
        if not best or value < bestScore then best, bestScore = recipe, value end
    end
    return best
end

function ns.ProfessionGoal(id, value)
    if value == 75 or value == 150 or value == 225 or value == 300 then
        if ns.professionSaved then ns.professionSaved.goals[id] = value end
        return value
    end
    local saved = ns.professionSaved and ns.professionSaved.goals[id]
    return (saved == 75 or saved == 150 or saved == 225 or saved == 300) and saved or 225
end

function ns.ProfessionTrainer(id, maximum, recipeID)
    local facts, profile = ns.ProfessionFacts(id), ns.profile or {}
    local best, bestScore
    local point = ns.PlayerPoint(profile.mapID or 0)
    local trainers = {}; for _, trainer in ipairs(facts.trainers) do trainers[#trainers + 1] = trainer end
    for _, trainer in ipairs(ns.ObservedProfessionTrainers and ns.ObservedProfessionTrainers(id, maximum, recipeID) or {}) do trainers[#trainers + 1] = trainer end
    for _, trainer in ipairs(trainers) do
        if (trainer.faction == "Both" or trainer.faction == profile.faction)
            and (trainer.maximum >= maximum or recipeID and trainer.recipes and trainer.recipes[recipeID]) then
            local distance = point and ns.TravelPointDistance(point, trainer)
            local value = distance or (trainer.mapID == profile.mapID and 10000 or 100000)
            if not distance and trainer.mapID ~= profile.mapID
                and (trainer.mapID == 1453 or trainer.mapID == 1454 or trainer.mapID == 1455 or trainer.mapID == 1456 or trainer.mapID == 1457 or trainer.mapID == 1458) then value = value - 20000 end
            value = value + (trainer.dungeon and 1000000 or 0) + (trainer.maximum - maximum) * 2
            if not best or value < bestScore then best, bestScore = trainer, value end
        end
    end
    return best
end

local function stop(id, action, instruction, description, trainer)
    local facts = ns.ProfessionFacts(id)
    local s = {id = 0, kind = "profession", professionStep = true, professionID = id, action = action,
        title = facts.name .. " crafting guide", label = instruction, description = description,
        mapID = trainer and trainer.mapID or 0, x = trainer and trainer.x or 0, y = trainer and trainer.y or 0,
        unknownLocation = not trainer, npcName = trainer and trainer.name}
    if trainer then s.description = description .. "\n" .. trainer.hub .. (trainer.dungeon and " • Inside the dungeon; marker shows its entrance." or "") end
    return s
end

-- A batch is remaining work, not a new shopping order on every bag event.
-- Skill milestones limit material commitments; only actual skill ends a stage.
local function milestone(id, recipe, skill, limit)
    for _, value in ipairs({recipe.yellow or limit, recipe.green or limit, recipe.grey or limit}) do
        if value > skill then limit = math.min(limit, value) end
    end
    for _, nextRecipe in ipairs(index(id).data.recipes) do
        if ns.GuideInteger(nextRecipe.learn, 1000) and nextRecipe.learn > skill and nextRecipe.learn < limit
            and allowed(id, nextRecipe, nextRecipe.learn) then limit = nextRecipe.learn end
    end
    return limit
end

local function remainingCrafts(id, recipe, skill, finish)
    local live = liveRecipe(id, recipe)
    local gain = live and live.skillUps and math.max(1, live.skillUps) or 1
    -- Estimate the work to the milestone from this recipe's current chance,
    -- rather than a fixed 1/3/5-craft limit. Actual skill ends the step even when
    -- it reaches the milestone before this estimate is exhausted.
    local chance = ns.ProfessionSkillChance(id, recipe, skill, true)
    return math.min(math.ceil((finish - skill) / (gain * math.max(0.05, chance))),
        string.match(recipe.name, "^Runed .* Rod$") and 1 or 6000)
end

local function currentBatch(guide, info)
    local id, batch = guide.professionID, guide.professionBatch
    local bestRecipe = ns.ProfessionNextRecipe(id, info.skill)
    local recipe = batch and index(id).byID[batch.recipeID]
    if batch and not recipe then
        -- A live-only beta recipe has no bundled thresholds. Resolve it from
        -- this read without storing the entire native recipe in SavedVariables.
        for _, candidate in ipairs(candidates(id, info.skill, true)) do
            if candidate.id == batch.recipeID then recipe = candidate; break end
        end
    end
    if batch and recipe and bestRecipe and bestRecipe.id == recipe.id and batch.remaining > 0
        and info.skill >= batch.startSkill and info.skill < batch.finish
        and batch.goal == guide.targetSkill and batch.maximum == info.maximum
        and (not excluded[id] or excluded[id].skill ~= info.skill or not excluded[id][recipe.id])
        and ns.ProfessionSkillChance(id, recipe, info.skill, true) > 0 then
        -- Failed skill-ups consume materials but do not reduce the skill gap.
        -- Re-estimate from the actual current skill/color after each update.
        batch.remaining = remainingCrafts(id, recipe, info.skill, batch.finish)
        batch.total = math.max(batch.total, batch.remaining)
    else
        recipe = bestRecipe
        batch = nil
        if recipe then
            local finish = milestone(id, recipe, info.skill, math.min(guide.targetSkill, info.maximum))
            local crafts = remainingCrafts(id, recipe, info.skill, finish)
            batch = {recipeID = recipe.id, remaining = crafts, total = crafts, startSkill = info.skill,
                finish = finish, goal = guide.targetSkill, maximum = info.maximum}
        end
        guide.professionBatch = batch
    end
    return recipe, batch
end

function ns.ObserveProfessionCraft(unit, castGUID, spellID)
    -- This documented spell-success event may contain secret combat values.
    -- Count only a public player's successful cast of the active craft recipe.
    if not ns.Public(unit) or unit ~= "player" or not ns.SafeTitle(castGUID)
        or not ns.GuideInteger(spellID) or spellID <= 0 or castGUID == lastCraftGUID then return end
    local guide, route = ns.routeSelection, ns.selectedRoute
    local batch = guide and guide.mode == "profession" and guide.professionBatch
    local current = route and route.stops[1]
    if not batch or not current or not route.recipe or route.recipe.id ~= batch.recipeID then return end
    -- Players may craft the affordable part while the guide still asks for
    -- the rest of the materials. That work belongs to the same active batch.
    local matching = spellID == batch.recipeID or current.craftRecipeID == spellID
    if not matching then
        for _, prep in ipairs(route.preparations or {}) do
            if prep.recipe.id == spellID then matching = true; break end
        end
    end
    if not matching then return end
    lastCraftGUID = castGUID
    if spellID == batch.recipeID then batch.remaining = math.max(0, batch.remaining - 1) end
    ns.professionCraftsObserved = ns.professionCraftsObserved + 1
    -- Preparation crafts alter stock and can themselves raise skill. Let the
    -- batched fresh skill/bag reads decide how much preparation remains.
    ns.SaveSelectedGuide()
    ns.QueueProfessionUpdate(true)
end

function ns.BuildProfessionGuideRoute(guide)
    if cachedRevision ~= ns.professionRevision then stockCache, cachedRevision = {}, ns.professionRevision end
    local id, target = guide.professionID, guide.targetSkill
    local info, facts = ns.professionData[id], ns.ProfessionFacts(id)
    local route = {key = guide.key, title = guide.title, mapID = 0, stops = {}, remainingSteps = 1}
    local current
    if not info then
        local trainer = ns.ProfessionTrainer(id, 75)
        current = stop(id, "learn", "Learn " .. facts.name .. (trainer and (" from " .. trainer.name) or " from a profession trainer"), "Learn the profession, then open its crafting window.", trainer)
    elseif not info.skill or not info.maximum then
        current = stop(id, "read", "Open your " .. facts.name .. " window", "Check your current skill and learned recipes.")
    elseif info.skill >= target then
        route.complete, route.remainingSteps = true, 0
        current = stop(id, "complete", facts.name .. " goal reached!", "Skill " .. info.skill .. " • Goal " .. target .. ". Choose a higher goal when ready.")
    elseif info.skill >= info.maximum then
        local rank
        for _, r in ipairs(facts.ranks) do if r.maximum > info.maximum and info.skill >= r.skill then rank = r; break end end
        if not rank then current = stop(id, "wait", "Check your profession trainer", "Your current rank is capped. Check available training.")
        elseif not ns.profile or not ns.profile.level or ns.profile.level < rank.level then
            current = stop(id, "wait", "Reach character level " .. rank.level .. " for " .. rank.name,
                "Skill " .. info.skill .. " / " .. info.maximum .. " • Resume crafting after rank training.")
        else
            local trainer = ns.ProfessionTrainer(id, rank.maximum)
            current = stop(id, "train", "Train " .. rank.name .. " " .. facts.name .. (trainer and (" with " .. trainer.name) or ""),
                "Your current cap is " .. info.maximum .. ". " .. rank.name .. " raises it to " .. rank.maximum
                    .. " so you can keep progressing toward skill " .. target .. ".", trainer)
        end
    else
        local recipe, batch = currentBatch(guide, info)
        if not recipe then current = stop(id, "read", "Open your " .. facts.name .. " window or check its trainer", "No suitable skill-up recipe is confirmed. Refresh after training.")
        else
            local live = liveRecipe(id, recipe)
            local crafts = batch.remaining
            local gain = live and live.skillUps and math.max(1, live.skillUps) or 1
            local chance = ns.ProfessionSkillChance(id, recipe, info.skill, true)
            route.estimatedCraftsToMilestone = math.ceil((batch.finish - info.skill) / (math.max(0.05, chance) * gain))
            local list, cost, prep, incomplete = ns.ProfessionMaterials(id, recipe, crafts, info.skill, true)
            route.materials, route.recipe, route.crafts, route.preparations = list, recipe, crafts, prep
            route.skillTarget, route.batchTotal = batch.finish, batch.total
            local nextRecipe, amount = recipe, crafts
            if prep[1] then nextRecipe, amount = prep[1].recipe, prep[1].crafts; live = liveRecipe(id, nextRecipe) end
            if incomplete then
                current = stop(id, "read", "Check the materials for " .. recipe.name .. " in your profession window", "Refresh when the recipe's material data is ready.")
            elseif not live or not live.learned then
                if info.recipeRefreshPending or not info.live then
                    current = stop(id, "read", "Open your " .. facts.name .. " window",
                        "Refresh learned recipes before training " .. nextRecipe.name .. ".")
                else
                    -- Learning a recipe below the current cap does not require the
                    -- next rank. Do not send a 146/150 player across the continent
                    -- merely because Expert training is already unlocked at 125.
                    local trainer = ns.ProfessionTrainer(id, info.maximum, nextRecipe.id)
                    local extra = ""
                    for _, rank in ipairs(facts.ranks) do
                        if trainer and rank.maximum > info.maximum and rank.maximum <= target and rank.maximum <= 225
                            and trainer.maximum >= rank.maximum and info.skill >= rank.skill
                            and ns.profile and ns.profile.level >= rank.level then
                            extra = " Also train " .. rank.name .. " here to raise your cap to " .. rank.maximum
                                .. " and avoid a later training visit."; break
                        end
                    end
                    current = stop(id, "train", "Learn " .. nextRecipe.name .. (trainer and (" from " .. trainer.name) or " at your trainer"),
                        "Learn this recipe to work toward skill " .. batch.finish .. "." .. extra
                            .. " Then prepare materials for " .. recipe.name .. ".", trainer)
                end
            else
                local missing, summary = false, {}
                for _, row in ipairs(list) do
                    if row.missing > 0 then missing = true; summary[#summary + 1] = row.missing .. " × " .. row.name end
                end
                if missing then current = stop(id, "buy", "Gather or buy materials for " .. recipe.name,
                    table.concat(summary, ", ", 1, math.min(3, #summary)) .. (#summary > 3 and "…" or "") .. "\nMaterials opens your complete buy list.")
                else current = stop(id, "craft", "Craft " .. (not prep[1] and "~" or "") .. amount .. " × " .. nextRecipe.name,
                    (prep[1] and ("Prepare materials for " .. recipe.name .. ".") or (workstations[id] or "Craft in your profession window."))
                    .. (prep[1] and " Skill-ups can vary." or (" Stop at skill " .. batch.finish .. "; skill-ups vary."))) end
            end
            current.description = "Skill " .. info.skill .. " → " .. batch.finish .. " • Goal " .. target .. ".\n"
                .. "~" .. crafts .. " × " .. recipe.name .. " • stop at skill " .. batch.finish .. ".\n" .. current.description
            current.recipeID = recipe.id
            if current.action == "craft" then current.craftRecipeID = nextRecipe.id end
            route.estimatedCost = cost
        end
    end
    route.stops[1], route.mapID = current, current.mapID
    if current.action == "complete" then guide.professionBatch = nil end
    return route
end

function ns.UpdateProfessionRoute(guide)
    local signature = table.concat({guide.key, guide.targetSkill, ns.professionRevision or 0}, ":")
    if ns.selectedRoute and ns.selectedRoute.professionSignature == signature then return end
    local route = ns.BuildProfessionGuideRoute(guide)
    route.professionSignature = signature
    local previous = ns.selectedRoute and ns.selectedRoute.stops[1]
    ns.selectedRoute, ns.routePaused = route, nil
    ns.guideAction = route.stops[1].label
    ns.SaveSelectedGuide()
    if not previous or previous.label ~= route.stops[1].label or previous.mapID ~= route.mapID then
        ns.routeSignature = nil; ns.ResetTravelPath(); ns.DrawRoute(nil, true)
    end
end

function ns.StartProfessionGuide(id, goal)
    local facts = ns.ProfessionFacts(id)
    if not facts then return end
    ns.ReadProfessionSkills()
    if ns.ProfessionWindowMatches(id) then ns.ReadProfessionRecipes()
    elseif ns.professionData[id] then ns.professionData[id].recipeRefreshPending = true end
    excluded[id] = nil
    ns.professionRevision = (ns.professionRevision or 0) + 1
    local guide = {key = "profession:" .. id, title = facts.name .. " crafting guide", mode = "profession",
        professionID = id, targetSkill = ns.ProfessionGoal(id, goal), personal = true, records = {}, focusKey = ns.self}
    ns.ActivateRoute(guide)
    ns.guideAction = ns.selectedRoute.stops[1].label
    ns.UpdateNavigation()
    if ns.window then ns.window:Hide() end
    if ns.professionViewer then ns.professionViewer:Hide() end
    if ns.professionScanPrompt then ns.professionScanPrompt:Hide() end
    if not ns.selectedRoute.complete then ns.OfferProfessionScan(id) end
end

function ns.RefreshProfessionPlan(id)
    if id then excluded[id] = nil end
    ns.QueueProfessionUpdate(true)
    if id and ns.routeSelection and ns.routeSelection.mode == "profession" and ns.routeSelection.professionID == id then
        ns.OfferProfessionScan(id)
    end
end

function ns.ProfessionPricesChanged()
    local guide = ns.routeSelection
    if guide and guide.mode == "profession" then
        -- A fresh auction quote is an explicit opportunity to choose a cheaper
        -- craft now. Actual skill/bags retain everything already made.
        guide.professionBatch = nil
    end
    ns.QueueProfessionUpdate()
end

function ns.ProfessionGuideAction(kind)
    local guide = ns.routeSelection
    if not guide or guide.mode ~= "profession" then return end
    if kind == "quest" then ns.ShowProfessionShopping(guide.professionID, guide.targetSkill, "batch"); return end
    local info, recipe = ns.professionData[guide.professionID], ns.selectedRoute.recipe
    if info and recipe then
        local state = excluded[guide.professionID]
        if not state or state.skill ~= info.skill then state = {skill = info.skill}; excluded[guide.professionID] = state end
        state[recipe.id] = true
        ns.professionRevision = (ns.professionRevision or 0) + 1
        stockCache, cachedRevision = {}, ns.professionRevision
        ns.UpdateProfessionRoute(guide); ns.UpdateNavigation()
    end
end

-- Future estimates use dynamic programming over skill states, independent of
-- another site's suggested sequence. Yield every eight states during previews.
function ns.PlanProfessionPreview(id, target, cooperative)
    local info, facts = ns.professionData[id], ns.ProfessionFacts(id)
    local start = info and info.skill or 1
    local distance, choice = {[target] = 0}, {}
    for skill = target - 1, start, -1 do
        for _, recipe in ipairs(candidates(id, skill, false)) do
            local value = score(id, recipe, skill, false, false) + (distance[skill + 1] or 0)
            if not distance[skill] or value < distance[skill] then distance[skill], choice[skill] = value, recipe end
        end
        if cooperative and skill % 8 == 0 then coroutine.yield() end
    end
    local steps, missing = {}, 0
    for skill = start, target - 1 do
        local recipe = choice[skill]
        if not recipe then missing = target - skill; break end
        local previous = steps[#steps]
        local chance = ns.ProfessionSkillChance(id, recipe, skill, false)
        if previous and previous.recipe.id == recipe.id then previous.finish = skill + 1; previous.crafts = previous.crafts + 1 / chance
        else steps[#steps + 1] = {recipe = recipe, start = skill, finish = skill + 1, crafts = 1 / chance} end
    end
    return {steps = steps, missing = missing, start = start, target = target}
end

local legacyChoices = ns.ProfessionChoices
function ns.ProfessionChoices()
    if ns.professionSelection then return legacyChoices() end
    local ids, choices = {}, {}
    for _, id in ipairs(order) do ids[#ids + 1] = id end
    table.sort(ids, function(a, b)
        if (ns.professionData[a] ~= nil) ~= (ns.professionData[b] ~= nil) then return ns.professionData[a] ~= nil end
        return ns.ProfessionFacts(a).name < ns.ProfessionFacts(b).name
    end)
    for _, id in ipairs(ids) do
        local key, facts, info = id, ns.ProfessionFacts(id), ns.professionData[id]
        choices[#choices + 1] = {title = facts.name, category = info and "YOUR PROFESSION" or "CRAFTING PROFESSION", profession = id,
            count = info and ("Skill " .. (info.skill or "?") .. " / " .. (info.maximum or "?")) or "Learn & level",
            detail = info and "Next craft, materials & rank training" or "Learn the profession and plan your materials",
            icon = facts.icon, click = function() ns.ShowProfessionViewer(key) end}
    end
    return choices
end

function ns.QueueProfessionUpdate(readRecipes)
    ns.professionReadQueued = ns.professionReadQueued or readRecipes
    if ns.professionUpdateQueued then return end
    ns.professionUpdateQueued = true
    local function update()
        ns.professionUpdateQueued = nil
        if ns.RouteInCombat() then ns.professionUpdateDeferred = true; return end
        ns.professionRevision = (ns.professionRevision or 0) + 1
        stockCache, cachedRevision = {}, ns.professionRevision
        if ns.professionReadQueued and ns.professionWindowOpen then ns.ReadProfessionRecipes() end
        -- Recipe-window snapshots can lag behind the primary skill line. The
        -- fresh skill-line read wins; colors retain their own snapshot skill.
        ns.ReadProfessionSkills()
        ns.professionReadQueued = nil
        if ns.routeSelection and ns.routeSelection.mode == "profession" then ns.UpdateProfessionRoute(ns.routeSelection); ns.UpdateNavigation() end
        if ns.professionViewer and ns.professionViewer:IsShown() then ns.RefreshProfessionViewer() end
        if ns.RefreshProfessionShopping then ns.RefreshProfessionShopping() end
        if ns.RefreshAuctionGuideSearch then ns.RefreshAuctionGuideSearch() end
        ns.RenderProfessionGuide()
    end
    if C_Timer and type(C_Timer.After) == "function" then C_Timer.After(0.25, update) else update() end
end
local previousRegen = ns.handlers.PLAYER_REGEN_ENABLED
ns.On("PLAYER_REGEN_ENABLED", function(...)
    if previousRegen then previousRegen(...) end
    if ns.professionUpdateDeferred then ns.professionUpdateDeferred = nil; ns.QueueProfessionUpdate(true) end
    if ns.ResumeProfessionPreview then ns.ResumeProfessionPreview() end
end)

-- Optional quotes from a merchant the player opened. Extended-currency goods
-- are excluded; a stack's price is divided by its purchase quantity.
ns.professionVendorQuotes = {}
function ns.ReadProfessionVendorPrices()
    if type(GetMerchantNumItems) ~= "function" or type(GetMerchantItemInfo) ~= "function" or type(GetMerchantItemLink) ~= "function" then return end
    local count = ns.ReadPublic(GetMerchantNumItems)
    if not ns.GuideInteger(count, 1000) then return end
    local npc = ns.SafeTitle(ns.ReadPublic(UnitName, "npc"))
    for slot = 1, math.min(count, 200) do
        local link = ns.ReadPublic(GetMerchantItemLink, slot)
        local itemID = ns.Public(link) and type(link) == "string" and tonumber(string.match(link, "item:(%d+)"))
        local okay, name, texture, copper, quantity, available, usable, extended = pcall(GetMerchantItemInfo, slot)
        if okay and ns.GuideInteger(itemID) and itemID > 0 and ns.GuideInteger(copper, 9000000000000)
            and copper > 0 and ns.GuideInteger(quantity, 1000) and quantity > 0 and ns.Public(extended) and extended == false then
            ns.professionVendorQuotes[itemID] = {unitPrice = copper / quantity, npc = npc}
        end
    end
    ns.QueueProfessionUpdate()
end
ns.On("MERCHANT_SHOW", function() ns.ReadProfessionVendorPrices() end)
