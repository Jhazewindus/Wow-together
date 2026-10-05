local addonName, ns = ...

local KEY = "travel:orgrimmar"
local gates = {"ENTRANCE_C1454_517_858", "ENTRANCE_C1454_115_669"}

function ns.OrgrimmarTravelGuide()
    local profile = ns.profile
    if not profile or profile.faction ~= "Horde" or not ns.GuideInteger(profile.level)
        or profile.level < 1 or profile.level > 60 then return end
    local target = ns.travelData and ns.travelData.nodes[gates[1]]
    if not ns.ValidTravelPoint(target) then return end
    return {key = KEY, mode = "travel", personal = true, kind = "Travel guide", title = "Path to Orgrimmar",
        zone = "Orgrimmar", mapID = target.mapID, homeMapID = target.mapID, minLevel = 1, maxLevel = 60,
        rangeLow = 1, rangeHigh = 60, records = {}, hasPoint = true, knownStops = 1,
        target = {id = 0, title = "Orgrimmar"}, priority = -10000,
        search = "path to orgrimmar travel horde city", destination = "Reach Orgrimmar.",
        reason = "Levels 1–60. Take the quickest known route to Orgrimmar, using crossings, transports and confirmed flights. Travel times are estimates."}
end

function ns.GuideBrowserChoices(ignoreSearch, query)
    local choices = ns.LevelingGuideChoices(ignoreSearch, query)
    local low, high = ns.GuideLevelRange(nil, query)
    local search = ignoreSearch and "" or string.lower(ns.guideSearch or "")
    local travel = low <= 60 and high >= 1 and ns.OrgrimmarTravelGuide()
    if travel and (search == "" or string.find(travel.search, search, 1, true)) then choices[#choices + 1] = travel end
    return choices
end

function ns.BuildTravelGuideRoute(guide)
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    local position = ns.GuideInteger(mapID) and ns.PlayerPoint(mapID)
    local goal, best
    for _, id in ipairs(gates) do
        local gate = ns.travelData and ns.travelData.nodes[id]
        if ns.ValidTravelPoint(gate) then
            goal = goal or gate
            local path = position and ns.FindTravelPath(position, gate, ns.Option("suggestFlights"))
            if path and (not best or path.seconds < best.seconds) then goal, best = gate, path end
        end
    end
    local route = {key = guide.key, title = guide.title, mapID = guide.mapID, stops = {}, otherMaps = 0}
    if mapID == guide.mapID then route.complete = true; return route end
    if not goal or not position or not best then
        route.pendingReason = not position and "Player position unavailable; the travel guide is retained."
            or "No known travel connection from this zone to Orgrimmar. Scan again after reaching a mapped zone."
        return route
    end
    local stop = {id = 0, kind = "destination", action = "travel", title = guide.title,
        mapID = goal.mapID, x = goal.x, y = goal.y, label = "Enter Orgrimmar", guideStep = 1}
    route.stops, route.origin = {stop}, position
    route.estimatedSeconds = best.seconds
    return route
end

function ns.UpdateTravelGuide(guide, arrivalOnly)
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    if mapID == guide.mapID then
        if not (ns.selectedRoute and ns.selectedRoute.complete) then
            ns.CompleteSelectedGuide(guide, "Arrived in Orgrimmar.")
        end
        return
    end
    if arrivalOnly then return end
    -- Choose the gate at start, Scan, zone change or a flight-network change.
    -- Continuous movement is handled by the existing cached travel search.
    local route = ns.selectedRoute
    if route and route.travelOriginMap == mapID and route.travelRevision == ns.travelRevision then return end
    route = ns.BuildTravelGuideRoute(guide)
    route.travelOriginMap, route.travelRevision = mapID, ns.travelRevision
    ns.selectedRoute, ns.routePaused = route, route.pendingReason
    ns.ResetTravelPath(); ns.DrawRoute()
end

function ns.RestoreTravelGuide(key)
    if key == KEY then return ns.OrgrimmarTravelGuide() end
end
