local addonName, ns = ...

ns.travelStatus = "Open a flight master's map to learn this character's flight network."

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

function ns.ReadFlightMap()
    ns.flightMapSource, ns.visibleFlights = nil, nil
    local mapID = C_TaxiMap and ns.ReadPublic(C_TaxiMap.GetTaxiMapID)
    local nodes = C_TaxiMap and ns.ReadPublic(C_TaxiMap.GetAllTaxiNodes, mapID)
    local states = Enum and Enum.FlightPathState
    if type(nodes) ~= "table" or not states or not ns.Public(states.Current) or not ns.Public(states.Reachable) then
        ns.travelStatus = "Flight map APIs or state enums unavailable; choose flights manually."; return
    end
    local current, visible = nil, {}
    local ownMap = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    local state = flights()
    for index, info in ipairs(nodes) do
        if index > 256 then break end
        if ns.Public(info) and type(info) == "table" and ns.Public(info.nodeID) and ns.GuideInteger(info.nodeID)
            and ns.Public(info.state) and ns.Public(info.slotIndex) then
            local id, name = info.nodeID, ns.SafeTitle(info.name)
            if id > 0 and name then
                local published = ns.travelData and ns.travelData.nodes["TAXI_" .. id]
                local p = point(mapID, ns.Public(info.position) and info.position)
                if not p and published then p = {mapID = published.mapID, x = published.x, y = published.y} end
                if info.state == states.Current then current = id; p = ns.PlayerPoint(ownMap) or p end
                if p then p = localPoint(ownMap, p) end
                local old = state.nodes[id] or {}
                local known = info.state == states.Current or info.state == states.Reachable or old.known == true
                state.nodes[id] = {id = id, name = name, point = p or old.point,
                    world = p and world(p) or old.world, known = known}
                visible[id] = {slot = ns.GuideInteger(info.slotIndex, 1000) and info.slotIndex or nil,
                    reachable = info.state == states.Reachable}
            end
        end
    end
    ns.flightMapSource, ns.visibleFlights = current, visible
    ns.checkedFlightNodes = ns.checkedFlightNodes or {}
    if current then ns.checkedFlightNodes[current] = true end
    if current then
        for id, info in pairs(visible) do
            if info.reachable then state.edges[current .. ":" .. id] = {source = current, destination = id} end
        end
    end
    ns.travelRevision, ns.flightPlanCache = (ns.travelRevision or 0) + 1, nil
    ns.travelStatus = "Flight network observed. Travel times are estimated until this character has timed that flight."
    ns.UpdateNavigation()
    ns.TrySuggestedFlight()
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
        cache = {signature = signature, time = now, plan = ns.FindFlightPlan(stop)}
        ns.flightPlanCache = cache
    end
    local plan = cache.plan
    if plan then
        local p = plan.source.point
        local flightStop = {id = stop.id, kind = "f", action = "flight", title = stop.title, npcName = plan.source.name,
            targetName = plan.source.name, mapID = p.mapID, x = p.x, y = p.y,
            label = "Fly to " .. plan.destination.name, flightPlan = plan, goal = stop}
        if #ns.FilterGuideStages({flightStop}) > 0 then return flightStop end
    end
    if ns.Option("nearbyFlights") then
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
    ns.UpdateNavigation()
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
    if ns.ReadPublic(UnitOnTaxi, "player") == true then return route end
    local stop = ns.CorpseDestination() or ns.TravelDestination(route.stops[1])
    if stop and stop.travelLeg and stop.kind ~= "f" then return route end
    if stop and (stop.kind == "corpse" or stop.kind == "f") then
        return {mapID = stop.mapID, stops = {stop}, title = stop.title,
            origin = ns.PlayerPoint(stop.mapID), key = route.key, partial = false}
    end
    return route
end

ns.On("TAXIMAP_OPENED", function() if ns.db then ns.ReadFlightMap() end end)
ns.On("TAXIMAP_CLOSED", function() ns.visibleFlights, ns.flightMapSource, ns.flightAttempt = nil, nil, nil end)
ns.On("PLAYER_CONTROL_LOST", function() if ns.db then ns.FlightState(); ns.UpdateNavigation() end end)
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
