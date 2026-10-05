local addonName, ns = ...

function ns.ReadPublic(fn, ...)
    if type(fn) ~= "function" then return end
    local okay, a, b, c = pcall(fn, ...)
    if okay and ns.Public(a) and ns.Public(b) and ns.Public(c) then return a, b, c end
end

function ns.IsProfessionQuest(id)
    local quest = ns.CatalogueQuest(id)
    return quest and quest.categoryPath and string.sub(quest.categoryPath, 1, 12) == "professions/" or false
end

function ns.IsDungeonQuest(id)
    local quest = ns.CatalogueQuest(id)
    return quest and (quest.questType == "Dungeon" or (quest.categoryPath and string.sub(quest.categoryPath, 1, 9) == "dungeons/")) or false
end

function ns.IsClassQuest(id)
    local quest = ns.CatalogueQuest(id)
    return quest and ((quest.classMask and quest.classMask > 0)
        or (quest.categoryPath and string.sub(quest.categoryPath, 1, 8) == "classes/")) or false
end

function ns.ClassQuestLabel(id)
    if not ns.IsClassQuest(id) then return nil end
    local quest = ns.CatalogueQuest(id)
    if quest.categoryPath and string.sub(quest.categoryPath, 1, 8) == "classes/" then
        return "Class quest: " .. string.gsub(string.sub(quest.categoryPath, 9), "^%l", string.upper)
    end
    local classes, names = {}, {[1] = "Warrior", [2] = "Paladin", [3] = "Hunter", [4] = "Rogue", [5] = "Priest",
        [6] = "Death Knight", [7] = "Shaman", [8] = "Mage", [9] = "Warlock", [10] = "Monk", [11] = "Druid", [12] = "Demon Hunter", [13] = "Evoker"}
    if bit and type(bit.band) == "function" and type(bit.lshift) == "function" then
        for id, name in pairs(names) do if bit.band(quest.classMask or 0, bit.lshift(1, id - 1)) ~= 0 then classes[#classes + 1] = name end end
    end
    table.sort(classes)
    return #classes > 0 and ("Class quest: " .. table.concat(classes, ", ")) or "Class quest • restriction needs checking"
end

function ns.LevelingQuestEnabled(id)
    return not ns.IsProfessionQuest(id) and not ns.IsDungeonQuest(id)
        and (not ns.IsClassQuest(id) or ns.Option("classQuests"))
end

function ns.PlayerPoint(mapID)
    local point = C_Map and ns.ReadPublic(C_Map.GetPlayerMapPosition, mapID, "player")
    local x, y
    if point then x, y = ns.ReadPublic(point.GetXY, point) end
    if type(x) == "number" and type(y) == "number" and x >= 0 and x <= 1 and y >= 0 and y <= 1 then
        return {mapID = mapID, x = x, y = y}
    end
end

function ns.NormalizedDistance(a, b)
    if not a or not b or a.mapID ~= b.mapID then return math.huge end
    return math.sqrt(((a.x - b.x) * 1.5)^2 + (a.y - b.y)^2)
end

function ns.WalkingDistance(mapID, a, b)
    local width, height
    if C_Map then width, height = ns.ReadPublic(C_Map.GetMapWorldSize, mapID) end
    if type(width) == "number" and type(height) == "number" and width > 0 and height > 0
        and width < 1000000 and height < 1000000 then
        return math.sqrt(((a.x - b.x) * width)^2 + ((a.y - b.y) * height)^2)
    end
end

local indexedCatalogue, maps
local function mapRecords(mapID)
    if ns.catalogue ~= indexedCatalogue then
        maps, indexedCatalogue = {}, ns.catalogue
        for id, quest in pairs(ns.catalogue.quests) do
            local start = quest.starts and quest.starts[1]
            local finish = quest.ends and quest.ends[1]
            local map = finish and finish.mapID or (start and start.mapID)
            if map then maps[map] = maps[map] or {}; maps[map][#maps[map] + 1] = id end
        end
        for _, ids in pairs(maps) do table.sort(ids) end
    end
    return maps[mapID] or {}
end

local function focusPlayer()
    local key, level, ready = ns.self, ns.profile and ns.profile.level, true
    for _, person in ipairs(ns.PartyProfiles()) do
        local p = person.profile
        if not person.synced or not p or not p.level or p.level <= 0 then ready = false
        elseif not level or level <= 0 or p.level < level or (p.level == level and person.key < key) then key, level = person.key, p.level end
    end
    return key, level or 0, ready
end

function ns.LocalCircuitChoices()
    local mapID = ns.profile and ns.profile.mapID or 0
    local key, level, ready = focusPlayer()
    if mapID <= 0 or level <= 0 or not ready then return {} end
    local position, candidates = ns.PlayerPoint(mapID), {}
    local radius = ns.Option("circuitRadius")
    for _, id in ipairs(mapRecords(mapID)) do
        local quest = ns.CatalogueQuest(id)
        if ns.LevelingQuestEnabled(id) and not quest.objectiveLocationsIncomplete
            and (quest.level or 0) <= level + 2 then
            local record = ns.CatalogueRecord(id)
            local stages = ns.PartyRouteStages(record, key)
            local hasObjective, valid = false, #stages > 0
            local finish = quest.ends and quest.ends[1]
            for _, stop in ipairs(stages) do
                if stop.mapID ~= mapID or ns.NormalizedDistance(stop, finish) > radius * 2 then valid = false end
                if stop.kind == "q" then hasObjective = true end
            end
            if valid and finish and (hasObjective or stages[1].kind == "t") then
                local first = quest.starts and quest.starts[1] or stages[1]
                if first.mapID == mapID then
                    local nearby = not position or ns.NormalizedDistance(position, first) <= radius * 1.8
                    if nearby then candidates[#candidates + 1] = {record = record, first = first, finish = finish, stages = stages,
                        value = math.max(100, quest.xp or 300) / (1 + math.max(0, level - (quest.level or level) - 3)), xp = quest.xp} end
                end
            end
        end
    end
    table.sort(candidates, function(a, b)
        local da = position and ns.NormalizedDistance(position, a.first) or 0
        local db = position and ns.NormalizedDistance(position, b.first) or 0
        if da ~= db then return da < db end
        return a.record.id < b.record.id
    end)
    local choices, signatures = {}, {}
    -- Bound the search by local candidates, independent of global catalogue size.
    for anchorIndex = 1, math.min(40, #candidates) do
        local anchor, available = candidates[anchorIndex], {}
        for index = 1, math.min(80, #candidates) do
            local candidate = candidates[index]
            if ns.NormalizedDistance(candidate.finish, anchor.finish) <= radius * 0.45
                and ns.NormalizedDistance(candidate.first, anchor.first) <= radius then
                local walking = ns.NormalizedDistance(candidate.stages[1], anchor.finish)
                available[#available + 1] = {candidate = candidate, priority = candidate.value / (0.04 + walking)}
            end
        end
        table.sort(available, function(a, b)
            if a.priority ~= b.priority then return a.priority > b.priority end
            return a.candidate.record.id < b.candidate.record.id
        end)
        local records, ids, xp, unknown, score, stopCount = {}, {}, 0, 0, 0, 0
        for index = 1, #available do
            local c = available[index].candidate
            if #records < ns.Option("circuitLimit") and stopCount + #c.stages <= 20 then
                records[#records + 1], ids[#ids + 1] = c.record, c.record.id
                if c.xp then xp = xp + c.xp else unknown = unknown + 1 end
                score, stopCount = score + c.value, stopCount + #c.stages
            end
        end
        table.sort(ids)
        local signature = table.concat(ids, ",")
        if #records > 0 and not signatures[signature] then
            signatures[signature] = true
            local title = "Local circuit • " .. #records .. " quest" .. (#records > 1 and "s" or "")
            local hub = anchor.finish.name or ns.MapName(mapID)
            local group = {key = "circuit:" .. mapID .. ":" .. signature, title = title, kind = "Local XP circuit", mode = "circuit",
                mapID = mapID, records = records, target = records[1], focusKey = key, zone = ns.MapName(mapID), profilesReady = true,
                lowest = level, highest = level, xp = xp, xpUnknown = unknown, hasPoint = true, level = level, shared = 0,
                priority = 1000 + score / 50 - (position and ns.NormalizedDistance(position, anchor.first) * 400 or 0),
                reason = "Collect nearby quests, work their objectives, then return together around " .. hub .. ".",
                destination = "Finish in one local turn-in circuit."}
            local plan = ns.BuildCircuitRoute(group, true)
            group.nextStop, group.knownStops, group.missingStops = plan.stops[1], #plan.stops, plan.missing
            group.reason = group.reason .. " Listed quest XP: " .. xp .. (unknown > 0 and (" + " .. unknown .. " unknown rewards") or "") .. "; actual XP varies by level."
            if plan.walkingYards then group.reason = group.reason .. " Approx. " .. math.ceil(plan.walkingYards / 7 / 60) .. " walking minutes before terrain/combat." end
            choices[#choices + 1] = group
        end
    end
    table.sort(choices, function(a, b) if a.priority ~= b.priority then return a.priority > b.priority end; return a.key < b.key end)
    local result = {}
    for index = 1, math.min(3, #choices) do result[#result + 1] = choices[index] end
    return result
end

function ns.BuildCircuitRoute(guide, includeOrigin)
    local phases, missing, partial = {a = {}, q = {}, t = {}}, 0, false
    local mapID = guide.mapID or (guide.target and guide.target.mapID) or 0
    for _, record in ipairs(guide.records) do
        local stages = guide.personal and ns.RouteStages(record, ns.self) or ns.PartyRouteStages(record, guide.focusKey)
        if #stages == 0 then missing = missing + 1 end
        for _, stop in ipairs(stages) do
            if stop.mapID == mapID then phases[stop.kind][#phases[stop.kind] + 1] = stop else partial = true end
        end
    end
    local position = includeOrigin and ns.PlayerPoint(mapID) or nil
    local stops, last, yards = {}, position, position and 0 or nil
    for _, kind in ipairs({"a", "q", "t"}) do
        local remaining = phases[kind]
        while #remaining > 0 and #stops < 20 do
            local best, distance = 1, math.huge
            for index, stop in ipairs(remaining) do
                local d = last and ns.NormalizedDistance(last, stop) or index
                if d < distance then best, distance = index, d end
            end
            local stop = table.remove(remaining, best)
            if last then
                local length = ns.WalkingDistance(mapID, last, stop)
                if length and yards ~= nil then yards = yards + length else yards = nil end
            end
            stops[#stops + 1], last = stop, stop
        end
    end
    return {key = guide.key, title = guide.title, mapID = mapID, stops = stops, origin = position, focusKey = guide.focusKey,
        missing = missing, otherMaps = 0, limited = #phases.a + #phases.q + #phases.t, partial = partial, walkingYards = yards}
end
