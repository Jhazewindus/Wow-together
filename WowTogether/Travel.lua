local addonName, ns = ...

ns.travelStatus = "Open a flight master's map to learn this character's flight network."
ns.flightDiscoveryStatus = "Map unlock flags have not been checked this session."
ns.flightMapStatus = "No flight-master map read this session."
local flightMapOpen, flightMapGeneration, discoveryPending = false, 0, false

local function number(value)
    return ns.Public(value) and type(value) == "number" and value == value
        and value > -math.huge and value < math.huge
end

local function point(mapID, vector)
    if not ns.GuideInteger(mapID) or mapID <= 0 or not ns.Public(vector)
        or (type(vector) ~= "table" and type(vector) ~= "userdata") then return end
    local x, y = ns.ReadPublic(vector.GetXY, vector)
    if not number(x) or not number(y) or x < 0 or x > 1 or y < 0 or y > 1 then return end
    return {mapID = mapID, x = x, y = y}
end

local function world(p)
    if not p or not C_Map or type(CreateVector2D) ~= "function" then return end
    local continent, vector = ns.ReadPublic(C_Map.GetWorldPosFromMapPos, p.mapID, CreateVector2D(p.x, p.y))
    if not ns.GuideInteger(continent) or not vector then return end
    local x, y = ns.ReadPublic(vector.GetXY, vector)
    if number(x) and number(y) then return {continent = continent, x = x, y = y} end
end

local function distance(a, b)
    if type(a) == "table" and type(b) == "table" and a.continent == b.continent
        and number(a.x) and number(a.y) and number(b.x) and number(b.y) then
        return math.sqrt((a.x - b.x)^2 + (a.y - b.y)^2)
    end
end

local function localPoint(mapID, p)
    if not p or not C_Map or type(CreateVector2D) ~= "function" then return p end
    local continent, vector = ns.ReadPublic(C_Map.GetWorldPosFromMapPos, p.mapID, CreateVector2D(p.x, p.y))
    if not continent or not vector then return p end
    local map, position = ns.ReadPublic(C_Map.GetMapPosFromWorldPos, continent, vector, mapID)
    return point(map, position) or p
end

local function flights() return ns.db.flights and ns.db.flights[ns.self] end

local function savedPoint(p)
    return type(p) == "table" and ns.GuideInteger(p.mapID) and p.mapID > 0
        and number(p.x) and number(p.y) and p.x >= 0 and p.x <= 1 and p.y >= 0 and p.y <= 1
end

local function counts()
    local known, located, edges = 0, 0, 0
    local state = flights()
    for _, node in pairs(state and state.nodes or {}) do
        if node.known == true then
            known = known + 1
            if node.point then located = located + 1 end
        end
    end
    for _ in pairs(state and state.edges or {}) do edges = edges + 1 end
    return known, located, edges
end

local function changed()
    ns.travelRevision, ns.flightPlanCache = (ns.travelRevision or 0) + 1, nil
    -- Discovery can run during a boat/zeppelin zone change. Keep the crossing.
    local path = ns.travelPath
    if not path or path.transportIndex ~= path.cursor then ns.ResetTravelPath() end
end

local function destinationPoint(p, published)
    if not p or not published or p.mapID == published.mapID then return p end
    local projected = localPoint(published.mapID, p)
    return projected and projected.mapID == published.mapID and projected
        or {mapID = published.mapID, x = published.x, y = published.y}
end

local function storeNode(info, mapID, ownMap, known, current, reachable)
    if not ns.Public(info) or type(info) ~= "table" or not ns.GuideInteger(info.nodeID) or info.nodeID <= 0 then return end
    local id, state = info.nodeID, flights()
    local old = state.nodes[id] or {}
    local published = ns.travelData and ns.travelData.nodes["TAXI_" .. id]
    local name = ns.SafeTitle(info.name) or old.name or published and ns.SafeTitle(published.name)
    if not name then return end
    local p = point(mapID, ns.Public(info.position) and info.position)
    -- A continent flight-map point belongs to the destination's zone, not
    -- the zone of the flight master currently being visited. Keep it connected
    -- to that zone's walking graph; preserve actual client coordinates where
    -- the public projection succeeds.
    if not current then p = destinationPoint(p, published) end
    if not p and published then p = {mapID = published.mapID, x = published.x, y = published.y} end
    if current then p = ns.PlayerPoint(ownMap) or p end
    local confirmed = known ~= nil or old.unlockConfirmed == true
    local factions = Enum and Enum.FlightPathFaction
    local faction = old.faction or published and published.faction
    if factions and ns.Public(info.faction) and type(info.faction) == "number" then
        if info.faction == factions.Horde then faction = "Horde"
        elseif info.faction == factions.Alliance then faction = "Alliance"
        elseif info.faction == factions.Neutral then faction = "Both" end
    end
    -- A confirmed reachable flight is stronger evidence than a later map
    -- discovery flag. Keep that stronger evidence if the two sources conflict;
    -- taking a flight still checks the open menu itself.
    if known == false and old.known == true and old.reachabilityConfirmed == true then
        known = true
        ns.flightCacheConflicts = (ns.flightCacheConflicts or 0) + 1
    end
    if known == nil then known = old.known == true end
    state.nodes[id] = {id = id, name = name, point = p or old.point,
        world = p and world(p) or old.world, known = known, unlockConfirmed = confirmed, faction = faction,
        reachabilityConfirmed = reachable == true or old.reachabilityConfirmed == true}
    if known == false then
        for key, edge in pairs(state.edges) do
            if edge.source == id or edge.destination == id then state.edges[key] = nil end
        end
    end
    return id
end

local function factionMatches(info)
    local values = Enum and Enum.FlightPathFaction
    if not values or not ns.Public(info.faction) then return nil end
    local faction = ns.profile and ns.profile.faction or ns.ReadPublic(UnitFactionGroup, "player")
    local own = faction == "Horde" and values.Horde or faction == "Alliance" and values.Alliance
    if not number(own) or not number(values.Neutral) then return nil end
    return info.faction == own or info.faction == values.Neutral
end

function ns.ReadKnownFlightPaths()
    if not flights() then return end
    if not C_TaxiMap or type(C_TaxiMap.GetTaxiNodesForMap) ~= "function" then
        ns.flightDiscoveryStatus = "GetTaxiNodesForMap unavailable; confirm unlocks at flight masters."; return
    end
    local ownMap = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    local mapID, seen, reads, flags, skipped = ownMap, {}, 0, 0, 0
    -- Public parent maps reach the current continent without scanning the world.
    for _ = 1, 6 do
        if not ns.GuideInteger(mapID) or mapID <= 0 or seen[mapID] then break end
        seen[mapID] = true
        local nodes = ns.ReadPublic(C_TaxiMap.GetTaxiNodesForMap, mapID)
        if type(nodes) == "table" then
            reads = reads + 1
            for index, info in ipairs(nodes) do
                if index > 512 then break end
                if ns.Public(info) and type(info) == "table" then
                    local matches = factionMatches(info)
                    if matches ~= false and ns.Public(info.isUndiscovered) and type(info.isUndiscovered) == "boolean" then
                        -- Without faction metadata, do not add an unowned enemy
                        -- flight master as a nearby unlock recommendation.
                        if info.isUndiscovered == false or matches == true then
                            if storeNode(info, mapID, ownMap, not info.isUndiscovered) then flags = flags + 1 end
                        end
                    elseif matches ~= false then skipped = skipped + 1 end
                end
            end
        end
        local info = C_Map and ns.ReadPublic(C_Map.GetMapInfo, mapID)
        mapID = type(info) == "table" and ns.GuideInteger(info.parentMapID) and info.parentMapID or nil
    end
    if flags > 0 then changed() end
    local known = counts()
    ns.flightDiscoveryStatus = reads .. " map reads; " .. flags .. " public unlock flags; " .. skipped .. " unknown flags; " .. known .. " known paths saved."
    if flags > 0 then
        ns.travelStatus = known .. " unlocked paths recognized. Open a flight master's map to confirm reachable connections."
        ns.RefreshTravelDirections()
    end
end

function ns.ScheduleFlightDiscovery()
    if not ns.db or discoveryPending or not C_Timer or type(C_Timer.After) ~= "function" then return end
    discoveryPending = true
    C_Timer.After(0.2, function() discoveryPending = false; ns.ReadKnownFlightPaths() end)
end

local function taxiMapID()
    -- Blizzard's FlightMapMixin uses the GLOBAL GetTaxiMapID(), not a C_ API.
    local id = ns.ReadPublic(GetTaxiMapID)
    if ns.GuideInteger(id) and id > 0 then return id, "GetTaxiMapID" end
    if FlightMapFrame and ns.ReadPublic(FlightMapFrame.IsShown, FlightMapFrame) == true then
        id = ns.ReadPublic(FlightMapFrame.GetMapID, FlightMapFrame)
        if ns.GuideInteger(id) and id > 0 then return id, "FlightMapFrame.GetMapID" end
    end
end

function ns.RefreshTravelDirections(tryFlight)
    -- The city destination can change when a faster flight becomes known.
    -- Refresh it before either the renderer or the flight action reads it.
    if ns.routeSelection and ns.routeSelection.mode == "travel" then ns.UpdateTravelGuide(ns.routeSelection) end
    ns.UpdateNavigation()
    if tryFlight then ns.TrySuggestedFlight() end
    ns.DrawRoute(nil, true)
end

function ns.InitializeTravel()
    ns.db.flights = type(ns.db.flights) == "table" and ns.db.flights or {}
    local state = ns.db.flights[ns.self]
    if type(state) ~= "table" then state = {}; ns.db.flights[ns.self] = state end
    for _, name in ipairs({"nodes", "edges", "timings"}) do
        if type(state[name]) ~= "table" then state[name] = {} end
    end
    for id, node in pairs(state.nodes) do
        if not ns.GuideInteger(id) or type(node) ~= "table" or not ns.SafeTitle(node.name) then
            state.nodes[id] = nil
        else
            node.id, node.known = id, node.known == true
            if not savedPoint(node.point) then node.point = nil end
            local previous = node.point
            node.point = destinationPoint(previous, ns.travelData and ns.travelData.nodes["TAXI_" .. id])
            if previous ~= node.point then node.world = world(node.point) or node.world end
            local w = node.world
            if type(w) ~= "table" or not ns.GuideInteger(w.continent) or not number(w.x) or not number(w.y) then node.world = nil end
        end
    end
    local restored = 0
    for key, edge in pairs(state.edges) do
        if type(edge) ~= "table" or not ns.GuideInteger(edge.source) or not ns.GuideInteger(edge.destination)
            or not state.nodes[edge.source] or not state.nodes[edge.destination] then state.edges[key] = nil end
        if state.edges[key] then
            restored = restored + 1
            for _, id in ipairs({edge.source, edge.destination}) do
                if state.nodes[id].known == true then state.nodes[id].reachabilityConfirmed = true end
            end
        end
    end
    ns.flightCacheRestored, ns.flightCacheConflicts = restored, 0
    for key, timing in pairs(state.timings) do
        if type(timing) ~= "table" or not number(timing.mean) or timing.mean <= 0 or timing.mean >= 7200
            or not ns.GuideInteger(timing.samples, 11) or timing.samples < 1 then state.timings[key] = nil end
    end
    if not savedPoint(state.corpse) then state.corpse = nil end
    local _, build = ns.ReadPublic(GetBuildInfo)
    ns.flightTimingBuild = ns.SafeTitle(build)
    if type(hooksecurefunc) == "function" and type(TakeTaxiNode) == "function" then
        hooksecurefunc("TakeTaxiNode", function(slot) ns.NoteFlightSelection(slot) end)
    end
end

function ns.NoteFlightSelection(slot)
    if not ns.Public(slot) or not ns.GuideInteger(slot) then return end
    local sourceID, visible, now = ns.flightMapSource, ns.visibleFlights, ns.ReadPublic(GetTime)
    local closed = ns.recentFlightMap
    -- Native TakeTaxiNode can close the map before its post-hook runs. This
    -- snapshot is identification only; it is never used to take a flight.
    if not sourceID and closed and number(now) and number(closed.time)
        and now >= closed.time and now - closed.time <= 1 then sourceID, visible = closed.source, closed.visible end
    if not sourceID then return end
    for id, info in pairs(visible or {}) do
        if info.slot == slot and info.reachable then
            local node = flights().nodes[id]
            local source = flights().nodes[sourceID]
            local air, estimate = ns.FlightPointDistance(source, node, nil, sourceID, id)
            local expected, measured, basis = ns.FlightDuration(sourceID, id, air, nil, estimate)
            local previous = ns.pendingFlight
            if ns.flightStarted and previous and (previous.source ~= sourceID or previous.destination ~= id
                or number(now) and number(previous.selectedAt) and now - previous.selectedAt > 30) then
                -- A missed old landing must not time two rides as one.
                ns.flightStarted = nil
            end
            ns.pendingFlight = {source = sourceID, destination = id, name = node.name,
                expected = expected, estimated = not measured, basis = basis}
            ns.PrepareFlightTiming(ns.pendingFlight)
            ns.recentFlightMap = nil
            if C_Timer and type(C_Timer.After) == "function" then
                local selection = ns.pendingFlight
                C_Timer.After(0.1, function()
                    if ns.pendingFlight == selection and not ns.flightStarted then ns.ObserveFlightDeparture() end
                end)
            end
            return
        end
    end
end

function ns.ReadFlightMap(attempt)
    attempt = attempt or 0
    ns.flightMapSource, ns.visibleFlights = nil, nil
    local mapID, source = taxiMapID()
    local states = Enum and Enum.FlightPathState
    local failure
    if not C_TaxiMap or type(C_TaxiMap.GetAllTaxiNodes) ~= "function" then failure = "GetAllTaxiNodes unavailable"
    elseif not states or not number(states.Current) or not number(states.Reachable) then failure = "FlightPathState enums unavailable"
    elseif not mapID then failure = "No public flight map ID; GetTaxiMapID and the visible flight frame could not supply one" end
    local nodes
    if not failure then
        nodes = ns.ReadPublic(C_TaxiMap.GetAllTaxiNodes, mapID)
        if type(nodes) ~= "table" then failure = "GetAllTaxiNodes failed or returned restricted data for map " .. mapID
        elseif not next(nodes) then failure = "Flight map " .. mapID .. " has not returned any nodes yet" end
    end
    if failure then
        ns.flightMapStatus = failure .. "."
        ns.travelStatus = "Flight map read unavailable: " .. failure .. "; choose flights manually."
        if flightMapOpen and attempt < 3 and C_Timer and type(C_Timer.After) == "function" then
            local generation = flightMapGeneration
            C_Timer.After(0.2, function()
                if flightMapOpen and generation == flightMapGeneration then ns.ReadFlightMap(attempt + 1) end
            end)
        end
        return
    end
    local current, visible, slots, accepted, restricted = nil, {}, {}, 0, 0
    local ownMap = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    local state = flights()
    for index, info in ipairs(nodes) do
        if index > 256 then break end
        if ns.Public(info) and type(info) == "table" and ns.GuideInteger(info.nodeID) and number(info.state) then
            local known = (info.state == states.Current or info.state == states.Reachable) and true or nil
            local id = storeNode(info, mapID, ownMap, known, info.state == states.Current, known == true)
            if id then
                accepted = accepted + 1
                if info.state == states.Current then current = id end
                visible[id] = {slot = ns.GuideInteger(info.slotIndex, 1000) and info.slotIndex or nil,
                    reachable = info.state == states.Reachable, unreachable = number(states.Unreachable) and info.state == states.Unreachable}
                if visible[id].slot then slots[visible[id].slot] = id end
            end
        else restricted = restricted + 1 end
    end
    ns.flightMapSource, ns.visibleFlights = current, visible
    ns.checkedFlightNodes = ns.checkedFlightNodes or {}
    if current then ns.checkedFlightNodes[current] = true end
    if current then
        for id, info in pairs(visible) do
            if info.reachable then state.edges[current .. ":" .. id] = {source = current, destination = id,
                route = info.slot and ns.ReadNativeFlightRoute(info.slot, current, id, slots)} end
            if info.unreachable then state.edges[current .. ":" .. id] = nil end
        end
    end
    changed()
    local known = counts()
    ns.flightMapStatus = "Map " .. mapID .. " via " .. source .. "; " .. accepted .. " nodes read; " .. restricted .. " restricted/invalid; source " .. (current and state.nodes[current].name or "not reported") .. "."
    ns.travelStatus = accepted > 0 and ("Flight network observed; " .. known .. " known paths. Travel times are estimates until timed.")
        or "No public flight nodes could be recorded; choose flights manually."
    ns.RefreshTravelDirections(true)
end

function ns.TravelDiagnostics(output)
    local known, located, edges = counts()
    output("Flight paths: " .. known .. " known; " .. located .. " with locations; " .. edges .. " observed connections. Personal to this character.")
    output("Flight unlock scan: " .. ns.flightDiscoveryStatus)
    output("Flight map read: " .. ns.flightMapStatus)
    output("Flight cache: " .. (ns.flightCacheRestored or 0) .. " connections restored at login; "
        .. (ns.flightCacheConflicts or 0) .. " conflicting map discovery flags ignored after confirmed reachability.")
    ns.FlightTimingDiagnostics(output)
    ns.TravelNetworkDiagnostics(output)
end

function ns.FindFlightPlan(stop, safety)
    if not stop or not ns.Option("suggestFlights") then return end
    local state = flights()
    if not state or not next(state.edges) then return end
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    local position = ns.PlayerPoint(mapID)
    local a, b = world(position), world(stop)
    local direct = distance(a, b)
    if not direct or direct < 500 then return end
    local speed, running = ns.ReadPublic(GetUnitSpeed, "player")
    speed = number(running) and running > 0 and running or speed
    speed = number(speed) and speed > 0 and speed or 7
    local best, cost, timingGeometry = nil, nil, {}
    safety = safety or ns.TravelSafetyContext()
    for _, edge in pairs(state.edges) do
        local source, dest = state.nodes[edge.source], state.nodes[edge.destination]
        if source and dest and source.known and dest.known and source.point and dest.point
            and ns.TravelNodeAllowed("TAXI_" .. edge.source, source.point, source, safety)
            and ns.TravelNodeAllowed("TAXI_" .. edge.destination, dest.point, dest, safety)
            and not ns.HostileWalkCrossing(position, source.point, safety, true, false)
            and not ns.HostileWalkCrossing(dest.point, stop, safety, false, true) then
            local start, finish, air = distance(a, source.world), distance(dest.world, b), distance(source.world, dest.world)
            if start and finish and air and air > 0 then
                local duration, measured, basis = ns.FlightDuration(edge.source, edge.destination, air, timingGeometry)
                local value = start / speed + duration + finish / speed + 45
                if value + math.max(30, direct / speed * 0.15) < direct / speed and (not cost or value < cost) then
                    best, cost = {source = source, destination = dest, seconds = value,
                        flightSeconds = duration, measured = measured, timingBasis = basis, walkingSeconds = direct / speed}, value
                end
            end
        end
    end
    return best
end

function ns.TravelDestination(stop)
    if not stop or stop.kind == "notice" or ns.navigationPreview then ns.travelWaypoint = nil; return stop end
    local network = ns.TravelNetworkDestination(stop)
    if network and #ns.FilterGuideStages({network}) > 0 then return network end
    local now = ns.ReadPublic(GetTime)
    now = number(now) and now or nil
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    local signature = table.concat({stop.id, stop.kind, stop.mapID, stop.x, stop.y, mapID or 0,
        ns.travelRevision or 0, ns.profile and ns.SafeTitle(ns.profile.faction) or "Unknown"}, ":")
    local cache = ns.flightPlanCache
    if not cache or cache.signature ~= signature or not now or not cache.time or now - cache.time > 1 then
        -- A terminal Dijkstra walking leg returns no intermediate waypoint.
        -- It still is a decision: do not replace it with a second flight solver.
        cache = {signature = signature, time = now}
        if not ns.HasTravelPathTo(stop) then
            local safety = ns.TravelSafetyContext()
            cache.plan = ns.FindFlightPlan(stop, safety)
            if not cache.plan then cache.hostile = ns.HostileWalkCrossing(ns.PlayerPoint(mapID), stop, safety, true, true) end
        end
        ns.flightPlanCache = cache
    end
    local plan = not ns.HasTravelPathTo(stop) and cache.plan or nil
    if plan then
        local p = plan.source.point
        local flightStop = {id = stop.id, kind = "f", action = "flight", title = stop.title, npcName = plan.source.name,
            targetName = plan.source.name, mapID = p.mapID, x = p.x, y = p.y,
            label = "Fly to " .. plan.destination.name, flightPlan = plan, goal = stop}
        if #ns.FilterGuideStages({flightStop}) > 0 then return flightStop end
    end
    if cache.hostile and not ns.HasTravelPathTo(stop) then
        -- Retain the real quest/marker; do not aim straight through an enemy
        -- town when the graph has no supported bypass. No invented road points.
        local caution = {}; for key, value in pairs(stop) do caution[key] = value end
        caution.kind, caution.unsafeTransit = "travel", cache.hostile
        caution.label = "Route around " .. cache.hostile.name .. " (" .. cache.hostile.faction .. ")."
        return caution
    end
    -- Nearby unlock advice lives in the optional GuideTips strip; it must
    -- not replace the current quest instruction or divert a fixed guide.
    return stop
end

function ns.TrySuggestedFlight()
    if not ns.Option("autoFly") or not ns.Option("suggestFlights") or ns.RouteInCombat()
        or ns.guideScanning or ns.routePlanning or ns.ReadPublic(UnitOnTaxi, "player") == true
        or ns.navigationPreview or ns.routePaused or ns.ReadPublic(UnitIsGhost, "player") == true
        or type(TakeTaxiNode) ~= "function" then return end
    local first = ns.selectedRoute and ns.selectedRoute.stops[1]
    local destination = first and ns.TravelDestination(first)
    local plan = destination and destination.kind == "f" and destination.flightPlan
    local target = plan and ns.visibleFlights and ns.visibleFlights[plan.destination.id]
    if not plan or plan.source.id ~= ns.flightMapSource or not target or not target.reachable or not target.slot
        or ns.flightAttempt == plan.destination.id then return end
    ns.flightAttempt = plan.destination.id
    ns.pendingFlight = {source = plan.source.id, destination = plan.destination.id,
        name = plan.destination.name, expected = plan.flightSeconds, estimated = not plan.measured, basis = plan.timingBasis}
    ns.PrepareFlightTiming(ns.pendingFlight)
    ns.travelStatus = "Requested flight to " .. plan.destination.name .. "; waiting for actual flight state."
    TakeTaxiNode(target.slot)
end

function ns.FlightState()
    local flying = ns.ReadPublic(UnitOnTaxi, "player")
    if flying ~= true then
        if flying == false and ns.flightStarted then ns.FinishFlight() end
        return
    end
    local now = ns.ReadPublic(GetTime)
    if not ns.flightStarted and number(now) then
        local selected = ns.pendingFlight and ns.pendingFlight.selectedAt
        if number(selected) and (now < selected or now - selected > 30) then ns.pendingFlight = nil end
        ns.flightStarted = now
        ns.flightTimingStatus = ns.pendingFlight and ("Timing flight to " .. ns.pendingFlight.name .. ".")
            or "No selected flight was captured; showing elapsed flight time."
    end
    local elapsed = number(now) and number(ns.flightStarted) and math.max(0, now - ns.flightStarted) or nil
    local selection = ns.pendingFlight
    ns.travelNetworkStatus = "Flying to " .. (selection and selection.name or "destination") .. "; ground directions resume after landing."
    local remaining = selection and selection.expected and elapsed and math.max(0, selection.expected - elapsed)
    return {elapsed = elapsed, remaining = remaining, estimated = selection and selection.estimated,
        name = selection and selection.name or "destination"}
end

function ns.FinishFlight()
    if ns.ReadPublic(UnitOnTaxi, "player") ~= false then return end
    if not ns.flightStarted and not ns.pendingFlight then return end
    local now, start, selection = ns.ReadPublic(GetTime), ns.flightStarted, ns.pendingFlight
    ns.FinishFlightTiming(selection, start, now)
    ns.flightStarted, ns.pendingFlight, ns.flightPlanCache = nil, nil, nil
    ns.travelRevision = (ns.travelRevision or 0) + 1
    ns.ResetTravelPath()
    ns.RefreshTravelDirections()
end

local function observeControl(starting)
    if not ns.db then return end
    local selection, began = ns.pendingFlight, ns.flightStarted
    local function check(attempt)
        -- Cancel callbacks when a different ride was selected/finished.
        if selection ~= ns.pendingFlight or not starting and began ~= ns.flightStarted then return end
        local flying = ns.ReadPublic(UnitOnTaxi, "player")
        if starting and flying == true then ns.FlightState(); ns.RefreshTravelDirections(); return end
        if not starting and flying == false then ns.FinishFlight(); return end
        if attempt < 20 and (selection or began) and C_Timer and type(C_Timer.After) == "function" then
            C_Timer.After(0.1, function() check(attempt + 1) end)
        end
    end
    check(0)
    ns.RefreshTravelDirections()
end
function ns.ObserveFlightDeparture() observeControl(true) end

function ns.CorpseDestination()
    if not ns.Option("corpseArrow") or ns.ReadPublic(UnitIsGhost, "player") ~= true then return end
    local recorded = flights() and flights().corpse
    local mapID = recorded and recorded.mapID or C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    local p = C_DeathInfo and point(mapID, ns.ReadPublic(C_DeathInfo.GetCorpseMapPosition, mapID))
    if not p and recorded then p = {mapID = recorded.mapID, x = recorded.x, y = recorded.y, approximate = true} end
    if not p then p = {mapID = mapID or 0, positionUnavailable = true} end
    if p then
        p.id, p.kind, p.title, p.label, p.action = 0, "corpse", "Return to your corpse", "Return to your corpse", "corpse"
        return p
    end
end

function ns.RouteForDisplay()
    local route = ns.selectedRoute
    if not route then return end
    if ns.ReadPublic(UnitOnTaxi, "player") == true then
        ns.travelWaypoint = nil
        -- Keep the same quest steps/full-preview scope during a ride. The map
        -- renderer suppresses ground lines from the moving flight, not pins.
        local display = {}; for key, value in pairs(route) do display[key] = value end
        display.flying = true
        return display
    end
    local confirmation = ns.CurrentQuestConfirmation()
    local training = not confirmation and ns.ClassTrainingDestination(route.stops[1])
    training = training and training.kind == "trainer" and training or nil
    local display = route
    if training then
        display = {}; for key, value in pairs(route) do display[key] = value end
        display.mapID, display.stops = training.mapID, {training}
        for _, value in ipairs(route.stops) do display.stops[#display.stops + 1] = value end
        if route.previewStops then
            display.previewStops = {training}
            for _, value in ipairs(route.previewStops) do display.previewStops[#display.previewStops + 1] = value end
        end
    end
    local stop = ns.CorpseDestination() or ns.TravelDestination(confirmation and not confirmation.unknownLocation and confirmation or training or route.stops[1])
    if stop and stop.travelLeg and stop.kind ~= "f" and not confirmation then return display end
    if stop and (stop.kind == "corpse" or stop.kind == "f") then
        return {mapID = stop.mapID, stops = {stop}, title = stop.title,
            origin = ns.PlayerPoint(stop.mapID), key = route.key, partial = false}
    end
    if confirmation and not confirmation.unknownLocation then
        return {mapID = confirmation.mapID, stops = {confirmation}, title = confirmation.title,
            origin = ns.PlayerPoint(confirmation.mapID), key = route.key, confirmation = true}
    end
    return display
end

ns.On("TAXIMAP_OPENED", function()
    flightMapGeneration, flightMapOpen = flightMapGeneration + 1, true
    ns.recentFlightMap = nil
    if ns.db then ns.ReadKnownFlightPaths(); ns.ReadFlightMap() end
end)
ns.On("TAXIMAP_CLOSED", function()
    flightMapGeneration, flightMapOpen = flightMapGeneration + 1, false
    ns.recentFlightMap = {source = ns.flightMapSource, visible = ns.visibleFlights, time = ns.ReadPublic(GetTime)}
    ns.visibleFlights, ns.flightMapSource, ns.flightAttempt = nil, nil, nil
end)
ns.On("TAXI_NODE_STATUS_CHANGED", function()
    ns.ScheduleFlightDiscovery()
    if flightMapOpen and ns.db then ns.ReadFlightMap() end
end)
ns.On("PLAYER_CONTROL_LOST", function() observeControl(true) end)
ns.On("PLAYER_CONTROL_GAINED", function() observeControl(false) end)
ns.On("PLAYER_DEAD", function()
    if ns.db then
        local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
        flights().corpse = ns.PlayerPoint(mapID)
        ns.UpdateNavigation()
    end
end)
ns.On("PLAYER_ALIVE", function() if ns.db then ns.UpdateNavigation() end end)
ns.On("PLAYER_UNGHOST", function() if ns.db then flights().corpse = nil; ns.UpdateNavigation() end end)
