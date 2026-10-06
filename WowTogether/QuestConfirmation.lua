local addonName, ns = ...

-- Uncertain branching pickups get directions to a giver, not acceptance credit.
-- A native waypoint is an explicit, narrowly scoped button action only.
local cached
function ns.CurrentQuestConfirmation()
    local route = ns.selectedRoute
    if not route or not ns.routeSelection or ns.guideScanning or ns.routePlanning or ns.navigationPreview then return end
    local pending = route.stops and route.stops[1] or route.pendingStop
    if not pending or pending.kind ~= "a" or pending.action == "start-item" or ns.GuideQuestSkipped(pending.id)
        or #ns.FilterGuideStages({pending}) == 0 then return end
    local quest = ns.CatalogueQuest(pending.id)
    if not quest or not quest.prerequisitesUnverified then return end
    local key = pending.memberKey or ns.self
    local member = key ~= ns.self and ns.members[key]
    local profile = key == ns.self and ns.profile or member and member.profile
    local active = key == ns.self and ns.active or member and member.active
    local now = ns.ReadPublic(GetTime)
    local timed = ns.Public(now) and type(now) == "number" and now == now and now > -math.huge and now < math.huge
    -- Quest/offer events refresh the revision. Reuse the same confirmation
    -- between movement ticks instead of polling quest history at arrow speed.
    if timed and cached and cached.route == route and cached.pending == pending and cached.quest == quest
        and cached.revision == ns.objectiveDisplayRevision and cached.active == active
        and now >= cached.time and now - cached.time < 1 then return cached.stop end
    if active and active[pending.id] or ns.CatalogueCompletion(key, pending.id) == true then return end
    local allowed, reason, code = ns.CataloguePickupCheck(pending.id, profile, key)
    if allowed ~= nil or code ~= "branching-prerequisite" then return end
    local result = {}; for name, value in pairs(pending) do result[name] = value end
    local point = ns.NPCPickupPoint(pending.id)
    if not point then
        for _, candidate in ipairs(quest and quest.starts or {}) do
            if candidate.npc and candidate.action ~= "start-item" and ns.ValidTravelPoint(candidate) then
                if not point or candidate.entityID == pending.entityID then point = candidate end
                if candidate.entityID == pending.entityID then break end
            end
        end
    end
    local reference = point
    if not reference then
        for _, candidate in ipairs(quest and quest.startRefs or {}) do
            if candidate.entityType == "npc" then reference = candidate; break end
        end
    end
    result.npcName = reference and ns.SafeTitle(reference.name) or ns.SafeTitle(pending.npcName) or ns.QuestGiverName(pending.id)
    result.entityID = reference and reference.entityID or pending.entityID
    result.kind, result.action, result.confirmation = "a", "confirm", true
    result.confirmationReason = reason
    result.label = "Talk to " .. (result.npcName or "the quest giver") .. " to confirm " .. result.title
    if point then
        result.mapID, result.x, result.y, result.unknownLocation = point.mapID, point.x, point.y, nil
        result.approximate = point == ns.NPCPickupPoint(pending.id) or result.approximate
    elseif not ns.ValidTravelPoint(result) or result.unknownLocation then
        result.x, result.y, result.unknownLocation = nil, nil, true
    end
    cached = timed and {route = route, pending = pending, quest = quest, active = active,
        revision = ns.objectiveDisplayRevision, time = now, stop = result} or nil
    return result
end

local function samePoint(a, b)
    return ns.ValidTravelPoint(a) and ns.ValidTravelPoint(b) and a.mapID == b.mapID
        and math.abs(a.x - b.x) < 0.00001 and math.abs(a.y - b.y) < 0.00001
end

local function savedWaypoints()
    if not ns.db or not ns.self then return end
    if type(ns.db.confirmationWaypoints) ~= "table" then ns.db.confirmationWaypoints = {} end
    return ns.db.confirmationWaypoints
end

function ns.ClearConfirmationWaypoint(current)
    local saved = savedWaypoints()
    local owned = ns.confirmationWaypoint or saved and saved[ns.self]
    if owned and (not ns.ValidTravelPoint(owned) or not ns.GuideInteger(owned.id) or owned.id <= 0) then
        ns.confirmationWaypoint = nil; if saved then saved[ns.self] = nil end; return
    end
    if not owned or current and current.id == owned.id and samePoint(current, owned) or ns.RouteInCombat() then return end
    -- Do not erase a waypoint the player placed after clicking our button.
    local waypoint = C_Map and ns.ReadPublic(C_Map.GetUserWaypoint)
    local usable = ns.Public(waypoint) and (type(waypoint) == "table" or type(waypoint) == "userdata")
    local mapID = usable and ns.ReadPublic(function() return waypoint.uiMapID end)
    local position = usable and ns.ReadPublic(function() return waypoint.position end)
    local x, y
    if position and ns.Public(position) and type(position.GetXY) == "function" then x, y = ns.ReadPublic(position.GetXY, position) end
    if samePoint(owned, {mapID = mapID, x = x, y = y}) and type(C_Map.ClearUserWaypoint) == "function" then C_Map.ClearUserWaypoint() end
    ns.confirmationWaypoint = nil
    if saved then saved[ns.self] = nil end
end

function ns.ShowConfirmationOnMap()
    local stop = ns.CurrentQuestConfirmation()
    if not stop or stop.unknownLocation or not ns.ValidTravelPoint(stop) or ns.RouteInCombat() then return false end
    if not WorldMapFrame and C_AddOns and type(C_AddOns.LoadAddOn) == "function" then C_AddOns.LoadAddOn("Blizzard_WorldMap") end
    if WorldMapFrame and type(WorldMapFrame.SetMapID) == "function" and type(WorldMapFrame.Show) == "function" then
        WorldMapFrame:SetMapID(stop.mapID); WorldMapFrame:Show()
        ns.AttachRouteProvider(); ns.DrawRoute()
    end
    local api = C_Map
    -- Requiring ownership/readback APIs also permits safe cleanup. Their
    -- presence is probed; ordinary routing never sets a native waypoint.
    if api and type(api.SetUserWaypoint) == "function" and type(api.GetUserWaypoint) == "function"
        and type(api.ClearUserWaypoint) == "function" and type(api.CanSetUserWaypointOnMap) == "function"
        and UiMapPoint and type(UiMapPoint.CreateFromCoordinates) == "function"
        and ns.ReadPublic(api.CanSetUserWaypointOnMap, stop.mapID) == true then
        local point = ns.ReadPublic(UiMapPoint.CreateFromCoordinates, stop.mapID, stop.x, stop.y)
        if point then
            api.SetUserWaypoint(point)
            ns.confirmationWaypoint = {id = stop.id, mapID = stop.mapID, x = stop.x, y = stop.y}
            local saved = savedWaypoints()
            if saved then saved[ns.self] = ns.confirmationWaypoint end
        end
    end
    return true
end
