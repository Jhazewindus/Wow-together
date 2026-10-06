local addonName, ns = ...

-- Personal ride measurements and read-only native connecting stops. No flight
-- is unlocked, selected or taken here. See TRAVEL_DATA.md for sources/limits.
ns.flightTimingStatus = "No flight timed this session."
local function finite(value)
    return ns.Public(value) and type(value) == "number" and value == value
        and value > -math.huge and value < math.huge
end
local function state() return ns.db and ns.db.flights and ns.db.flights[ns.self] end
local function routeKey(route)
    if not ns.Public(route) or type(route) ~= "table" or #route < 2 or #route > 33 then return end
    local ids = {}
    for _, id in ipairs(route) do
        if not ns.GuideInteger(id) or id <= 0 then return end
        ids[#ids + 1] = tostring(id)
    end
    return table.concat(ids, ":")
end

function ns.ReadNativeFlightRoute(slot, source, destination, slots)
    local count = ns.ReadPublic(GetNumRoutes, slot)
    if not ns.GuideInteger(count, 32) or count < 1 or type(TaxiGetNodeSlot) ~= "function" then return end
    local route, seen = {source}, {[source] = true}
    for index = 1, count do
        local start = ns.ReadPublic(TaxiGetNodeSlot, slot, index, true)
        local finish = ns.ReadPublic(TaxiGetNodeSlot, slot, index, false)
        if not ns.GuideInteger(start, 1000) or not ns.GuideInteger(finish, 1000) then return end
        start, finish = slots[start], slots[finish]
        if start ~= route[#route] or not finish or seen[finish] then return end
        route[#route + 1], seen[finish] = finish, true
    end
    if route[#route] == destination then return route end
end

function ns.FlightDuration(source, destination, air, geometry)
    local flights = state()
    local edge = flights and flights.edges[source .. ":" .. destination]
    local timing = flights and flights.timings[source .. ":" .. destination]
    local signature = edge and routeKey(edge.route)
    local build = ns.flightTimingBuild
    if timing and timing.validated == true and finite(timing.mean) and timing.mean > 0 and timing.mean < 7200
        and build and timing.build == build and timing.routeKey == signature then
        return timing.mean, true, "Timed flight"
    end
    if signature then
        geometry = geometry or {}
        local length = 0
        for index = 2, #edge.route do
            local a, b = flights.nodes[edge.route[index - 1]], flights.nodes[edge.route[index]]
            local segment = a and b and ns.TravelPointDistance(a.point, b.point, geometry)
            if not finite(segment) then length = nil; break end
            length = length + segment
        end
        if length and length > 0 then return length / 32 * 1.35, false, "Connecting-stop estimate" end
    end
    if finite(air) and air > 0 then return air / 32 * 1.35, false, "Distance estimate" end
end

function ns.PrepareFlightTiming(selection)
    ns.flightMeasurementRevision = (ns.flightMeasurementRevision or 0) + 1
    selection.selectedAt = ns.ReadPublic(GetTime)
    local flights = state()
    local edge = flights and flights.edges[selection.source .. ":" .. selection.destination]
    selection.routeKey, selection.build = edge and routeKey(edge.route), ns.flightTimingBuild
    selection.basis = selection.basis or (selection.estimated and "Distance estimate" or "Timed flight")
end

function ns.RecordFlightTiming(selection, started, ended)
    if not selection or not finite(started) or not finite(ended) or ended - started <= 1 or ended - started >= 7200 then
        ns.flightTimingStatus = "Ride not saved: departure or duration could not be confirmed."; return
    end
    if not selection.build or selection.build ~= ns.flightTimingBuild then
        ns.flightTimingStatus = "Ride not saved: matching client build could not be confirmed."; return
    end
    local flights = state()
    local destination = flights and flights.nodes[selection.destination]
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    local position = ns.PlayerPoint(mapID)
    local distance = destination and ns.TravelPointDistance(position, destination.point)
    if ns.ReadPublic(UnitIsGhost, "player") == true then
        ns.flightTimingStatus = "Ride not saved: interrupted by death."; return
    end
    if not finite(distance) or distance > 300 then
        ns.flightTimingStatus = "Ride not saved: arrival at the selected destination was not confirmed."; return false, true
    end
    local key, seconds = selection.source .. ":" .. selection.destination, ended - started
    local old = flights.timings[key]
    local reusable = old and old.validated == true and old.build == selection.build and old.routeKey == selection.routeKey
        and finite(old.mean) and ns.GuideInteger(old.samples, 11) and old.samples > 0
    local samples = reusable and math.min(10, old.samples) or 0
    flights.timings[key] = {mean = ((reusable and old.mean or 0) * samples + seconds) / (samples + 1),
        samples = samples + 1, validated = true, build = selection.build, routeKey = selection.routeKey}
    ns.flightTimingStatus = "Timed " .. selection.name .. ": " .. math.floor(seconds + 0.5)
        .. " seconds; arrival confirmed; " .. (samples + 1) .. " sample(s)."
        .. (finite(selection.expected) and (" Previous " .. (selection.estimated and "estimate" or "timing")
            .. ": " .. math.floor(selection.expected + 0.5) .. " seconds.") or "")
    return true
end

function ns.FinishFlightTiming(selection, started, ended)
    local saved, retry = ns.RecordFlightTiming(selection, started, ended)
    if saved or not retry or not C_Timer or type(C_Timer.After) ~= "function" then return end
    local generation = ns.flightMeasurementRevision
    local function check(attempt)
        if generation ~= ns.flightMeasurementRevision or ns.ReadPublic(UnitOnTaxi, "player") ~= false then return end
        local recorded, again = ns.RecordFlightTiming(selection, started, ended)
        if recorded then
            ns.travelRevision, ns.flightPlanCache = (ns.travelRevision or 0) + 1, nil
            ns.ResetTravelPath(); ns.RefreshTravelDirections()
        elseif again and attempt < 20 then C_Timer.After(0.1, function() check(attempt + 1) end) end
    end
    -- Use the original landing time even when GPS becomes public a moment later.
    C_Timer.After(0.1, function() check(1) end)
end

function ns.FlightTimingDiagnostics(output)
    local usable, legacy, routes = 0, 0, 0
    local flights = state()
    for _, timing in pairs(flights and flights.timings or {}) do
        if timing.validated == true and timing.build == ns.flightTimingBuild then usable = usable + 1
        else legacy = legacy + 1 end
    end
    for _, edge in pairs(flights and flights.edges or {}) do if routeKey(edge.route) then routes = routes + 1 end end
    output("Flight timing: " .. usable .. " arrival-validated timings on this build; " .. legacy
        .. " older/unverified timings retained; " .. routes .. " native connecting routes.")
    output("Flight recording: " .. ns.flightTimingStatus)
    local selection = ns.pendingFlight
    if selection then output("Selected flight: " .. selection.name .. "; " .. selection.basis .. "; "
        .. (finite(selection.expected) and math.floor(selection.expected + 0.5) .. " seconds" or "duration unknown") .. ".") end
end
