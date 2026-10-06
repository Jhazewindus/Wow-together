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

local referenceData, referenceGraph, referenceRows, referenceCount
function ns.PublishedTravelDistance(from, to)
    local data = ns.travelData
    if not data or not data.nodes[from] or not data.nodes[to] then return end
    if data ~= referenceData then
        referenceData, referenceGraph, referenceRows, referenceCount = data, {}, {}, 0
        for _, edge in ipairs(data.edges) do
            -- Geometry estimates only: never add a flight, ship, teleport or
            -- a usable ground route from this distance lookup.
            local distance = finite(edge.distance) and edge.distance
                or finite(edge.seconds) and edge.seconds == 0 and 0 or nil
            if edge.method == "walk" and distance and distance >= 0 and data.nodes[edge.from] and data.nodes[edge.to] then
                referenceGraph[edge.from] = referenceGraph[edge.from] or {}
                referenceGraph[edge.from][#referenceGraph[edge.from] + 1] = {to = edge.to, distance = distance}
            end
        end
    end
    if not referenceRows[from] then
        if referenceCount >= 8 then referenceRows, referenceCount = {}, 0 end
        local heap, costs, visited = {}, {[from] = 0}, {}
        push(heap, {id = from, cost = 0})
        while #heap > 0 do
            local item = pop(heap)
            if not visited[item.id] and item.cost == costs[item.id] then
                visited[item.id] = true
                for _, edge in ipairs(referenceGraph[item.id] or {}) do
                    local value = item.cost + edge.distance
                    if not visited[edge.to] and (not costs[edge.to] or value < costs[edge.to]) then
                        costs[edge.to] = value; push(heap, {id = edge.to, cost = value})
                    end
                end
            end
        end
        referenceRows[from], referenceCount = costs, referenceCount + 1
    end
    return referenceRows[from][to]
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

function ns.FindTravelPath(origin, goal, useFlights)
    if not ns.ValidTravelPoint(origin) or not ns.ValidTravelPoint(goal) then return end
    local data, speed, positions = ns.travelData or {nodes = {}, edges = {}, factors = {}}, ns.TravelWalkSpeed(), {}
    local nodes, adjacency = {START = origin, GOAL = goal}, {}
    local faction = ns.profile and ns.profile.faction
    local safety = ns.TravelSafetyContext()
    local function link(from, to, seconds, method, extra)
        if not nodes[from] or not nodes[to] or not finite(seconds) or seconds < 0 then return end
        if method == "walk" and ns.HostileWalkCrossing(nodes[from], nodes[to], safety, from == "START", to == "GOAL") then return end
        adjacency[from] = adjacency[from] or {}
        adjacency[from][#adjacency[from] + 1] = {from = from, to = to, seconds = seconds, method = method, flight = extra}
    end
    for id, point in pairs(data.nodes) do
        if ns.ValidTravelPoint(point) and allowed(point, faction) and ns.TravelNodeAllowed(id, point, nil, safety) then nodes[id] = point end
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
    local legs = {}
    for index = #reverse, 1, -1 do
        local edge = reverse[index]
        local name, waypoint = nodeName(edge.to, nodes[edge.to])
        legs[#legs + 1] = {from = nodes[edge.from], to = nodes[edge.to], method = edge.method,
            fromID = edge.from, toID = edge.to, name = name, waypoint = waypoint,
            seconds = edge.seconds, flight = edge.flight}
    end
    return {legs = legs, seconds = costs.GOAL, cursor = 1, origin = origin, goal = goal}
end

function ns.ResetTravelPath() ns.travelPath, ns.travelPathSignature, ns.travelPathChecked, ns.travelWaypoint = nil, nil, nil, nil end

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
    if not ns.HasTravelPathTo(stop.goal or stop) then return end
    local path = ns.travelPath
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
    local moved = not holding and path and (not finite(now) or not ns.travelPathChecked or now - ns.travelPathChecked >= 2)
        and ns.TravelPointDistance(position, path.origin)
    if not holding and (ns.travelPathSignature ~= signature or moved and moved > 175
        or not path and (not finite(now) or not ns.travelPathChecked or now - ns.travelPathChecked >= 1)) then
        ns.travelPathSignature = signature
        ns.travelPathChecked = finite(now) and now or nil
        ns.travelPath = ns.FindTravelPath(position, stop, ns.Option("suggestFlights"))
        if ns.travelPath then ns.travelPath.selectionKey = ns.routeSelection and ns.routeSelection.key end
        ns.travelNetworkStatus = ns.travelPath and "Dijkstra travel directions; walk segments are estimates." or "No connected travel path; direct quest directions retained."
    end
    path = ns.travelPath
    if not path then return end
    while path.legs[path.cursor] do
        local connection = nextConnection(path)
        ns.travelNetworkStatus = connection and ("Dijkstra next connection: " .. transportAction(connection.method)
            .. " from " .. nodeName(connection.fromID, connection.from) .. " to " .. connection.name .. "; times are estimates.")
            or "Dijkstra travel directions; walk segments are estimates."
        local leg = path.legs[path.cursor]
        local remaining = ns.TravelPointDistance(position, leg.to)
        if leg.toID == "GOAL" then return end
        if position and position.mapID == leg.to.mapID and remaining and remaining <= (leg.method == "walk" and 20 or 100) then
            path.transportIndex = nil
            path.cursor = path.cursor + 1
        else
            local transport = leg.method ~= "walk"
            local target = transport and leg.from or leg.to
            local following = path.legs[path.cursor + 1]
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
    output("Settlement travel checks: " .. #(ns.travelData and ns.travelData.settlements or {})
        .. " published footprints; estimated 100-yard margin. Hostile ground crossings are excluded; roads/guards remain unverified.")
    if ns.routeStats and (ns.routeStats.hostileLines or 0) > 0 then
        output("Hostile ground preview lines hidden: " .. ns.routeStats.hostileLines .. ". Quest markers retained.")
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
