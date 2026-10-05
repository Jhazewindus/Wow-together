local addonName, ns = ...

-- Actual NPC offers supply pickup geography, never objective/turn-in geography
-- or completion credit. Coordinates are the player's position during dialogue.
local LOCATION_LIMIT = 2048
local locationCount = 0

function ns.InitializeNPCPickups()
    local _, build = ns.ReadPublic(GetBuildInfo)
    build = build and tostring(build) or "unknown"
    ns.db.npcPickupBuilds = type(ns.db.npcPickupBuilds) == "table" and ns.db.npcPickupBuilds or {}
    local locations = ns.db.npcPickupBuilds[build]
    if type(locations) ~= "table" then locations = {}; ns.db.npcPickupBuilds[build] = locations end
    ns.npcPickupLocations, ns.npcPickupBuild, locationCount = locations, build, 0
    for id, point in pairs(locations) do
        if not ns.GuideInteger(id) or id <= 0 or not ns.ValidTravelPoint(point)
            or not ns.GuideInteger(point.entityID) or point.entityID <= 0 or not ns.SafeTitle(point.name)
            or locationCount >= LOCATION_LIMIT then locations[id] = nil
        else locationCount = locationCount + 1 end
    end
end

function ns.NPCPickupPoint(id)
    local point = ns.npcPickupLocations and ns.npcPickupLocations[id]
    return ns.ValidTravelPoint(point) and point or nil
end

function ns.RecordNPCPickupLocations(npcID, offered)
    if not ns.npcPickupLocations or not ns.GuideInteger(npcID) or npcID <= 0 then return end
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    if not ns.GuideInteger(mapID) or mapID <= 0 then return end
    local position = ns.PlayerPoint(mapID)
    if not ns.ValidTravelPoint(position) then return end
    local first, surname = ns.ReadPublic(UnitName, "npc")
    local name = ns.SafeTitle(first)
    surname = ns.SafeTitle(surname)
    name = name and (name .. (surname and (" " .. surname) or "")) or "Quest giver"
    for id in pairs(offered) do
        if ns.npcPickupLocations[id] or locationCount < LOCATION_LIMIT then
            if not ns.npcPickupLocations[id] then locationCount = locationCount + 1 end
            ns.npcPickupLocations[id] = {mapID = mapID, x = position.x, y = position.y,
                entityID = npcID, name = name, npc = true}
        end
    end
end

function ns.NPCPickupStop(stop, key, observedVisit)
    if stop.kind ~= "a" then return end
    local point = ns.NPCPickupPoint(stop.id)
    if not point or not stop.unknownLocation and not observedVisit then return end
    local current = {}; for name, value in pairs(stop) do current[name] = value end
    current.fixedStepKey = ns.GuideStepKey(stop)
    current.mapID, current.x, current.y = point.mapID, point.x, point.y
    current.entityID, current.npcName, current.targetName = point.entityID, point.name, point.name
    current.label, current.unknownLocation = "Talk to " .. point.name, nil
    current.published, current.observedPickup, current.approximate = nil, true, true
    return current
end

local function pickupStep(guide, id)
    for _, stop in ipairs(guide.fixedPlan or {}) do
        if stop.id == id and stop.kind == "a" then return stop end
    end
    for _, record in ipairs(guide.records or {}) do
        if record.id == id then
            local quest = ns.CatalogueQuest(id)
            return ns.PublishedGuideStop(record, quest and quest.starts and quest.starts[1], "a")
                or {id = id, kind = "a", title = record.title, mapID = record.mapID, unknownLocation = true}
        end
    end
end

local function usefulPickup(guide, id, query)
    if ns.active[id] or ns.CatalogueCompletion(ns.self, id, query) ~= false
        or not ns.LevelingQuestEnabled(id) then return end
    local step = pickupStep(guide, id)
    if not step or #ns.FilterGuideStages({step}) == 0 then return end
    if ns.CatalogueAllowed(id, ns.profile, ns.self, query) == false then return end
    return step
end

function ns.RecordGuideNPCVisit(offered)
    local guide = ns.routeSelection
    if not guide or guide.mode == "travel" or guide.mode == "dungeon" or not ns.Option("nearbyPickups") then return end
    local ids, query = {}, ns.NewQuestQuery()
    -- The selected guide is the scope. Unrelated NPC quests are left manual.
    for _, record in ipairs(guide.records or {}) do
        if offered[record.id] and usefulPickup(guide, record.id, query)
            and ns.CatalogueAllowed(record.id, ns.profile, ns.self, query) == true
            and ns.NPCPickupPoint(record.id) then ids[#ids + 1] = record.id end
    end
    if #ids == 0 then return end
    local same = #(guide.npcVisitPickupIDs or {}) == #ids
    for index, id in ipairs(ids) do if not guide.npcVisitPickupIDs or guide.npcVisitPickupIDs[index] ~= id then same = false end end
    if not same then guide.npcVisitPickupIDs = ids end
    ns.navigationPreview, ns.routeSignature = nil, nil
    ns.ResetTravelPath()
end

function ns.AddNPCVisitPickups(guide, route, query)
    if not route or not ns.Option("nearbyPickups") or not guide.npcVisitPickupIDs then return route end
    query = query or ns.NewQuestQuery()
    local pickups, included = {}, {}
    for _, id in ipairs(guide.npcVisitPickupIDs) do
        local step = usefulPickup(guide, id, query)
        local current = step and ns.NPCPickupStop(step, ns.self, true)
        if current and not included[id] then
            current.memberKey, current.forPlayer, current.npcVisitPickup = ns.self, "You", true
            pickups[#pickups + 1], included[id] = current, true
        end
    end
    if #pickups == 0 then return route end
    table.sort(pickups, function(a, b)
        if a.guideStep and b.guideStep and a.guideStep ~= b.guideStep then return a.guideStep < b.guideStep end
        return a.id < b.id
    end)
    local function prepend(stops)
        local result = {}; for _, step in ipairs(pickups) do result[#result + 1] = step end
        for _, step in ipairs(stops or {}) do
            if step.kind ~= "a" or not included[step.id] or step.memberKey and step.memberKey ~= ns.self then
                result[#result + 1] = step
            end
        end
        return result
    end
    route.stops = prepend(route.stops)
    if route.previewStops then route.previewStops = prepend(route.previewStops) end
    route.mapID, route.npcVisitCount = pickups[1].mapID, #pickups
    route.pendingReason, route.pendingStop = nil, nil
    guide.pendingReason = nil
    return route
end

function ns.RefreshNPCGuideProgress(id)
    ns.ReadQuests()
    if ns.GuideInteger(id) then ns.offered[id] = nil end
    ns.autoGossipAttempt, ns.autoAcceptAttempt = nil, nil
    if ns.routeSelection and not ns.routePlanning and not ns.guideScanning then
        ns.UpdateSelectedRoute(nil, ns.NewQuestQuery())
        ns.Refresh()
    end
end

function ns.NPCPickupDiagnostics(output)
    output("Observed pickup locations: " .. locationCount .. " for this build; dialogue positions are approximate.")
    output("NPC visit pickups remaining: " .. (ns.selectedRoute and ns.selectedRoute.npcVisitCount or 0) .. ". Objective order is retained.")
end

function ns.ExportNPCPickupLocations()
    local result = {build = ns.npcPickupBuild, approximate = true, source = "npc-dialogue", quests = {}}
    local ids = {}; for id in pairs(ns.npcPickupLocations or {}) do ids[#ids + 1] = id end
    table.sort(ids)
    for _, id in ipairs(ids) do
        local point = ns.npcPickupLocations[id]
        result.quests[#result.quests + 1] = {questID = id, npcID = point.entityID, npcName = point.name,
            mapID = point.mapID, x = point.x, y = point.y}
    end
    return result
end
