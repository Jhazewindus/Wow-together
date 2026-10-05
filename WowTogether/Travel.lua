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
    ns.ResetTravelPath()
end

local function storeNode(info, mapID, ownMap, known, current)
    if not ns.Public(info) or type(info) ~= "table" or not ns.GuideInteger(info.nodeID) or info.nodeID <= 0 then return end
    local id, state = info.nodeID, flights()
    local old = state.nodes[id] or {}
    local published = ns.travelData and ns.travelData.nodes["TAXI_" .. id]
    local name = ns.SafeTitle(info.name) or old.name or published and ns.SafeTitle(published.name)
    if not name then return end
    local p = point(mapID, ns.Public(info.position) and info.position)
    if not p and published then p = {mapID = published.mapID, x = published.x, y = published.y} end
    if current then p = ns.PlayerPoint(ownMap) or p end
    if p then p = localPoint(ownMap, p) end
    if known == nil then known = old.known == true end
    state.nodes[id] = {id = id, name = name, point = p or old.point,
        world = p and world(p) or old.world, known = known}
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
            local w = node.world
            if type(w) ~= "table" or not ns.GuideInteger(w.continent) or not number(w.x) or not number(w.y) then node.world = nil end
        end
    end
    for key, edge in pairs(state.edges) do
        if type(edge) ~= "table" or not ns.GuideInteger(edge.source) or not ns.GuideInteger(edge.destination)
            or not state.nodes[edge.source] or not state.nodes[edge.destination] then state.edges[key] = nil end
    end
    for key, timing in pairs(state.timings) do
        if type(timing) ~= "table" or not number(timing.mean) or timing.mean <= 0 or timing.mean >= 7200
            or not ns.GuideInteger(timing.samples, 11) or timing.samples < 1 then state.timings[key] = nil end
    end
    if not savedPoint(state.corpse) then state.corpse = nil end
    if type(hooksecurefunc) == "function" and type(TakeTaxiNode) == "function" then
        hooksecurefunc("TakeTaxiNode", function(slot) ns.NoteFlightSelection(slot) end)
    end
end

function ns.NoteFlightSelection(slot)
    if not ns.Public(slot) or not ns.GuideInteger(slot) or not ns.flightMapSource then return end
    for id, info in pairs(ns.visibleFlights or {}) do
        if info.slot == slot and info.reachable then
            local node = flights().nodes[id]
            local timing = flights().timings[ns.flightMapSource .. ":" .. id]
            ns.pendingFlight = {source = ns.flightMapSource, destination = id, name = node.name,
                expected = timing and timing.mean}
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
    local current, visible, accepted, restricted = nil, {}, 0, 0
    local ownMap = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    local state = flights()
    for index, info in ipairs(nodes) do
        if index > 256 then break end
        if ns.Public(info) and type(info) == "table" and ns.GuideInteger(info.nodeID) and number(info.state) then
            local known = (info.state == states.Current or info.state == states.Reachable) and true or nil
            local id = storeNode(info, mapID, ownMap, known, info.state == states.Current)
            if id then
                accepted = accepted + 1
                if info.state == states.Current then current = id end
                visible[id] = {slot = ns.GuideInteger(info.slotIndex, 1000) and info.slotIndex or nil,
                    reachable = info.state == states.Reachable, unreachable = number(states.Unreachable) and info.state == states.Unreachable}
            end
        else restricted = restricted + 1 end
    end
    ns.flightMapSource, ns.visibleFlights = current, visible
    ns.checkedFlightNodes = ns.checkedFlightNodes or {}
    if current then ns.checkedFlightNodes[current] = true end
    if current then
        for id, info in pairs(visible) do
            if info.reachable then state.edges[current .. ":" .. id] = {source = current, destination = id} end
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
end

function ns.FindFlightPlan(stop)
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
    local best, cost
    for _, edge in pairs(state.edges) do
        local source, dest = state.nodes[edge.source], state.nodes[edge.destination]
        if source and dest and source.known and dest.known and source.point and dest.point then
            local start, finish, air = distance(a, source.world), distance(dest.world, b), distance(source.world, dest.world)
            if start and finish and air then
                local timing = state.timings[edge.source .. ":" .. edge.destination]
                local duration = timing and timing.mean or air / 32 * 1.35
                local value = start / speed + duration + finish / speed + 45
                if value + math.max(30, direct / speed * 0.15) < direct / speed and (not cost or value < cost) then
                    best, cost = {source = source, destination = dest, seconds = value,
                        flightSeconds = duration, measured = timing ~= nil, walkingSeconds = direct / speed}, value
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
    local signature = table.concat({stop.id, stop.kind, stop.mapID, stop.x, stop.y, mapID or 0, ns.travelRevision or 0}, ":")
    local cache = ns.flightPlanCache
    if not cache or cache.signature ~= signature or not now or not cache.time or now - cache.time > 1 then
        -- A terminal Dijkstra walking leg returns no intermediate waypoint.
        -- It still is a decision: do not replace it with a second flight solver.
        cache = {signature = signature, time = now,
            plan = not ns.HasTravelPathTo(stop) and ns.FindFlightPlan(stop) or nil}
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
    if ns.Option("nearbyFlights") and not (ns.routeSelection and ns.routeSelection.mode == "travel") then
        local state = flights()
        local position = ns.PlayerPoint(mapID)
        for _, node in pairs(state and state.nodes or {}) do
            local p = node.point
            if not node.known and p and p.mapID == mapID and ns.NormalizedDistance(position, p) <= 0.012
                and not (ns.checkedFlightNodes and ns.checkedFlightNodes[node.id]) then
                local flightStop = {id = stop.id, kind = "f", action = "flight-check", title = "Check flight path: " .. node.name,
                    npcName = node.name, mapID = p.mapID, x = p.x, y = p.y, label = "Check flight path",
                    flightNodeID = node.id, goal = stop}
                if #ns.FilterGuideStages({flightStop}) > 0 then return flightStop end
            end
        end
    end
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
        name = plan.destination.name, expected = plan.measured and plan.flightSeconds or nil}
    ns.travelStatus = "Requested flight to " .. plan.destination.name .. "; waiting for actual flight state."
    TakeTaxiNode(target.slot)
end

function ns.FlightState()
    local flying = ns.ReadPublic(UnitOnTaxi, "player")
    if flying ~= true then return end
    local now = ns.ReadPublic(GetTime)
    if not ns.flightStarted and number(now) then ns.flightStarted = now end
    local elapsed = number(now) and number(ns.flightStarted) and math.max(0, now - ns.flightStarted) or nil
    local selection = ns.pendingFlight
    ns.travelNetworkStatus = "Flying to " .. (selection and selection.name or "destination") .. "; ground directions resume after landing."
    local remaining = selection and selection.expected and elapsed and math.max(0, selection.expected - elapsed)
    return {elapsed = elapsed, remaining = remaining, name = selection and selection.name or "destination"}
end

function ns.FinishFlight()
    if ns.ReadPublic(UnitOnTaxi, "player") ~= false then return end
    local now, start, selection = ns.ReadPublic(GetTime), ns.flightStarted, ns.pendingFlight
    if selection and number(now) and number(start) and now - start > 1 and now - start < 7200 then
        local key = selection.source .. ":" .. selection.destination
        local timings = flights().timings
        local old = timings[key]
        local samples = math.min(10, old and old.samples or 0)
        timings[key] = {mean = ((old and old.mean or 0) * samples + now - start) / (samples + 1), samples = samples + 1}
    end
    ns.flightStarted, ns.pendingFlight, ns.flightPlanCache = nil, nil, nil
    ns.travelRevision = (ns.travelRevision or 0) + 1
    ns.ResetTravelPath()
    ns.RefreshTravelDirections()
end

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
        local selection = ns.pendingFlight
        local node = selection and flights() and flights().nodes[selection.destination]
        local p = node and node.point
        local stop = p and {id = 0, kind = "f", action = "flight", mapID = p.mapID, x = p.x, y = p.y,
            title = "Flying to " .. node.name, label = "Flying to " .. node.name}
        return {key = route.key, title = route.title, mapID = p and p.mapID or route.mapID,
            flying = true, stops = stop and {stop} or {}}
    end
    local stop = ns.CorpseDestination() or ns.TravelDestination(route.stops[1])
    if stop and stop.travelLeg and stop.kind ~= "f" then return route end
    if stop and (stop.kind == "corpse" or stop.kind == "f") then
        return {mapID = stop.mapID, stops = {stop}, title = stop.title,
            origin = ns.PlayerPoint(stop.mapID), key = route.key, partial = false}
    end
    return route
end

ns.On("TAXIMAP_OPENED", function()
    flightMapGeneration, flightMapOpen = flightMapGeneration + 1, true
    if ns.db then ns.ReadKnownFlightPaths(); ns.ReadFlightMap() end
end)
ns.On("TAXIMAP_CLOSED", function()
    flightMapGeneration, flightMapOpen = flightMapGeneration + 1, false
    ns.visibleFlights, ns.flightMapSource, ns.flightAttempt = nil, nil, nil
end)
ns.On("TAXI_NODE_STATUS_CHANGED", function()
    ns.ScheduleFlightDiscovery()
    if flightMapOpen and ns.db then ns.ReadFlightMap() end
end)
ns.On("PLAYER_CONTROL_LOST", function() if ns.db then ns.FlightState(); ns.RefreshTravelDirections() end end)
ns.On("PLAYER_CONTROL_GAINED", function() if ns.db then ns.FinishFlight() end end)
ns.On("PLAYER_DEAD", function()
    if ns.db then
        local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
        flights().corpse = ns.PlayerPoint(mapID)
        ns.UpdateNavigation()
    end
end)
ns.On("PLAYER_ALIVE", function() if ns.db then ns.UpdateNavigation() end end)
ns.On("PLAYER_UNGHOST", function() if ns.db then flights().corpse = nil; ns.UpdateNavigation() end end)
