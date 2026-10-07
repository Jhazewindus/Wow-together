local addonName, ns = ...

-- A read-only front page, using the same eligibility and crafting planners.
-- Providers return cards; only their clicked actions may activate a guide.
local providers, revision, cached = {}, 0, nil
ns.recommendationErrors = {}

function ns.RegisterRecommendationProvider(key, provider)
    if type(key) ~= "string" or not string.match(key, "^[a-z]+$") or type(provider) ~= "function" then return false end
    providers[key], revision, cached = provider, revision + 1, nil
    return true
end

local function signature()
    local p, values = ns.profile or {}, {revision, ns.objectiveDisplayRevision or 0,
        ns.professionRevision or 0, ns.catalogueLocationRevision or 0, ns.questHistoryCount or 0,
        ns.db and ns.db.questLearning and ns.db.questLearning.revision or 0}
    for _, key in ipairs({"level", "faction", "classID", "raceID", "mapID"}) do values[#values + 1] = tostring(p[key] or "") end
    values[#values + 1] = tostring(ns.Option("classQuests"))
    values[#values + 1] = tostring(ns.Option("soloMode"))
    values[#values + 1] = tostring(ns.Option("useLearnedQuests"))
    values[#values + 1] = ns.routeSelection and ns.routeSelection.key or ""
    for _, id in ipairs({171, 164, 333, 202, 165, 197}) do
        local info = ns.professionData[id]
        values[#values + 1] = id .. ":" .. (info and tostring(info.skill) .. ":" .. tostring(info.maximum)
            .. ":" .. ns.ProfessionGoal(id) .. ":" .. tostring(info.recipeRefreshPending) or "none")
    end
    return table.concat(values, "|")
end

function ns.RecommendedItems(query)
    local stamp = signature()
    if cached and cached.catalogue == ns.catalogue and cached.signature == stamp then return cached.items, cached.states end
    query = query or ns.NewQuestQuery()
    local items, states, keys = {}, {}, {}
    for key in pairs(providers) do keys[#keys + 1] = key end
    table.sort(keys)
    for _, key in ipairs(keys) do
        local okay, result, state = pcall(providers[key], query)
        if okay then
            ns.recommendationErrors[key] = nil; states[key] = state
            for _, item in ipairs(result or {}) do items[#items + 1] = item end
        else ns.recommendationErrors[key] = tostring(result) end
    end
    table.sort(items, function(a, b)
        if a.priority ~= b.priority then return a.priority > b.priority end
        return a.key < b.key
    end)
    -- Native completion/map reads can fill caches during this pass. Keep only
    -- cards, not the per-pass query or its character/party snapshots.
    cached = {catalogue = ns.catalogue, signature = signature(), items = items, states = states}
    return items, states
end

ns.RegisterRecommendationProvider("leveling", function(query)
    local p = ns.profile
    if not p or not ns.GuideInteger(p.level, 255) or p.level < 1 or p.faction ~= "Horde" and p.faction ~= "Alliance" then
        return {}, "Your character details are loading."
    end
    local level, _, name = ns.PartyLevelFloor(query)
    if level and level >= 60 then return {}, "Level cap reached. Explore dungeons or continue your professions." end
    for _, guide in ipairs(ns.LevelingGuideChoices(true, query, "party")) do
        if guide.hasPoint and ns.GuideLevelSuitable(guide, query, true) then
            local active, remaining, completed = 0, 0, 0
            for _, record in ipairs(guide.records) do
                if ns.ClassQuestEnabled(record.id) and ns.CatalogueIdentityAllowed(record.id, p) == true
                    and not ns.GuideQuestSkipped(record.id) then
                    if ns.PartyQuestFinished(record.id, query) then completed = completed + 1
                    else
                        remaining = remaining + 1
                        if ns.active[record.id] then active = active + 1 end
                    end
                end
            end
            local here = (guide.homeMapID or guide.mapID) == p.mapID
            local reason = here and "Useful quest chains in your current zone." or "Useful quest chains near your level."
            reason = reason .. " " .. remaining .. " quests left in this section"
                .. (active > 0 and " • " .. active .. " already in your log." or ".")
            if name and name ~= "You" then reason = reason .. " Fits " .. name .. " at level " .. level .. "." end
            local running = ns.routeSelection and ns.routeSelection.key == guide.key
                and ns.selectedRoute and not ns.selectedRoute.complete
            return {{key = guide.key, kind = "leveling", priority = 1000, title = guide.zone,
                category = "RECOMMENDED LEVELING", count = "Lv " .. (guide.mainLevelLow or guide.rangeLow)
                    .. "–" .. (guide.mainLevelHigh or guide.rangeHigh), detail = reason, guide = guide,
                progress = completed .. " / " .. (completed + remaining) .. " quests completed",
                progressValue = completed, progressTotal = completed + remaining,
                action = running and "Continue guide" or "Start guide",
                start = running and ns.OpenGuideWindow or function() ns.RequestStartRoute(guide) end,
                secondary = "Quest list", inspect = function() ns.ShowGuideQuestList(guide) end}}, "ready"
        end
    end
    return {}, "No suitable unfinished zone guide is ready. Browse leveling guides to explore your next zone."
end)

ns.RegisterRecommendationProvider("professions", function()
    local result = {}
    for _, id in ipairs({171, 164, 333, 202, 165, 197}) do
        local info = ns.professionData[id]
        local facts = info and ns.ProfessionFacts(id)
        if info and facts then
            local goal = ns.ProfessionGoal(id)
            local route = ns.routeSelection and ns.routeSelection.mode == "profession" and ns.routeSelection.professionID == id and ns.selectedRoute
            if not route then
                route = ns.BuildProfessionGuideRoute({key = "profession:" .. id, title = facts.name .. " crafting guide",
                    professionID = id, targetSkill = goal, records = {}, mode = "profession"})
            end
            local nextStep = route and route.stops and route.stops[1]
            local ready = ns.GuideInteger(info.skill, 1000) and info.skill < goal
            local running = ns.routeSelection and ns.routeSelection.mode == "profession"
                and ns.routeSelection.professionID == id and ns.selectedRoute and not ns.selectedRoute.complete
            local key = id
            result[#result + 1] = {key = "profession:" .. id, kind = "professions", priority = ready and 500 or 400,
                title = facts.name, category = ready and "YOUR CRAFTING GUIDE" or "YOUR PROFESSION", icon = facts.icon,
                count = "Skill " .. (info.skill or "?") .. " / " .. (info.maximum or "?"),
                detail = nextStep and nextStep.label or "Check your profession window for your next craft.",
                progress = "Your skill goal: " .. goal, progressValue = info.skill or 0, progressTotal = goal,
                action = running and "Continue guide" or ready and "Start guide" or "View guide",
                start = running and ns.OpenGuideWindow or ready and function() ns.StartProfessionGuide(key, goal) end
                    or function() ns.ShowProfessionViewer(key) end,
                secondary = "View guide", inspect = function() ns.ShowProfessionViewer(key) end,
                professionID = id, guide = {mode = "crafting"}}
        end
    end
    return result, #result == 0 and "Learn a crafting profession to get a personal recommendation here." or "ready"
end)
