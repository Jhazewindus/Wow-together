local addonName, ns = ...

-- Companion adapter only: AzerothGPS remains a separately installed addon and
-- owns its router, map data, route drawing and direction arrow. Wow Together
-- continues to own guide selection and advances the destination as objectives
-- change. No AzerothGPS code, artwork or map data is bundled here.
local API_VERSION = 23
local lastRequest, lastStatus = nil, "Waiting for AzerothGPS or a guide route."
local active = false
local lastTarget, arrivedKey, overlaySignature, overlayPoints = nil, nil, nil, {}
local arrivalAPI
local OVERLAY_OWNER, OVERLAY_STOP_LIMIT = "WowTogether_GuideRoute", 24

local function finite(value)
    return ns.Public(value) and type(value) == "number" and value == value
        and value > -math.huge and value < math.huge
end

local function api()
    local candidate = _G.AzerothGPS
    if type(candidate) ~= "table" or type(candidate.version) ~= "number"
        or candidate.version < API_VERSION or type(candidate.MapToWorld) ~= "function"
        or type(candidate.RouteTo) ~= "function" then return nil end
    return candidate
end

local function setActive(value)
    value = value == true
    if active == value then return end
    active = value
    if ns.DrawRoute then ns.DrawRoute() end
end

function ns.AzerothGPSPathingActive()
    return active == true
end

function ns.AzerothGPSPathingStatus()
    return lastStatus
end

function ns.AzerothGPSPathingArrived()
    return lastTarget ~= nil and arrivedKey == lastTarget.key
end

local function clearOverlay(targetAPI)
    if not overlaySignature then return end
    overlaySignature, overlayPoints = nil, {}
    if targetAPI and type(targetAPI.SetOverlay) == "function" then
        pcall(targetAPI.SetOverlay, OVERLAY_OWNER, nil)
    end
end

local function updateGuideOverlay(targetAPI, route)
    if type(targetAPI.SetOverlay) ~= "function" then return end
    local parts, count = {}, math.min(#(route.stops or {}), OVERLAY_STOP_LIMIT)
    for index = 1, count do
        local stop = route.stops[index]
        parts[index] = table.concat({tostring(stop.mapID), tostring(stop.x), tostring(stop.y), tostring(stop.label)}, ":")
    end
    local signature = table.concat(parts, "|")
    if signature == overlaySignature then return end

    local points = {}
    for index = 1, count do
        local stop = route.stops[index]
        local mapID = tonumber(stop.mapID)
        if mapID and mapID > 0 and finite(stop.x) and finite(stop.y)
            and stop.x >= 0 and stop.x <= 1 and stop.y >= 0 and stop.y <= 1 then
            local okay, x, y, level = pcall(targetAPI.MapToWorld, mapID, stop.x, stop.y)
            if okay and finite(x) and finite(y) and finite(level) then
                points[#points + 1] = {x = x, y = y, level = level, index = index}
            end
        end
    end
    overlaySignature, overlayPoints = signature, points
    local okay = pcall(targetAPI.SetOverlay, OVERLAY_OWNER, function(ctx)
        for _, point in ipairs(overlayPoints) do
            if point.level == ctx.cont then
                if point.index == 1 then
                    ctx.Dot(point.x, point.y, {1, 0.82, 0.30}, 12, 1)
                elseif point.index == 2 then
                    ctx.Dot(point.x, point.y, {0.95, 0.62, 0.27}, 9, 0.9)
                else
                    ctx.Dot(point.x, point.y, {0.45, 0.72, 1}, 7, 0.72)
                end
            end
        end
    end)
    if not okay then overlaySignature = nil end
end

local function onArrive(info)
    if type(info) ~= "table" or not lastTarget or not (active or lastStatus == "Waiting for the AzerothGPS route confirmation.")
        or not finite(info.x) or not finite(info.y) or not finite(info.cont) then return end
    if info.cont ~= lastTarget.level or math.abs(info.x - lastTarget.x) > 8 or math.abs(info.y - lastTarget.y) > 8 then return end
    arrivedKey = lastTarget.key
    lastStatus = "Arrived at this guide stop; complete its objective to advance."
    setActive(false)
    if ns.UpdateNavigation then ns.UpdateNavigation() end
end

local function registerArrival(targetAPI)
    if targetAPI ~= arrivalAPI and type(targetAPI) == "table" and type(targetAPI.OnArrive) == "function" then
        arrivalAPI = targetAPI
        pcall(targetAPI.OnArrive, OVERLAY_OWNER, onArrive)
    end
end

function ns.SyncAzerothGPSPathing(state)
    local mode = ns.Option("pathingEngine")
    if mode == "native" then
        setActive(false)
        clearOverlay(api())
        lastTarget, arrivedKey = nil, nil
        lastRequest, lastStatus = nil, "Using Wow Together pathing (selected in settings)."
        return
    end

    local targetAPI = api()
    if not targetAPI then
        setActive(false)
        clearOverlay(nil)
        lastTarget, arrivedKey = nil, nil
        lastRequest = nil
        lastStatus = mode == "azerothgps"
            and "AzerothGPS pathing requested; install AzerothGPS 1.4.1 or later (API 23). Using Wow Together for now."
            or "AzerothGPS not detected; using Wow Together pathing."
        return
    end
    if not ns.routeSelection or not ns.selectedRoute or ns.selectedRoute.complete then
        setActive(false)
        clearOverlay(targetAPI)
        lastTarget, arrivedKey = nil, nil
        lastRequest, lastStatus = nil, "AzerothGPS ready; no active Wow Together guide."
        return
    end
    updateGuideOverlay(targetAPI, ns.selectedRoute)
    registerArrival(targetAPI)
    local stop = state and state.stop or ns.selectedRoute.stops and ns.selectedRoute.stops[1]
    if not stop or state and (state.busy or state.idle) then
        setActive(false)
        lastRequest = nil
        lastTarget, arrivedKey = nil, nil
        lastStatus = "AzerothGPS ready; waiting for the next mapped guide stop."
        return
    end
    if state and (state.flight or state.stop and state.stop.kind == "corpse")
        or ns.ReadPublic(UnitOnTaxi, "player") == true then
        setActive(false)
        lastRequest = nil
        lastTarget, arrivedKey = nil, nil
        lastStatus = "AzerothGPS paused during flight or corpse recovery."
        return
    end
    if ns.RouteInCombat and ns.RouteInCombat() then
        setActive(false)
        lastRequest = nil
        lastTarget, arrivedKey = nil, nil
        lastStatus = "AzerothGPS route update queued until combat ends."
        return
    end

    local mapID = tonumber(stop.mapID)
    if not mapID or mapID <= 0 or not finite(stop.x) or not finite(stop.y)
        or stop.x < 0 or stop.x > 1 or stop.y < 0 or stop.y > 1 then
        setActive(false)
        lastRequest = nil
        lastTarget, arrivedKey = nil, nil
        lastStatus = "This guide stop has no map coordinate; Wow Together pathing remains active."
        return
    end

    local okay, x, y, level = pcall(targetAPI.MapToWorld, mapID, stop.x, stop.y)
    if not okay or not finite(x) or not finite(y) or not finite(level) then
        setActive(false)
        lastRequest = nil
        lastTarget, arrivedKey = nil, nil
        lastStatus = "AzerothGPS could not convert this guide stop; using Wow Together pathing."
        return
    end
    local label = stop.label or stop.title or stop.targetName or "Wow Together guide stop"
    local key = table.concat({tostring(level), string.format("%.1f", x), string.format("%.1f", y), tostring(label)}, ":")
    lastTarget = {key = key, level = level, x = x, y = y}
    if lastRequest == key then
        setActive(lastStatus == "AzerothGPS is routing the current guide leg.")
        return
    end

    local called, accepted, asking = pcall(targetAPI.RouteTo, level, x, y, nil, label)
    lastRequest, arrivedKey = key, nil
    if not called then
        setActive(false)
        lastStatus = "AzerothGPS route request failed; using Wow Together pathing."
        return
    end
    if accepted == true then
        setActive(true)
        lastStatus = "AzerothGPS is routing the current guide leg."
    elseif asking == true then
        setActive(false)
        lastStatus = "Waiting for the AzerothGPS route confirmation."
    else
        setActive(false)
        lastStatus = "AzerothGPS did not accept this route; using Wow Together pathing."
    end
end

function ns.AzerothGPSPathingDiagnostics(output)
    output("Path routing: " .. lastStatus)
end

ns.hooks.diagnostics[#ns.hooks.diagnostics + 1] = ns.AzerothGPSPathingDiagnostics

ns.On("ADDON_LOADED", function(name)
    if name == "AzerothGPS" then
        lastRequest = nil
        registerArrival(api())
        if ns.UpdateNavigation then ns.UpdateNavigation() end
    end
end)

registerArrival(api())
