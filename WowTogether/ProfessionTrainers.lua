local addonName, ns = ...

-- Positive observations from an opened trainer override old-world rank lists.
-- Never buy training, change trainer filters, or infer offerings from proximity.
local rankSpells = {
    [171] = {2259, 3101, 3464, 11611}, [164] = {2018, 3100, 3538, 9785},
    [333] = {7411, 7412, 7413, 13920}, [202] = {4036, 4037, 4038, 12656},
    [165] = {2108, 3104, 3811, 10662}, [197] = {3908, 3909, 3910, 12180},
}
local trainerOpen, spellRefreshQueued, pendingSpells, requestedSpells = false, false, {}, {}
local function build()
    local _, value = ns.ReadPublic(GetBuildInfo)
    return ns.SafeTitle(value)
end
function ns.ObservedProfessionTrainers(id, maximum, recipeID)
    local result, saved = {}, ns.professionSaved
    for _, trainer in pairs(saved and type(saved.trainers) == "table" and saved.trainers or {}) do
        if type(trainer) == "table" and trainer.professionID == id and trainer.build == build()
            and trainer.faction == (ns.profile and ns.profile.faction) and ns.ValidTravelPoint(trainer)
            and ns.SafeTitle(trainer.name) and ns.GuideInteger(trainer.maximum, 300)
            and (trainer.maximum >= maximum or recipeID and type(trainer.recipes) == "table" and trainer.recipes[recipeID] == true) then
            result[#result + 1] = trainer
        end
    end
    return result
end

function ns.ReadProfessionTrainer()
    if type(GetNumTrainerServices) ~= "function" or type(GetTrainerServiceInfo) ~= "function" or not ns.professionSaved then return end
    if type(IsTradeskillTrainer) == "function" and ns.ReadPublic(IsTradeskillTrainer) ~= true then return end
    local count = ns.ReadPublic(GetNumTrainerServices)
    local name = ns.SafeTitle(ns.ReadPublic(UnitName, "npc"))
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    local point = ns.GuideInteger(mapID) and ns.PlayerPoint(mapID)
    if not ns.GuideInteger(count, 1000) or not name or not point or not build() then return end
    local recipes, ranks = {}, {}
    for id, spells in pairs(rankSpells) do
        local facts, info = ns.ProfessionFacts(id), ns.professionData[id]
        local guide = ns.routeSelection
        if info or guide and guide.mode == "profession" and guide.professionID == id then
            for _, recipe in ipairs(facts.recipes) do
                recipes[recipe.name] = {id = id, recipeID = recipe.id}
                local live = info and info.known and info.known[recipe.id]
                if live and ns.SafeTitle(live.name) then recipes[live.name] = {id = id, recipeID = recipe.id} end
            end
        end
        for index, rank in ipairs(facts.ranks) do
            local spell = C_Spell and ns.ReadPublic(C_Spell.GetSpellInfo, spells[index])
            if not spell and C_Spell and type(C_Spell.GetSpellInfo) == "function"
                and type(C_Spell.RequestLoadSpellData) == "function" and not requestedSpells[spells[index]] then
                pendingSpells[spells[index]], requestedSpells[spells[index]] = true, true
                C_Spell.RequestLoadSpellData(spells[index])
            end
            local spellName = type(spell) == "table" and ns.SafeTitle(spell.name)
            local tag = {id = id, maximum = rank.maximum}
            ranks[rank.name .. " " .. facts.name] = tag
            if spellName then ranks[spellName .. ":" .. rank.name] = tag end
            ranks[facts.name .. ":" .. rank.name] = tag
        end
    end
    local observed = {}
    local function observation(id)
        if not observed[id] then observed[id] = {professionID = id, name = name, hub = ns.MapName(mapID), maximum = 0,
            mapID = mapID, x = point.x, y = point.y, faction = ns.profile and ns.profile.faction, build = build(), recipes = {}} end
        return observed[id]
    end
    for index = 1, count do
        local service, second, third = ns.ReadPublic(GetTrainerServiceInfo, index)
        service = ns.SafeTitle(service)
        -- Probe the documented return shapes, not WOW_PROJECT_ID: Mainline's
        -- second return is type; the older UI puts subtext there and type third.
        local kind
        if second == "available" or second == "used" or second == "unavailable" then kind = second
        elseif third == "available" or third == "used" or third == "unavailable" then kind = third end
        if service and (kind == "available" or kind == "used") then
            local recipe = recipes[service]
            if recipe then observation(recipe.id).recipes[recipe.recipeID] = true end
            local rank = ranks[service] or ns.SafeTitle(second) and ranks[service .. ":" .. second]
            if rank then local row = observation(rank.id); row.maximum = math.max(row.maximum, rank.maximum) end
        end
    end
    local saved = ns.professionSaved
    if type(saved.trainers) ~= "table" then saved.trainers = {} end
    for id, row in pairs(observed) do
        local key = id .. ":" .. mapID .. ":" .. name
        local previous = saved.trainers[key]
        if type(previous) == "table" and previous.build == row.build then
            if ns.GuideInteger(previous.maximum, 300) then row.maximum = math.max(row.maximum, previous.maximum) end
            for recipeID, offered in pairs(type(previous.recipes) == "table" and previous.recipes or {}) do
                if ns.GuideInteger(recipeID) and offered == true then row.recipes[recipeID] = true end
            end
        end
        local total = 0; for _ in pairs(saved.trainers) do total = total + 1 end
        if total < 64 or previous then saved.trainers[key] = row end
    end
    if next(observed) then ns.QueueProfessionUpdate() end
end
ns.On("TRAINER_SHOW", function() trainerOpen = true; ns.ReadProfessionTrainer() end)
ns.On("TRAINER_UPDATE", ns.ReadProfessionTrainer)
ns.On("TRAINER_CLOSED", function() trainerOpen = false end)
local previousSpell = ns.handlers.SPELL_DATA_LOAD_RESULT
ns.On("SPELL_DATA_LOAD_RESULT", function(id, success)
    if previousSpell then previousSpell(id, success) end
    if not ns.GuideInteger(id) or not pendingSpells[id] then return end
    pendingSpells[id] = nil
    if not trainerOpen or not ns.Public(success) or success ~= true or spellRefreshQueued then return end
    spellRefreshQueued = true
    local function refresh()
        spellRefreshQueued = false
        if trainerOpen then ns.ReadProfessionTrainer() end
    end
    if C_Timer and type(C_Timer.After) == "function" then C_Timer.After(0.2, refresh) else refresh() end
end)
