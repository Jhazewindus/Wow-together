local addonName, ns = ...

ns.professionData = {}
ns.professionStatus = "Open your profession window to load recipe guides."
ns.professionBatch = 5

local function difficultyName(value)
    local enum = Enum and Enum.TradeskillRelativeDifficulty
    if enum then
        for _, name in ipairs({"Optimal", "Medium", "Easy", "Trivial"}) do
            if enum[name] ~= nil and value == enum[name] then return name == "Optimal" and "Orange" or (name == "Medium" and "Yellow" or (name == "Easy" and "Green" or "Grey")) end
        end
    end
    return "Difficulty unknown"
end

function ns.ReadProfessionRecipes()
    if ns.RouteInCombat() then return end
    if not C_TradeSkillUI or type(C_TradeSkillUI.GetAllRecipeIDs) ~= "function" or type(C_TradeSkillUI.GetRecipeInfo) ~= "function" then
        ns.professionStatus = "Recipe data is unavailable in this beta build. Personal profession quests remain available."; return
    end
    local info = ns.ReadPublic(C_TradeSkillUI.GetChildProfessionInfo)
    if type(info) ~= "table" or not ns.GuideInteger(info.professionID) or info.professionID <= 0 then
        info = ns.ReadPublic(C_TradeSkillUI.GetBaseProfessionInfo)
    end
    if type(info) ~= "table" or not ns.GuideInteger(info.professionID) or info.professionID <= 0 then return end
    local name = ns.SafeTitle(info.professionName)
    if not name then return end
    local list = ns.ReadPublic(C_TradeSkillUI.GetAllRecipeIDs)
    if type(list) ~= "table" then return end
    local recipes, count = {}, 0
    for _, id in ipairs(list) do
        count = count + 1; if count > 400 then break end
        if ns.GuideInteger(id) and id > 0 then
            local recipe = ns.ReadPublic(C_TradeSkillUI.GetRecipeInfo, id)
            if type(recipe) == "table" and ns.Public(recipe.learned) and recipe.learned == true
                and ns.Public(recipe.canSkillUp) and recipe.canSkillUp == true and ns.SafeTitle(recipe.name) then
                recipes[#recipes + 1] = {id = id, name = ns.SafeTitle(recipe.name),
                    difficulty = ns.GuideInteger(recipe.relativeDifficulty) and recipe.relativeDifficulty or nil,
                    skillUps = ns.GuideInteger(recipe.numSkillUps) and recipe.numSkillUps or nil}
            end
        end
    end
    ns.professionData[info.professionID] = {id = info.professionID, name = name, recipes = recipes,
        skill = ns.GuideInteger(info.skillLevel) and info.skillLevel or nil,
        maximum = ns.GuideInteger(info.maxSkillLevel) and info.maxSkillLevel or nil}
    ns.professionStatus = #recipes > 0 and "Live recipes loaded. Choose a small batch; refresh after crafting." or "No learned recipes with confirmed skill gains. Check your profession trainer."
end

function ns.RecipeMaterials(id, crafts)
    local schematic = C_TradeSkillUI and ns.ReadPublic(C_TradeSkillUI.GetRecipeSchematic, id, false)
    if type(schematic) ~= "table" or not ns.Public(schematic.reagentSlotSchematics) or type(schematic.reagentSlotSchematics) ~= "table" then
        return {}, nil, true
    end
    local result, total, incomplete = {}, 0, false
    for index, slot in ipairs(schematic.reagentSlotSchematics) do
        if index > 12 then incomplete = true; break end
        if ns.Public(slot) and type(slot) == "table" and ns.Public(slot.required) and slot.required == true then
            if ns.GuideInteger(slot.quantityRequired, 10000) and ns.Public(slot.reagents) and type(slot.reagents) == "table" then
                local best, cost, bestOwned
                for option, reagent in ipairs(slot.reagents) do
                    if option > 32 then break end
                    if ns.Public(reagent) and type(reagent) == "table" and ns.GuideInteger(reagent.itemID) and reagent.itemID > 0 then
                        local have = ns.ItemOwned(reagent.itemID)
                        local need = slot.quantityRequired * crafts
                        local missing = have and math.max(0, need - have) or nil
                        local quote = ns.marketQuotes[reagent.itemID]
                        local price = missing == 0 and 0 or (quote and missing and quote.unitPrice * missing)
                        local owned = missing == 0
                        if not best or (owned and not bestOwned) or (owned == bestOwned and price and (not cost or price < cost)) then
                            best, cost, bestOwned = {itemID = reagent.itemID, name = ns.ItemName(reagent.itemID), need = need, have = have,
                                missing = missing, source = #slot.reagents > 1 and "One reagent alternative; verify your chosen quality/item" or "Recipe reagent • check vendor / AH"}, price, owned
                        end
                    end
                end
                if best then
                    result[#result + 1] = best
                    if total and cost then total = total + cost else total = nil end
                else incomplete, total = true, nil end
            else incomplete, total = true, nil end
        elseif not ns.Public(slot) or type(slot) ~= "table" or not ns.Public(slot.required) or slot.required ~= false then incomplete, total = true, nil end
    end
    -- The same reagent in separate required slots must subtract bag stock once.
    local merged, list = {}, {}
    for _, item in ipairs(result) do
        if merged[item.itemID] then merged[item.itemID].need = merged[item.itemID].need + item.need
        else merged[item.itemID] = item end
    end
    total = 0
    for id, item in pairs(merged) do
        item.missing = item.have and math.max(0, item.need - item.have) or nil
        local quote = ns.marketQuotes[id]
        if item.missing == 0 then
        elseif quote and item.missing and total then total = total + item.missing * quote.unitPrice
        else total = nil end
        list[#list + 1] = item
    end
    if incomplete then total = nil end
    table.sort(list, function(a, b) return a.itemID < b.itemID end)
    return list, total, incomplete
end

function ns.ProfessionChoices()
    ns.professionBatch = ns.Option("professionBatch")
    local choices = {}
    if not ns.professionSelection then
        for id, info in pairs(ns.professionData) do
            choices[#choices + 1] = {title = info.name .. " crafting guide", category = "PERSONAL / LIVE RECIPES",
                detail = "Skill " .. (info.skill or "?") .. " / " .. (info.maximum or "?") .. " • " .. #info.recipes .. " learned recipes can raise skill.",
                action = "Choose guide", click = function() ns.professionSelection = "live:" .. id; ns.Refresh() end}
        end
        local groups = {}
        for id, quest in pairs(ns.catalogue.quests) do
            if ns.IsProfessionQuest(id) then
                local slug = string.sub(quest.categoryPath, 13)
                groups[slug] = (groups[slug] or 0) + 1
            end
        end
        local keys = {}; for slug in pairs(groups) do keys[#keys + 1] = slug end; table.sort(keys)
        for _, slug in ipairs(keys) do
            local key = slug
            choices[#choices + 1] = {title = string.gsub(key, "^%l", string.upper) .. " quest guide", category = "PERSONAL / PROFESSION QUESTS",
                detail = groups[key] .. " published quests. These do not appear in party leveling guides.", action = "Choose guide",
                click = function() ns.professionSelection = "quests:" .. key; ns.Refresh() end}
        end
        table.insert(choices, 1, {title = "Your next profession skill points", category = "PERSONAL / GET STARTED",
            detail = ns.professionStatus .. " AH costs use only public searches you make. No automatic shopping or crafting.",
            action = "Refresh recipes", click = function() ns.ReadProfessionRecipes(); ns.Refresh() end})
    else
        choices[#choices + 1] = {title = "Profession guides", category = "PERSONAL / CHOOSE ANOTHER GUIDE", detail = ns.professionStatus,
            action = "Back to guides", click = function() ns.professionSelection = nil; ns.Refresh() end}
        local id = tonumber(string.match(ns.professionSelection, "^live:(%d+)$"))
        if id then
            local info = ns.professionData[id]
            if info then
                local recipes = {}
                local enum = Enum and Enum.TradeskillRelativeDifficulty
                for _, recipe in ipairs(info.recipes) do
                    local rank = 3
                    if enum then
                        if enum.Optimal ~= nil and recipe.difficulty == enum.Optimal then rank = 0 elseif enum.Medium ~= nil and recipe.difficulty == enum.Medium then rank = 1 elseif enum.Easy ~= nil and recipe.difficulty == enum.Easy then rank = 2 end
                    end
                    recipes[#recipes + 1] = {recipe = recipe, rank = rank}
                end
                table.sort(recipes, function(a, b) if a.rank ~= b.rank then return a.rank < b.rank end; return a.recipe.id < b.recipe.id end)
                local compared = {}
                for index = 1, math.min(24, #recipes) do
                    local entry = recipes[index]
                    entry.materials, entry.cost, entry.incomplete = ns.RecipeMaterials(entry.recipe.id, ns.professionBatch)
                    compared[#compared + 1] = entry
                end
                table.sort(compared, function(a, b)
                    if a.rank ~= b.rank then return a.rank < b.rank end
                    if (a.cost ~= nil) ~= (b.cost ~= nil) then return a.cost ~= nil end
                    if a.cost and a.cost ~= b.cost then return a.cost < b.cost end
                    return a.recipe.id < b.recipe.id
                end)
                for index = 1, math.min(12, #compared) do
                    local entry, recipe = compared[index], compared[index].recipe
                    choices[#choices + 1] = {title = recipe.name, category = index == 1 and "RECOMMENDED / PERSONAL CRAFTING STEP" or "PERSONAL / CRAFTING ALTERNATIVE",
                        detail = difficultyName(recipe.difficulty) .. " • plan " .. ns.professionBatch .. " crafts • missing material cost " .. (entry.cost and ns.MoneyText(entry.cost) or "unknown")
                            .. (entry.incomplete and " • some reagent data missing" or "") .. ". Craft yourself; refresh when difficulty changes. Skill-ups can vary.",
                        action = "Materials / buy list", click = function() ns.ShowShoppingList(entry.materials, recipe.name .. " • " .. ns.professionBatch .. " crafts") end}
                end
            end
        else
            local slug = string.match(ns.professionSelection, "^quests:(.+)$")
            local ids = {}; for id, quest in pairs(ns.catalogue.quests) do if quest.categoryPath == "professions/" .. (slug or "") then ids[#ids + 1] = id end end; table.sort(ids)
            for _, id in ipairs(ids) do
                local quest, record = ns.CatalogueQuest(id), ns.CatalogueRecord(id)
                if ns.CatalogueIdentityAllowed(id, ns.profile) ~= false then
                    local guide = {key = "personal:" .. id, title = quest.title, records = {record}, target = record, focusKey = ns.self, personal = true}
                    local route = ns.BuildGuideRoute(guide, false)
                    choices[#choices + 1] = {title = quest.title, category = "PERSONAL / PROFESSION QUEST", guide = guide,
                        detail = "Quest level " .. (quest.level or "?") .. " • requires " .. (quest.minLevel or "?") .. ". " .. (ns.Completed(id) == true and "Completed." or "Check recipe, skill and quest prerequisites."),
                        action = #route.stops > 0 and "Show personal route" or "View quest details",
                        click = function() if #route.stops > 0 then ns.ShowGuideOnMap(guide) else ns.ShowQuestDetails(id) end end}
                end
            end
        end
    end
    return choices
end

function ns.RenderProfessionGuide() if ns.filter == "professions" then ns.Refresh() end end

function ns.InitializeProfessionGuides()
    ns.On("TRADE_SKILL_SHOW", function() ns.ReadProfessionRecipes(); ns.RenderProfessionGuide() end)
    ns.On("TRADE_SKILL_LIST_UPDATE", function() ns.ReadProfessionRecipes(); ns.RenderProfessionGuide() end)
    ns.On("BAG_UPDATE_DELAYED", function()
        ns.RefreshShoppingList(); ns.RenderProfessionGuide()
        -- Collection tools/items can change without a quest-log objective
        -- update (for example, the carcass used to summon Ishamuhale).
        ns.ScheduleGuideProgress()
    end)
    ns.On("ITEM_DATA_LOAD_RESULT", function(id, success)
        if ns.GuideInteger(id) and ns.pendingItems[id] and ns.Public(success) and success == true then
            ns.pendingItems[id] = nil; ns.RefreshShoppingList(); ns.RenderProfessionGuide()
        end
    end)
end
