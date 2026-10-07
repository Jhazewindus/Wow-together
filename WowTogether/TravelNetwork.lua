local addonName, ns = ...

-- Our own Dijkstra search. The attributed snapshot supplies geography only;
-- player progress, guide order and transport actions are outside this module.
local function finite(value)
    return ns.Public(value) and type(value) == "number" and value == value
        and value > -math.huge and value < math.huge
end

function ns.ValidTravelPoint(point)
    return ns.Public(point) and type(point) == "table" and ns.GuideInteger(point.mapID) and point.mapID > 0
        and finite(point.x) and finite(point.y) and point.x >= 0 and point.x <= 1 and point.y >= 0 and point.y <= 1
end

local function world(point, cache)
    if cache and cache[point] ~= nil then return cache[point] or nil end
    local result
    if C_Map and type(CreateVector2D) == "function" then
        local continent, vector = ns.ReadPublic(C_Map.GetWorldPosFromMapPos, point.mapID, CreateVector2D(point.x, point.y))
        if ns.GuideInteger(continent) and vector and (type(vector) == "table" or type(vector) == "userdata") then
            local x, y = ns.ReadPublic(vector.GetXY, vector)
            if finite(x) and finite(y) then result = {continent = continent, x = x, y = y} end
        end
    end
    if cache then cache[point] = result or false end
    return result
end

function ns.TravelPointDistance(a, b, cache)
    if not ns.ValidTravelPoint(a) or not ns.ValidTravelPoint(b) then return end
    if a.mapID == b.mapID then
        local width, height
        local scales = cache and cache.scales
        if scales and scales[a.mapID] then width, height = scales[a.mapID][1], scales[a.mapID][2]
        else
            if C_Map then width, height = ns.ReadPublic(C_Map.GetMapWorldSize, a.mapID) end
            if cache then cache.scales = scales or {}; cache.scales[a.mapID] = {width, height} end
        end
        if finite(width) and finite(height) and width > 0 and height > 0 and width < 1000000 and height < 1000000 then
            return math.sqrt(((a.x - b.x) * width)^2 + ((a.y - b.y) * height)^2)
        end
    end
    local x, y = world(a, cache), world(b, cache)
    if x and y and x.continent == y.continent then return math.sqrt((x.x - y.x)^2 + (x.y - y.y)^2) end
end

local function less(a, b) return a.cost < b.cost or a.cost == b.cost and a.id < b.id end
local function push(heap, item)
    local index = #heap + 1
    while index > 1 do
        local parent = math.floor(index / 2)
        if not less(item, heap[parent]) then break end
        heap[index], index = heap[parent], parent
    end
    heap[index] = item
end
local function pop(heap)
    local first, last = heap[1], table.remove(heap)
    if #heap == 0 then return first end
    local index = 1
    while index * 2 <= #heap do
        local child = index * 2
        if child + 1 <= #heap and less(heap[child + 1], heap[child]) then child = child + 1 end
        if not less(heap[child], last) then break end
        heap[index], index = heap[child], child
    end
    heap[index] = last
    return first
end

local referenceCache = {}
function ns.PublishedTravelDistance(from, to, policy)
    local data = ns.travelData
    if not data or not data.nodes[from] or not data.nodes[to] then return end
    local cache = referenceCache
    if policy then
        if not policy.lookup then policy.lookup = {} end
        cache = policy.lookup
    end
    if data ~= cache.data then
        cache.data, cache.graph, cache.rows, cache.count = data, {}, {}, 0
        for _, edge in ipairs(data.edges) do
            if policy and policy.tick then policy.tick() end
            -- Default lookup remains walk-only geometry for flight estimates.
            -- Fixed-guide policies may price published ordinary transports;
            -- neither lookup makes a personal flight/hearth usable.
            local distance = finite(edge.distance) and edge.distance
                or finite(edge.seconds) and edge.seconds == 0 and 0 or nil
            local a, b = data.nodes[edge.from], data.nodes[edge.to]
            local okay = a and b
            if policy and okay then
                okay = (not edge.faction or edge.faction == "Both" or edge.faction == policy.faction)
                    and ns.TravelNodeAllowed(edge.from, a, nil, policy.safety)
                    and ns.TravelNodeAllowed(edge.to, b, nil, policy.safety)
                if edge.method == "walk" then
                    okay = okay and not ns.HostileWalkCrossing(a, b, policy.safety)
                    if not distance then
                        local length = ns.TravelPointDistance(a, b, policy.metrics)
                        distance = length and length * 1.25
                    end
                elseif edge.method == "ship" or edge.method == "zeppelin" or edge.method == "tram" or edge.method == "transition" then
                    distance = finite(edge.seconds) and edge.seconds >= 0 and edge.seconds * 7 or nil
                else okay = false end
            end
            if okay and (policy or edge.method == "walk") and distance and distance >= 0 then
                cache.graph[edge.from] = cache.graph[edge.from] or {}
                cache.graph[edge.from][#cache.graph[edge.from] + 1] = {to = edge.to, distance = distance}
            end
        end
    end
    if not cache.rows[from] then
        if cache.count >= (policy and 32 or 8) then cache.rows, cache.count = {}, 0 end
        local heap, costs, visited = {}, {[from] = 0}, {}
        push(heap, {id = from, cost = 0})
        while #heap > 0 do
            local item = pop(heap)
            if not visited[item.id] and item.cost == costs[item.id] then
                visited[item.id] = true
                for _, edge in ipairs(cache.graph[item.id] or {}) do
                    local value = item.cost + edge.distance
                    if not visited[edge.to] and (not costs[edge.to] or value < costs[edge.to]) then
                        costs[edge.to] = value; push(heap, {id = edge.to, cost = value})
                    end
                    if policy and policy.tick then policy.tick() end
                end
            end
        end
        cache.rows[from], cache.count = costs, cache.count + 1
    end
    return cache.rows[from][to]
end

function ns.TravelWalkSpeed()
    local speed, running = ns.ReadPublic(GetUnitSpeed, "player")
    speed = finite(running) and running > 0 and running or speed
    return finite(speed) and speed > 0 and speed < 100 and speed or 7
end

local function factor(mapID) return ns.travelData and ns.travelData.factors[mapID] or 1.25 end
local function allowed(edge, faction)
    return not edge.faction or edge.faction == "Both" or edge.faction == faction
end
local function titleWords(value)
    return string.gsub(value, "(%a)([%w]*)", function(a, b) return string.upper(a) .. b end)
end
local function pointLocation(point)
    local zone = ns.MapName(point.mapID)
    if zone == "Map " .. point.mapID then
        local container = ns.SafeTitle(point.container)
        local area = container and string.match(container, "([^%.]+)$")
        if area then zone = titleWords(string.gsub(area, "_", " ")) end
    end
    return zone .. string.format(" (%.1f, %.1f)", point.x * 100, point.y * 100)
end
local function nodeName(id, point)
    local name = ns.SafeTitle(point.name)
    if point.terrain then return name or "Valley waypoint", true end
    -- Anonymous graph junctions are waypoints, not named places. Keep their
    -- stable IDs in the graph/diagnostics, without exposing them as directions.
    if string.find(id, "^CONVERGENCE_") and (not name
        or string.match(name, "^Convergence C%d+ %d+ %d+$")) then
        return "waypoint — " .. pointLocation(point), true
    end
    if string.find(id, "^BORDER_") then
        local target = string.match(id, "_TO_(.+)") or id
        target = string.gsub(target, "_%d+$", "")
        target = string.gsub(string.lower(target), "_", " ")
        return titleWords(target) .. " crossing"
    end
    return name or ns.MapName(point.mapID)
end

function ns.FindTravelPath(origin, goal, useFlights, discoverySource)
    if not ns.ValidTravelPoint(origin) or not ns.ValidTravelPoint(goal) then return end
    local data, speed, positions = ns.travelData or {nodes = {}, edges = {}, factors = {}}, ns.TravelWalkSpeed(), {}
    local nodes, adjacency = {START = origin, GOAL = goal}, {}
    local faction = ns.profile and ns.profile.faction
    local safety = ns.TravelSafetyContext()
    local terrain = ns.TravelTerrainContext()
    local function link(from, to, seconds, method, extra, terrainVisible)
        if not nodes[from] or not nodes[to] or not finite(seconds) or seconds < 0 then return end
        if method == "walk" and ns.HostileWalkCrossing(nodes[from], nodes[to], safety, from == "START", to == "GOAL") then return end
        if method == "walk" and not terrainVisible and ns.TerrainWalkCrossing(nodes[from], nodes[to], terrain) then return end
        adjacency[from] = adjacency[from] or {}
        adjacency[from][#adjacency[from] + 1] = {from = from, to = to, seconds = seconds, method = method, flight = extra}
    end
    for id, point in pairs(data.nodes) do
        if ns.ValidTravelPoint(point) and allowed(point, faction) and ns.TravelNodeAllowed(id, point, nil, safety) then nodes[id] = point end
    end
    for _, map in pairs(terrain.maps) do
        for id, point in pairs(map.nodes) do
            if ns.TravelNodeAllowed(id, point, nil, safety) then nodes[id] = point end
        end
    end
    local flights = ns.db and ns.db.flights and ns.db.flights[ns.self]
    for id, node in pairs(flights and flights.nodes or {}) do
        if ns.ValidTravelPoint(node.point) and ns.TravelNodeAllowed("TAXI_" .. id, node.point, node, safety) then
            local key = "TAXI_" .. id
            local published = nodes[key]
            local source = published and published.mapID ~= node.point.mapID and published or node.point
            local point = {}; for name, value in pairs(source) do point[name] = value end
            point.name, point.taxiID = node.name, id
            nodes[key] = point
        end
    end
    if origin.mapID ~= goal.mapID then
        local start, finish
        for id, p in pairs(nodes) do
            if id ~= "START" and id ~= "GOAL" then
                if p.mapID == origin.mapID then start = true end
                if p.mapID == goal.mapID then finish = true end
            end
        end
        if not start or not finish then return end
    end
    for _, edge in ipairs(data.edges) do
        if nodes[edge.from] and nodes[edge.to] and allowed(edge, faction) then
            local cost = edge.seconds
            if edge.distance then cost = edge.distance / speed
            elseif cost == nil then
                local length = ns.TravelPointDistance(nodes[edge.from], nodes[edge.to], positions)
                cost = length and length * (factor(nodes[edge.from].mapID) + factor(nodes[edge.to].mapID)) / 2 / speed
            end
            link(edge.from, edge.to, cost, edge.method)
        end
    end
    -- Only visible ground segments can join a mapped barrier's waypoints.
    -- This applies to published nodes and character attachments alike: a
    -- distant border/taxi node must not provide a shortcut through a mesa.
    for mapID, map in pairs(terrain.maps) do
        for _, edge in ipairs(map.edges) do
            local length = ns.TravelPointDistance(nodes[edge.from], nodes[edge.to], positions)
            local seconds = length and length * factor(mapID) / speed
            link(edge.from, edge.to, seconds, "walk", nil, true)
            link(edge.to, edge.from, seconds, "walk", nil, true)
        end
        for id, point in pairs(nodes) do
            if id ~= "START" and id ~= "GOAL" and not point.terrain and point.mapID == mapID then
                local indoor = point.container and (string.find(point.container, "wizards_sanctum", 1, true)
                    or string.find(point.container, "blackrock_mountain", 1, true))
                if not indoor then
                    for terrainID, corner in pairs(map.nodes) do
                        if nodes[terrainID] then
                            local length = ns.TravelPointDistance(point, corner, positions)
                            local seconds = length and length * factor(mapID) / speed
                            link(id, terrainID, seconds, "walk")
                            link(terrainID, id, seconds, "walk")
                        end
                    end
                end
            end
        end
    end
    if useFlights then
        for _, edge in pairs(flights and flights.edges or {}) do
            local source, target = flights.nodes[edge.source], flights.nodes[edge.destination]
            if source and target and source.known == true and target.known == true then
                local air, estimate = ns.FlightPointDistance(source, target, positions, edge.source, edge.destination)
                local duration, measured, basis = ns.FlightDuration(edge.source, edge.destination, air, positions, estimate)
                if duration then link("TAXI_" .. edge.source, "TAXI_" .. edge.destination, duration + 45, "taxi",
                    {source = source, destination = target, flightSeconds = duration, measured = measured, timingBasis = basis}) end
            end
        end
        -- A separate prospective calculation may price published connections.
        -- It never changes character unlocks or the executable graph. Only one
        -- selected unlearned departure may be used; every landing is unlocked.
        if discoverySource then
            local reference = {}
            for _, edge in pairs(flights and flights.edges or {}) do
                local source, target = flights.nodes[edge.source], flights.nodes[edge.destination]
                local from, to = "TAXI_" .. edge.source, "TAXI_" .. edge.destination
                if nodes[from] and nodes[to] and source and target and ns.Public(source.known) and source.known == true
                    and ns.Public(target.known) and target.known == true then
                    local air, estimate = ns.FlightPointDistance(source, target, positions, edge.source, edge.destination)
                    local duration = ns.FlightDuration(edge.source, edge.destination, air, positions, estimate)
                    if finite(duration) and duration > 0 then
                        reference[from] = reference[from] or {}
                        table.insert(reference[from], {id = to, seconds = duration})
                    end
                end
            end
            for _, edge in ipairs(data.flightConnections or {}) do
                local source, target = flights and flights.nodes[edge.source], flights and flights.nodes[edge.destination]
                local from, to = "TAXI_" .. edge.source, "TAXI_" .. edge.destination
                local confirmed = flights and flights.edges[edge.source .. ":" .. edge.destination]
                if nodes[from] and nodes[to] and allowed(edge, faction)
                    and (edge.source == discoverySource or source and ns.Public(source.known) and source.known == true)
                    and target and ns.Public(target.known) and target.known == true
                    and not (flights.unreachable and flights.unreachable[edge.source .. ":" .. edge.destination]) then
                    local duration = edge.seconds
                    if confirmed then
                        local air, estimate = ns.FlightPointDistance(source, target, positions, edge.source, edge.destination)
                        duration = ns.FlightDuration(edge.source, edge.destination, air, positions, estimate) or duration
                    end
                    if finite(duration) and duration > 0 then
                        reference[from] = reference[from] or {}
                        table.insert(reference[from], {id = to, seconds = duration})
                    end
                end
            end
            -- Price a connecting ticket with one boarding allowance, rather
            -- than charging another check-in at every intermediate master.
            local start = "TAXI_" .. discoverySource
            local heap, costs, visited = {}, {[start] = 0}, {}
            push(heap, {id = start, cost = 0})
            while #heap > 0 do
                local item = pop(heap)
                if not visited[item.id] and item.cost == costs[item.id] then
                    visited[item.id] = true
                    for _, edge in ipairs(reference[item.id] or {}) do
                        local value = item.cost + edge.seconds
                        if not visited[edge.id] and (not costs[edge.id] or value < costs[edge.id]) then
                            costs[edge.id] = value; push(heap, {id = edge.id, cost = value})
                        end
                    end
                end
            end
            local departure = flights and flights.nodes[discoverySource]
                or {id = discoverySource, name = nodes[start] and nodes[start].name, point = nodes[start]}
            for id, duration in pairs(costs) do
                local targetID = tonumber(string.match(id, "^TAXI_(%d+)$"))
                local target = flights and flights.nodes[targetID]
                if id ~= start and target and not (flights.unreachable and flights.unreachable[discoverySource .. ":" .. targetID]) then
                    link(start, id, duration + 45, "taxi", {source = departure, destination = target,
                        flightSeconds = duration, measured = false, timingBasis = "Published connection estimate", unconfirmed = true})
                end
            end
        end
    end
    local ids = {}; for id in pairs(nodes) do if id ~= "START" and id ~= "GOAL" then ids[#ids + 1] = id end end; table.sort(ids)
    for _, id in ipairs(ids) do
        local p = nodes[id]
        -- Attach only within the same map. Borders and city gates supply the
        -- crossing; proximity in world space cannot jump walls or continents.
        local indoor = p.container and (string.find(p.container, "wizards_sanctum", 1, true) or string.find(p.container, "blackrock_mountain", 1, true))
        if not indoor and p.mapID == origin.mapID then
            local length = ns.TravelPointDistance(origin, p, positions)
            link("START", id, length and length * factor(p.mapID) / speed, "walk")
        end
        if not indoor and p.mapID == goal.mapID then
            local length = ns.TravelPointDistance(p, goal, positions)
            link(id, "GOAL", length and length * factor(p.mapID) / speed, "walk")
        end
    end
    if origin.mapID == goal.mapID then
        local length = ns.TravelPointDistance(origin, goal, positions)
        link("START", "GOAL", length and length * factor(origin.mapID) / speed, "walk")
    end
    local heap, costs, previous, visited = {}, {START = 0}, {}, {}
    push(heap, {id = "START", cost = 0})
    while #heap > 0 do
        local item = pop(heap)
        if not visited[item.id] and item.cost == costs[item.id] then
            visited[item.id] = true
            if item.id == "GOAL" then break end
            for _, edge in ipairs(adjacency[item.id] or {}) do
                local value = item.cost + edge.seconds
                if not visited[edge.to] and (costs[edge.to] == nil or value < costs[edge.to]) then
                    costs[edge.to], previous[edge.to] = value, edge
                    push(heap, {id = edge.to, cost = value})
                end
            end
        end
    end
    if not visited.GOAL then return end
    local reverse, cursor = {}, "GOAL"
    while previous[cursor] do reverse[#reverse + 1] = previous[cursor]; cursor = previous[cursor].from end
    local legs, hasTerrain = {}, false
    for index = #reverse, 1, -1 do
        local edge = reverse[index]
        local name, waypoint = nodeName(edge.to, nodes[edge.to])
        legs[#legs + 1] = {from = nodes[edge.from], to = nodes[edge.to], method = edge.method,
            fromID = edge.from, toID = edge.to, name = name, waypoint = waypoint,
            seconds = edge.seconds, flight = edge.flight}
        if edge.method == "walk" and (nodes[edge.from].terrain or nodes[edge.to].terrain) then hasTerrain = true end
    end
    return {legs = legs, seconds = costs.GOAL, cursor = 1, origin = origin, goal = goal, hasTerrain = hasTerrain}
end

function ns.ResetTravelPath()
    ns.travelPath, ns.travelPathSignature, ns.travelPathChecked, ns.travelWaypoint = nil, nil, nil, nil
    ns.flightDiscoveryCache, ns.activeFlightCheck = nil, nil
end

function ns.HasTravelPathTo(stop)
    local path = ns.travelPath
    return not ns.navigationPreview and (not ns.routePaused or stop and stop.confirmation)
        and (ns.Option("travelNetwork") or ns.routeSelection and ns.routeSelection.mode == "travel")
        and path and stop and path.goal.mapID == stop.mapID and path.goal.x == stop.x and path.goal.y == stop.y
end

local function nextConnection(path)
    for index = path.cursor, #path.legs do
        if path.legs[index].method ~= "walk" then return path.legs[index] end
    end
end

local function transportAction(method)
    return method == "taxi" and "Fly" or method == "ship" and "Take the ship"
        or method == "zeppelin" and "Take the zeppelin" or method == "tram" and "Take the tram" or "Use the passage"
end

function ns.TravelPathSummary(stop)
    if ns.ReadPublic(UnitOnTaxi, "player") == true then return end
    if stop.flightDiscovery then
        local plan = stop.flightDiscovery
        return "Check flights at " .. plan.source.name .. " towards " .. plan.destination.name .. ".\n"
            .. "Potential saving ~" .. ns.FormatTravelDuration(plan.savedSeconds) .. "; confirm at the flight master."
    end
    if not ns.HasTravelPathTo(stop.goal or stop) then return end
    local path = ns.travelPath
    if stop.travelLeg and stop.travelLeg.method == "walk" and stop.travelLeg.to.terrain then
        return "Go around " .. stop.travelLeg.to.terrain.name .. ".\nContinue towards your guide destination."
    end
    if stop.travelLeg and stop.travelLeg.method ~= "walk" and stop.travelLeg.method ~= "taxi" then
        local leg = stop.travelLeg
        local boarding = nodeName(leg.fromID, leg.from)
        return "Board at " .. boarding .. " — " .. pointLocation(leg.from) .. ".\nWaiting time varies; continue towards " .. ns.MapName(stop.goal.mapID) .. "."
    end
    local connection = nextConnection(path)
    if connection and not connection.flight then
        return "Go to " .. nodeName(connection.fromID, connection.from) .. ".\n"
            .. transportAction(connection.method) .. " to " .. connection.name .. "."
    end
    local flight = connection and connection.flight and connection
    if flight then
        local source, target = flight.flight.source.name, flight.flight.destination.name
        return (stop.kind == "f" and ("Fly to " .. target .. ".") or ("Walk to " .. source .. "; then fly to " .. target .. "."))
            .. "\n" .. (flight.flight.measured and "Timed flight: ~" or "Estimated flight: ")
            .. ns.FormatTravelDuration(flight.flight.flightSeconds) .. "; journey ~" .. ns.FormatTravelDuration(path.seconds) .. "."
    end
    if stop.travelLeg then
        return "Travel towards " .. ns.MapName(stop.goal.mapID) .. ".\n"
            .. (stop.travelLeg.method == "walk" and (stop.travelLeg.waypoint
                and "Follow roads and terrain to this waypoint." or "Follow roads and terrain.")
                or "Board the correct transport; waiting time varies.")
    end
end

function ns.TravelNetworkDestination(stop)
    ns.travelWaypoint = nil
    local travelGuide = ns.routeSelection and ns.routeSelection.mode == "travel"
    if not ns.Option("travelNetwork") and not travelGuide or not ns.ValidTravelPoint(stop) or ns.navigationPreview
        or ns.routePaused and not stop.confirmation or ns.ReadPublic(UnitOnTaxi, "player") == true then return end
    local path = ns.travelPath
    local holding = path and path.transportIndex == path.cursor and path.selectionKey == (ns.routeSelection and ns.routeSelection.key)
        and path.goal.id == stop.id and path.goal.mapID == stop.mapID and path.goal.x == stop.x and path.goal.y == stop.y
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    local position = ns.GuideInteger(mapID) and ns.PlayerPoint(mapID)
    if not ns.ValidTravelPoint(position) and not holding then ns.ResetTravelPath(); return end
    local signature = table.concat({ns.routeSelection and ns.routeSelection.key or "", stop.id or 0, stop.kind or "", stop.mapID,
        stop.x, stop.y, mapID or 0, ns.travelRevision or 0, tostring(ns.Option("suggestFlights")), ns.profile and ns.profile.faction or "Unknown",
        ns.TravelWalkSpeed()}, ":")
    local now = ns.ReadPublic(GetTime)
    local checkMovement = not holding and path and (not finite(now) or not ns.travelPathChecked or now - ns.travelPathChecked >= 2)
    local moved = checkMovement and ns.TravelPointDistance(position, path.origin)
    local detour = moved and moved > 175
    if checkMovement and path.hasTerrain then
        local leg = path.legs[path.cursor]
        local distance = leg and leg.method == "walk" and ns.TravelSegmentDistance(position, leg.from, leg.to)
        -- Following the same segment is progress, not a reason to replace a
        -- corner waypoint. Reattach only after a real departure from it.
        if distance then detour = distance > 100 end
    end
    if checkMovement then ns.travelPathChecked = finite(now) and now or nil end
    if not holding and (ns.travelPathSignature ~= signature or detour
        or not path and (not finite(now) or not ns.travelPathChecked or now - ns.travelPathChecked >= 1)) then
        ns.travelPathSignature = signature
        ns.travelPathChecked = finite(now) and now or nil
        ns.travelPath = ns.FindTravelPath(position, stop, ns.Option("suggestFlights"))
        if ns.travelPath then ns.travelPath.selectionKey = ns.routeSelection and ns.routeSelection.key end
        ns.travelNetworkStatus = ns.travelPath and (ns.travelPath.hasTerrain
            and "Dijkstra directions around mapped terrain; footprints are estimates."
            or "Dijkstra travel directions; walk segments are estimates.") or "No connected travel path; direct quest directions retained."
    end
    path = ns.travelPath
    if not path then
        if ns.TerrainWalkCrossing(position, stop) then
            ns.travelNetworkStatus = "Mapped terrain blocks direct walking; no connected entrance/lift/ramp approach."
        end
        return
    end
    while path.legs[path.cursor] do
        local connection = nextConnection(path)
        ns.travelNetworkStatus = connection and ("Dijkstra next connection: " .. transportAction(connection.method)
            .. " from " .. nodeName(connection.fromID, connection.from) .. " to " .. connection.name .. "; times are estimates.")
            or (path.hasTerrain and "Dijkstra directions around mapped terrain; footprints are estimates."
                or "Dijkstra travel directions; walk segments are estimates.")
        local leg = path.legs[path.cursor]
        local remaining = ns.TravelPointDistance(position, leg.to)
        if leg.toID == "GOAL" then return end
        local arrived = remaining and remaining <= (leg.method == "walk" and 20 or 100)
        local following = path.legs[path.cursor + 1]
        if leg.to.terrain and position and remaining then
            local _, along = ns.TravelSegmentDistance(position, leg.from, leg.to)
            arrived = (arrived or along == 1 and remaining <= 100) and following
                and not ns.TerrainWalkCrossing(position, following.to)
                and not ns.HostileWalkCrossing(position, following.to, nil, true, following.toID == "GOAL")
        end
        if position and position.mapID == leg.to.mapID and arrived then
            path.transportIndex = nil
            path.cursor = path.cursor + 1
        else
            local transport = leg.method ~= "walk"
            local target = transport and leg.from or leg.to
            local instruction = transport and (transportAction(leg.method) .. " to " .. leg.name)
                or following and following.flight and ("Walk to " .. following.flight.source.name .. " (flight master)")
                or (leg.waypoint and "Go to " or "Head to ") .. leg.name
            local result = {id = stop.id, kind = "travel", title = stop.title, mapID = target.mapID, x = target.x, y = target.y,
                action = "travel", label = instruction, travelLeg = leg, goal = stop, guideStep = stop.guideStep}
            if leg.method == "ship" or leg.method == "zeppelin" or leg.method == "tram" then
                local boardingDistance = ns.TravelPointDistance(position, leg.from)
                if boardingDistance and boardingDistance <= 40 then path.transportIndex = path.cursor end
                result.transportWaiting = path.transportIndex == path.cursor
            end
            if leg.flight then
                result.kind, result.action, result.flightPlan = "f", "flight", {}
                for key, value in pairs(leg.flight) do result.flightPlan[key] = value end
                result.flightPlan.seconds = path.seconds
                local direct = ns.TravelPointDistance(position, stop)
                result.flightPlan.walkingSeconds = direct and direct / ns.TravelWalkSpeed()
            end
            ns.travelWaypoint = result
            return result
        end
    end
end

function ns.TravelNetworkDiagnostics(output)
    local terrain = ns.TravelTerrainContext()
    local maps, areas = 0, 0
    for _, map in pairs(terrain.maps) do maps, areas = maps + 1, areas + #map.areas end
    output("Mapped terrain: " .. areas .. " approximate barrier footprints in " .. maps
        .. " zone(s). Waypoints route around known outlines; no collision/elevation mesh.")
    output("Settlement travel checks: " .. #(ns.travelData and ns.travelData.settlements or {})
        .. " published footprints; estimated 100-yard margin. Hostile ground crossings are excluded; roads/guards remain unverified.")
    if ns.routeStats and (ns.routeStats.hostileLines or 0) > 0 then
        output("Hostile ground preview lines hidden: " .. ns.routeStats.hostileLines .. ". Quest markers retained.")
    end
    if ns.routeStats and (ns.routeStats.terrainLines or 0) > 0 then
        output("Unrouted ground preview lines hidden across mapped terrain: " .. ns.routeStats.terrainLines .. ". Quest markers retained.")
    end
    local stop = ns.travelWaypoint
    local leg = stop and stop.travelLeg
    if not leg or not ns.ValidTravelPoint(stop) then return end
    output("Travel leg: " .. leg.fromID .. " -> " .. leg.toID .. " (" .. leg.method .. "); target " .. pointLocation(stop) .. ".")
    if ns.ValidTravelPoint(stop.goal) then
        output("Travel goal: " .. (ns.SafeTitle(stop.goal.title) or "Guide destination")
            .. " (" .. (stop.goal.id or 0) .. "); " .. pointLocation(stop.goal) .. ".")
    end
end

function ns.TravelLinePoints(origin, goal)
    local check = ns.activeFlightCheck
    if check and check.goal.mapID == goal.mapID and check.goal.x == goal.x and check.goal.y == goal.y then
        -- Only draw the visit. Reference air links are not confirmed flights.
        return {origin, check, false}
    end
    local path = (ns.Option("travelNetwork") or ns.routeSelection and ns.routeSelection.mode == "travel") and ns.travelPath
    if not path or path.goal.mapID ~= goal.mapID or path.goal.x ~= goal.x or path.goal.y ~= goal.y then return end
    local points = path.transportIndex == path.cursor and {false} or {origin}
    for index = path.cursor, #path.legs do
        local leg = path.legs[index]
        if leg.method ~= "walk" then points[#points + 1] = leg.from; points[#points + 1] = false end
        points[#points + 1] = leg.to
    end
    return points
end
