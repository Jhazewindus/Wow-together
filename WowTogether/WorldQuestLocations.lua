local addonName, ns = ...

-- Convert identity-matched older-world source points with the client's own
-- map transform. Three published Forever anchors must confirm its convention.
-- The planning context owns caches; no character position or progress is used.
local function finite(value)
    return ns.Public(value) and type(value) == "number" and value == value and math.abs(value) < math.huge
end

local function project(world, mapID, context, swapped)
    if not C_Map or type(C_Map.GetMapPosFromWorldPos) ~= "function" or type(CreateVector2D) ~= "function" then return end
    context.projections = context.projections or {}
    local key = mapID .. ":" .. world.continent .. ":" .. world.worldX .. ":" .. world.worldY .. ":" .. (swapped and "yx" or "xy")
    if context.projections[key] ~= nil then return context.projections[key] or nil end
    context.work = (context.work or 0) + 1
    if context.cooperative and context.work % 80 == 0 then coroutine.yield() end
    local map, vector = ns.ReadPublic(C_Map.GetMapPosFromWorldPos, world.continent,
        CreateVector2D(swapped and world.worldY or world.worldX, swapped and world.worldX or world.worldY), mapID)
    local result
    if ns.Public(map) and map == mapID and ns.Public(vector) and (type(vector) == "table" or type(vector) == "userdata") then
        local x, y = ns.ReadPublic(vector.GetXY, vector)
        if finite(x) and finite(y) and x >= 0 and x <= 1 and y >= 0 and y <= 1 then result = {mapID = mapID, x = x, y = y} end
    end
    context.projections[key] = result or false
    return result
end

local function convention(continent, context)
    context.verified = context.verified or {}
    if context.verified[continent] ~= nil then return context.verified[continent] end
    local counts = {0, 0}
    for _, anchor in ipairs(ns.worldQuestChecks and ns.worldQuestChecks[continent] or {}) do
        for index = 1, 2 do
            local point = project(anchor, anchor.mapID, context, index == 2)
            if point and math.abs(point.x - anchor.x) <= 0.02 and math.abs(point.y - anchor.y) <= 0.02 then
                counts[index] = counts[index] + 1
                if counts[index] >= 3 then context.verified[continent] = index; return index end
            end
        end
    end
    context.verified[continent] = false
    return false
end

local function inside(world, mapID, context, swapped)
    context.bounds = context.bounds or {}
    local box = context.bounds[mapID]
    if box == nil then
        box = false
        if C_Map and type(C_Map.GetWorldPosFromMapPos) == "function" and type(CreateVector2D) == "function" then
            local ac, a = ns.ReadPublic(C_Map.GetWorldPosFromMapPos, mapID, CreateVector2D(0, 0))
            local bc, b = ns.ReadPublic(C_Map.GetWorldPosFromMapPos, mapID, CreateVector2D(1, 1))
            if ns.GuideInteger(ac) and ac == bc and a and b and (type(a) == "table" or type(a) == "userdata")
                and (type(b) == "table" or type(b) == "userdata") then
                local ax, ay = ns.ReadPublic(a.GetXY, a)
                local bx, by = ns.ReadPublic(b.GetXY, b)
                if finite(ax) and finite(ay) and finite(bx) and finite(by) then
                    box = {continent = ac, left = math.min(ax, bx), right = math.max(ax, bx),
                        bottom = math.min(ay, by), top = math.max(ay, by)}
                end
            end
        end
        context.bounds[mapID] = box
    end
    if not box then return true end -- Projection itself remains the authority.
    local x, y = swapped and world.worldY or world.worldX, swapped and world.worldX or world.worldY
    return box.continent == world.continent and x >= box.left and x <= box.right and y >= box.bottom and y <= box.top
end

local function candidate(reference, quest, context)
    local entity = ns.questEntities and ns.questEntities[reference.entityType]
        and ns.questEntities[reference.entityType][reference.entityID]
    if not entity then return end
    if not entity.worldPoints then
        entity.worldPoints = {}
        for _, point in ipairs(entity.worldLocations or {}) do
            entity.worldPoints[#entity.worldPoints + 1] = point.continent and point
                or {continent = point[1], worldX = point[2], worldY = point[3]}
        end
    end
    context.maps = context.maps or {}
    local maps = context.maps[quest.mapID or 0]
    if not maps then
        maps = {}
        if ns.GuideInteger(quest.mapID) and quest.mapID > 0 then maps[#maps + 1] = quest.mapID end
        local others = {}
        for id in pairs(ns.KnownZoneMaps()) do if id ~= quest.mapID then others[#others + 1] = id end end
        table.sort(others); for _, id in ipairs(others) do maps[#maps + 1] = id end
        context.maps[quest.mapID or 0] = maps
    end
    local anchor = quest.starts and quest.starts[1] or quest.ends and quest.ends[1]
    local best, cost
    for _, mapID in ipairs(maps) do
        for _, world in ipairs(entity.worldPoints) do
            local orientation = convention(world.continent, context)
            if orientation and inside(world, mapID, context, orientation == 2) then
                local point = project(world, mapID, context, orientation == 2)
                if point then
                    local distance = anchor and anchor.mapID == mapID and ns.NormalizedDistance(anchor, point) or 0
                    local value = (mapID == quest.mapID and 0 or 10) + distance
                    if not best or value < cost then best, cost = point, value end
                end
            end
        end
        -- The actual home-zone transform found this entity; other map views
        -- don't improve its spawn and shouldn't add unnecessary API calls.
        if best and best.mapID == quest.mapID then break end
    end
    if best then
        -- Cached projection coordinates are shared; entity/item annotations
        -- must never mutate a point another quest already uses.
        local result = {}; for key, value in pairs(best) do result[key] = value end
        best = result
        best.entityID, best.entityType = reference.entityID, reference.entityType
        best.name, best.npc = entity.name ~= "" and entity.name or reference.name, reference.entityType == "npc" or nil
        best.worldFallback = true
        return best
    end
end

local function itemPoint(reference, quest, context)
    local item = ns.questEntities and ns.questEntities.item[reference.entityID]
    local point, targets, bestName = nil, {}, 0
    local itemName = string.gsub(string.lower(reference.name or ""), "[^%w]", "")
    for _, target in ipairs(quest.npcTargets or {}) do targets[target.entityID] = true end
    local explicit = next(targets) ~= nil
    for pass = 1, 2 do
        for _, source in ipairs(item and item.sources or {}) do
            local appropriate = source.action ~= "loot" or not source.minlevel or not quest.level or source.minlevel <= quest.level + 5
            local named = targets[source.entityID] == true
            if appropriate and (not explicit or pass == 1 and named or pass == 2) then
                local location = candidate(source, quest, context)
                local name = string.gsub(string.lower(source.name or ""), "[^%w]", "")
                local nameRank = #name >= 5 and string.find(itemName, name, 1, true) and #name or 0
                local home = location and location.mapID == quest.mapID
                -- When the named source is unmapped, a fallback must stay in
                -- the quest's home zone, rather than send a low-level player
                -- to a common item's unrelated high-level drop source.
                if location and (pass == 1 or home) and (not point or home and point.mapID ~= quest.mapID
                    or location.mapID == point.mapID and (nameRank > bestName
                    or nameRank == bestName and quest.starts and quest.starts[1]
                    and quest.starts[1].mapID == location.mapID
                    and ns.NormalizedDistance(quest.starts[1], location) < ns.NormalizedDistance(quest.starts[1], point))) then
                    point, location.action, bestName = location, source.action, nameRank
                end
            end
        end
        if point or not explicit then break end
    end
    if point then point.itemID, point.itemName = reference.entityID, reference.name end
    return point
end

function ns.ResolveWorldQuestLocations(id, context)
    local quest = ns.CatalogueQuest(id)
    if not quest or not quest.legacyFactsSource or quest.foreverStatus ~= "unchanged" or not quest.worldReferences then return end
    context = context or {}
    for _, role in ipairs({"starts", "ends"}) do
        if not quest[role] or #quest[role] == 0 then
            for _, reference in ipairs(quest.worldReferences[role] or {}) do
                local point = reference.entityType == "item" and itemPoint(reference, quest, context)
                    or candidate(reference, quest, context)
                if point then
                    if role == "starts" and reference.entityType == "item" then point.sourceAction, point.action = point.action, "start-item" end
                    quest[role] = {point}; break
                end
            end
        end
    end
    quest.objectives = quest.objectives or {}
    local missing = {}
    for _, reference in ipairs(quest.worldReferences.requirements or {}) do
        local found = false
        for _, point in ipairs(quest.objectives) do
            if reference.entityType == "item" and (point.itemID == reference.entityID or point.itemName == reference.name)
                or reference.entityType ~= "item" and point.entityID == reference.entityID then found = true; break end
        end
        if not found then
            local point
            if reference.entityType == "item" then
                point = itemPoint(reference, quest, context)
            else point = candidate(reference, quest, context) end
            if point then
                point.quantity = reference.quantity
                if reference.action and (reference.action ~= "collect" or not point.action) then point.action = reference.action end
                point.useItemName, point.spellID = reference.useItemName, reference.spellID
                point.objectiveKey = reference.entityType .. ":" .. reference.entityID
                quest.objectives[#quest.objectives + 1] = point
                if point.npc then
                    quest.npcTargets = quest.npcTargets or {}
                    quest.npcTargets[#quest.npcTargets + 1] = {entityID = point.entityID, name = point.name,
                        npc = true, action = point.action, itemName = point.itemName}
                end
                if point.action == "buy" then
                    for _, item in ipairs(quest.requiredItems or {}) do if item.itemID == reference.entityID then item.buyable = true end end
                end
            else missing[#missing + 1] = reference end
        end
    end
    quest.missingRequirements = #missing > 0 and missing or nil
    if #missing > 0 then quest.objectiveLocationsIncomplete = true
    elseif #(quest.worldReferences.requirements or {}) > 0 and not quest.otherLocationsIncomplete then quest.objectiveLocationsIncomplete = nil end
end
