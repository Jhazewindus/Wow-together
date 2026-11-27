local addonName, ns = ...

-- Companion adapter only: AzerothGPS remains a separately installed addon and
-- owns its router, map data, route drawing and direction arrow. Wow Together
-- continues to own guide selection and advances the destination as objectives
-- change. No AzerothGPS code, artwork or map data is bundled here.
local API_VERSION = 23
local lastRequest, lastStatus = nil, "Waiting for AzerothGPS or a guide route."
local active = false

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

function ns.SyncAzerothGPSPathing(state)
    local mode = ns.Option("pathingEngine")
    if mode == "native" then
        setActive(false)
        lastRequest, lastStatus = nil, "Using Wow Together pathing (selected in settings)."
        return
    end

    local targetAPI = api()
    if not targetAPI then
        setActive(false)
        lastRequest = nil
        lastStatus = mode == "azerothgps"
            and "AzerothGPS pathing requested; install AzerothGPS 1.4.1 or later (API 23). Using Wow Together for now."
            or "AzerothGPS not detected; using Wow Together pathing."
        return
    end
    if not ns.routeSelection or not ns.selectedRoute or ns.selectedRoute.complete then
        setActive(false)
        lastRequest, lastStatus = nil, "AzerothGPS ready; no active Wow Together guide."
        return
    end
    local stop = state and state.stop or ns.selectedRoute.stops and ns.selectedRoute.stops[1]
    if not stop or state and (state.busy or state.idle) then
        setActive(false)
        lastRequest = nil
        lastStatus = "AzerothGPS ready; waiting for the next mapped guide stop."
        return
    end
    if state and (state.flight or state.stop and state.stop.kind == "corpse")
        or ns.ReadPublic(UnitOnTaxi, "player") == true then
        setActive(false)
        lastRequest = nil
        lastStatus = "AzerothGPS paused during flight or corpse recovery."
        return
    end
    if ns.RouteInCombat and ns.RouteInCombat() then
        setActive(false)
        lastRequest = nil
        lastStatus = "AzerothGPS route update queued until combat ends."
        return
    end

    local mapID = tonumber(stop.mapID)
    if not mapID or mapID <= 0 or not finite(stop.x) or not finite(stop.y)
        or stop.x < 0 or stop.x > 1 or stop.y < 0 or stop.y > 1 then
        setActive(false)
        lastRequest = nil
        lastStatus = "This guide stop has no map coordinate; Wow Together pathing remains active."
        return
    end

    local okay, x, y, level = pcall(targetAPI.MapToWorld, mapID, stop.x, stop.y)
    if not okay or not finite(x) or not finite(y) or not finite(level) then
        setActive(false)
        lastRequest = nil
        lastStatus = "AzerothGPS could not convert this guide stop; using Wow Together pathing."
        return
    end
    local label = stop.label or stop.title or stop.targetName or "Wow Together guide stop"
    local key = table.concat({tostring(level), string.format("%.1f", x), string.format("%.1f", y), tostring(label)}, ":")
    if lastRequest == key then
        setActive(lastStatus == "AzerothGPS is routing the current guide leg.")
        return
    end

    local called, accepted, asking = pcall(targetAPI.RouteTo, level, x, y, nil, label)
    lastRequest = key
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
        if ns.UpdateNavigation then ns.UpdateNavigation() end
    end
end)
