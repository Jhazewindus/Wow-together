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
    local nodes = policy and policy.nodes or data and data.nodes
    if not data or not nodes or not nodes[from] or not nodes[to] then return end
    local cache = referenceCache
    if policy then
        if not policy.lookup then policy.lookup = {} end
        cache = policy.lookup
    end
    if data ~= cache.data or nodes ~= cache.nodes then
        cache.data, cache.nodes, cache.graph, cache.rows, cache.count = data, nodes, {}, {}, 0
        local function link(a, b, distance)
            if nodes[a] and nodes[b] and finite(distance) and distance >= 0 then
                cache.graph[a] = cache.graph[a] or {}
                cache.graph[a][#cache.graph[a] + 1] = {to = b, distance = distance}
            end
        end
        for _, edge in ipairs(data.edges) do
            if policy and policy.tick then policy.tick() end
            -- Default lookup remains walk-only geometry for flight estimates.
            -- Fixed-guide policies may price published ordinary transports;
            -- neither lookup makes a personal flight/hearth usable.
            local distance = finite(edge.distance) and edge.distance
                or finite(edge.seconds) and edge.seconds == 0 and 0 or nil
            local a, b = nodes[edge.from], nodes[edge.to]
            local okay = a and b
            if policy and okay then
                okay = (not edge.faction or edge.faction == "Both" or edge.faction == policy.faction)
                    and ns.TravelNodeAllowed(edge.from, a, nil, policy.safety)
                    and ns.TravelNodeAllowed(edge.to, b, nil, policy.safety)
                if edge.method == "walk" then
                    okay = okay and not ns.HostileWalkCrossing(a, b, policy.safety)
                        and not ns.TerrainWalkCrossing(a, b, policy.terrain)
                    if not distance then
                        local length = ns.TravelPointDistance(a, b, policy.metrics)
                        distance = length and length * 1.25
                    end
                elseif edge.method == "ship" or edge.method == "zeppelin" or edge.method == "tram" or edge.method == "transition" then
                    distance = finite(edge.seconds) and edge.seconds >= 0 and edge.seconds * 7 or nil
                else okay = false end
            end
            if okay and (policy or edge.method == "walk") and distance and distance >= 0 then
                link(edge.from, edge.to, distance)
            end
        end
        -- Fixed-guide policies use the live router's existing visibility
        -- points. This prices mapped detours without importing character
        -- flights or changing the published/default flight geometry graph.
        for mapID, map in pairs(policy and policy.terrain and policy.terrain.maps or {}) do
            for _, edge in ipairs(map.edges) do
                local a, b = nodes[edge.from], nodes[edge.to]
                if a and b and not ns.HostileWalkCrossing(a, b, policy.safety) then
                    local length = ns.TravelPointDistance(a, b, policy.metrics)
                    link(edge.from, edge.to, length and length * 1.25)
                    link(edge.to, edge.from, length and length * 1.25)
                end
                if policy.tick then policy.tick() end
            end
            for id, point in pairs(nodes) do
                local indoor = point.container and (string.find(point.container, "wizards_sanctum", 1, true)
                    or string.find(point.container, "blackrock_mountain", 1, true))
                if not point.terrain and not indoor and point.mapID == mapID then
                    for corner, target in pairs(map.nodes) do
                        if nodes[corner] and not ns.HostileWalkCrossing(point, target, policy.safety)
                            and not ns.TerrainWalkCrossing(point, target, policy.terrain) then
                            local length = ns.TravelPointDistance(point, target, policy.metrics)
                            link(id, corner, length and length * 1.25)
                            link(corner, id, length and length * 1.25)
                        end
                        if policy.tick then policy.tick() end
                    end
                end
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
    if point.trail then return name or "Path waypoint", true end
    if point.personal then return name or "your destination" end
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

-- Straight chords across a map that has proven ground cost this much more
-- per yard than the ground itself, so a known road wins unless the chord
-- is far shorter. Maps without recorded/bundled ground keep plain estimates.
local OFFROAD = 2.0
local function isIndoor(point)
    return point.container and (string.find(point.container, "wizards_sanctum", 1, true)
        or string.find(point.container, "blackrock_mountain", 1, true)) or false
end

function ns.FindTravelPath(origin, goal, useFlights, discoverySource)
    if not ns.ValidTravelPoint(origin) or not ns.ValidTravelPoint(goal) then return end
    local data, speed, positions = ns.travelData or {nodes = {}, edges = {}, factors = {}}, ns.TravelWalkSpeed(), {}
    local nodes, adjacency = {START = origin, GOAL = goal}, {}
    local faction = ns.profile and ns.profile.faction
    local safety = ns.TravelSafetyContext()
    local terrain = ns.TravelTerrainContext()
    local trails = ns.TravelTrailContext and ns.TravelTrailContext() or {maps = {}}
    local personal = ns.PersonalTransports and ns.PersonalTransports() or {}
    -- Proven ground is loaded for the maps this trip touches; other zones keep
    -- their published estimates until the route re-plans on arrival there.
    local relevant = {[origin.mapID] = true, [goal.mapID] = true}
    for _, transport in ipairs(personal) do if ns.ValidTravelPoint(transport.point) then relevant[transport.point.mapID] = true end end
    local covered = {}
    for mapID in pairs(relevant) do covered[mapID] = ns.TrailMapCovered and ns.TrailMapCovered(mapID, trails) or false end
    local function offRoad(mapID) return covered[mapID] and OFFROAD or 1 end
    local function link(from, to, seconds, method, extra, terrainVisible)
        if not nodes[from] or not nodes[to] or not finite(seconds) or seconds < 0 then return end
        if method == "walk" and ns.HostileWalkCrossing(nodes[from], nodes[to], safety, from == "START", to == "GOAL") then return end
        if method == "walk" and not terrainVisible and ns.TerrainWalkCrossing(nodes[from], nodes[to], terrain) then return end
        adjacency[from] = adjacency[from] or {}
        adjacency[from][#adjacency[from] + 1] = {from = from, to = to, seconds = seconds, method = method, flight = extra}
    end
    -- A straight walking estimate between two points that are not proven ground.
    local function chord(a, b, mapID)
        local length = ns.TravelPointDistance(a, b, positions)
        return length and length * factor(mapID) * offRoad(mapID) / speed
    end
    for id, point in pairs(data.nodes) do
        if ns.ValidTravelPoint(point) and allowed(point, faction) and ns.TravelNodeAllowed(id, point, nil, safety) then nodes[id] = point end
    end
    for _, map in pairs(terrain.maps) do
        for id, point in pairs(map.nodes) do
            if ns.TravelNodeAllowed(id, point, nil, safety) then nodes[id] = point end
        end
    end
    for mapID, map in pairs(trails.maps) do
        if relevant[mapID] and map.count > 0 then
            for id, point in pairs(map.nodes) do
                if ns.TravelNodeAllowed(id, point, nil, safety) then nodes[id] = point end
            end
        end
    end
    for _, transport in ipairs(personal) do
        if ns.ValidTravelPoint(transport.point) and ns.TravelNodeAllowed(transport.id, transport.point, nil, safety) then
            nodes[transport.id] = {mapID = transport.point.mapID, x = transport.point.x, y = transport.point.y,
                name = transport.name, personal = transport}
        end
    end
    local flights = ns.char and ns.char.flights
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
            local a, b = nodes[edge.from], nodes[edge.to]
            if edge.distance then
                cost = edge.distance / speed
                if edge.method == "walk" and a.mapID == b.mapID then cost = cost * offRoad(a.mapID) end
            elseif cost == nil then
                local length = ns.TravelPointDistance(a, b, positions)
                cost = length and length * (factor(a.mapID) + factor(b.mapID)) / 2 / speed
                if cost and edge.method == "walk" and a.mapID == b.mapID then cost = cost * offRoad(a.mapID) end
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
            if id ~= "START" and id ~= "GOAL" and not point.terrain and not point.trail and point.mapID == mapID and not isIndoor(point) then
                for terrainID, corner in pairs(map.nodes) do
                    if nodes[terrainID] then
                        local seconds = chord(point, corner, mapID)
                        link(id, terrainID, seconds, "walk")
                        link(terrainID, id, seconds, "walk")
                    end
                end
            end
        end
    end
    -- Proven ground: recorded or bundled road segments cost their real length
    -- and bypass the terrain silhouette, because they were walked.
    local function ground(from, to, seconds)
        if not nodes[from] or not nodes[to] then return end
        adjacency[from] = adjacency[from] or {}
        adjacency[from][#adjacency[from] + 1] = {from = from, to = to, seconds = seconds, method = "walk"}
    end
    for mapID, map in pairs(trails.maps) do
        if relevant[mapID] then
            for _, edge in ipairs(ns.TrailUsableEdges(mapID, safety, trails)) do
                ground(edge.a, edge.b, edge.length / speed)
                ground(edge.b, edge.a, edge.length / speed)
            end
            -- Borders, gates, flight masters and landings join the nearest
            -- proven ground; START and GOAL also join everything below.
            for id, point in pairs(nodes) do
                if id ~= "START" and id ~= "GOAL" and not point.trail and not point.terrain and point.mapID == mapID and not isIndoor(point) then
                    for _, near in ipairs(ns.NearestTrailNodes(mapID, point, nil, nil, trails)) do
                        if nodes[near.id] then
                            local seconds = near.distance * factor(mapID) * offRoad(mapID) / speed
                            link(id, near.id, seconds, "walk")
                            link(near.id, id, seconds, "walk")
                        end
                    end
                end
            end
        end
    end
    -- Personal transports leave only from the current position and land on
    -- their own map, where they join the published nodes like any other place.
    for _, transport in ipairs(personal) do
        local landing = nodes[transport.id]
        if landing then
            link("START", transport.id, transport.seconds, transport.method)
            for id, point in pairs(nodes) do
                if id ~= transport.id and id ~= "START" and not point.trail and not point.personal
                    and point.mapID == landing.mapID and not isIndoor(point) then
                    link(transport.id, id, chord(landing, point, landing.mapID), "walk")
                end
            end
        end
    end
    if useFlights then
        local observed = {}
        for _, edge in pairs(flights and flights.edges or {}) do
            local source, target = flights.nodes[edge.source], flights.nodes[edge.destination]
            if source and target and source.known == true and target.known == true then
                observed[edge.source .. ":" .. edge.destination] = true
                local air, estimate = ns.FlightPointDistance(source, target, positions, edge.source, edge.destination)
                local duration, measured, basis = ns.FlightDuration(edge.source, edge.destination, air, positions, estimate)
                if duration then link("TAXI_" .. edge.source, "TAXI_" .. edge.destination, duration + 45, "taxi",
                    {source = source, destination = target, flightSeconds = duration, measured = measured, timingBasis = basis}) end
            end
        end
        -- Two masters this character has unlocked are connected by their
        -- published route even before the departure map was opened here.
        -- Those legs say so; opening the map replaces the estimate.
        for _, edge in ipairs(data.flightConnections or {}) do
            local key = edge.source .. ":" .. edge.destination
            local source, target = flights and flights.nodes[edge.source], flights and flights.nodes[edge.destination]
            if not observed[key] and allowed(edge, faction) and nodes["TAXI_" .. edge.source] and nodes["TAXI_" .. edge.destination]
                and source and target and ns.Public(source.known) and source.known == true
                and ns.Public(target.known) and target.known == true
                and not (flights.unreachable and flights.unreachable[key]) then
                -- The published duration already includes any intermediate
                -- stops; the air-distance estimate only fills a missing value.
                local duration = finite(edge.seconds) and edge.seconds > 0 and edge.seconds or nil
                if not duration then
                    local air, estimate = ns.FlightPointDistance(source, target, positions, edge.source, edge.destination)
                    duration = ns.FlightDuration(edge.source, edge.destination, air, positions, estimate)
                end
                if finite(duration) and duration > 0 then
                    link("TAXI_" .. edge.source, "TAXI_" .. edge.destination, duration + 45, "taxi",
                        {source = source, destination = target, flightSeconds = duration, measured = false,
                            timingBasis = "Published connection estimate", unconfirmed = true})
                end
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
        -- Chords to proven ground carry the off-road price; the ground itself
        -- is then free to follow, so the router leaves and joins roads where
        -- that is cheapest rather than at a fixed attachment point.
        local indoor = isIndoor(p)
        if not indoor and not p.personal and not p.trail and p.mapID == origin.mapID then
            link("START", id, chord(origin, p, p.mapID), "walk")
        end
        if not indoor and not p.trail and p.mapID == goal.mapID then
            link(id, "GOAL", chord(p, goal, p.mapID), "walk")
        end
    end
    -- Proven ground joins the trip at the nearest few recorded points to each
    -- end; the road itself is free to follow from there in either direction.
    for _, near in ipairs(ns.NearestTrailNodes(origin.mapID, origin, 8, nil, trails)) do
        if nodes[near.id] then link("START", near.id, near.distance * factor(origin.mapID) * offRoad(origin.mapID) / speed, "walk") end
    end
    for _, near in ipairs(ns.NearestTrailNodes(goal.mapID, goal, 8, nil, trails)) do
        if nodes[near.id] then link(near.id, "GOAL", near.distance * factor(goal.mapID) * offRoad(goal.mapID) / speed, "walk") end
    end
    if origin.mapID == goal.mapID then
        link("START", "GOAL", chord(origin, goal, origin.mapID), "walk")
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
    local legs, hasTerrain, hasTrail, hasPersonal = {}, false, false, false
    for index = #reverse, 1, -1 do
        local edge = reverse[index]
        local name, waypoint = nodeName(edge.to, nodes[edge.to])
        legs[#legs + 1] = {from = nodes[edge.from], to = nodes[edge.to], method = edge.method,
            fromID = edge.from, toID = edge.to, name = name, waypoint = waypoint,
            seconds = edge.seconds, flight = edge.flight}
        if edge.method == "walk" and (nodes[edge.from].terrain or nodes[edge.to].terrain) then hasTerrain = true end
        if edge.method == "walk" and (nodes[edge.from].trail or nodes[edge.to].trail) then hasTrail = true end
        if edge.method == "hearth" or edge.method == "teleport" then hasPersonal = true end
    end
    return {legs = legs, seconds = costs.GOAL, cursor = 1, origin = origin, goal = goal,
        hasTerrain = hasTerrain, hasTrail = hasTrail, hasPersonal = hasPersonal}
end

function ns.ResetTravelPath()
    ns.travelPath, ns.travelPathSignature, ns.travelPathChecked, ns.travelPathReplanned, ns.travelWaypoint = nil, nil, nil, nil, nil
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
        or method == "zeppelin" and "Take the zeppelin" or method == "tram" and "Take the tram"
        or method == "hearth" and "Use your Hearthstone" or method == "teleport" and "Teleport" or "Use the passage"
end

local function travelMinutes(seconds)
    if not finite(seconds) or seconds < 0 then return end
    if seconds < 60 then return "~" .. math.floor(seconds + 0.5) .. " sec" end
    return "~" .. math.floor(seconds / 60 + 0.5) .. " min"
end

local function summarizedLegs(path)
    local parts, walking, flight = {}, 0, nil
    local function flushWalk()
        if walking <= 0 then return end
        parts[#parts + 1] = "walk " .. (travelMinutes(walking) or "")
        walking = 0
    end
    for index = math.max(1, path.cursor or 1), #(path.legs or {}) do
        local leg = path.legs[index]
        local method = leg.method
        if method == "walk" then
            walking = walking + (finite(leg.seconds) and leg.seconds or 0)
        else
            flushWalk()
            local label = leg.name
            if method == "teleport" then parts[#parts + 1] = "Teleport"
            elseif method == "hearth" then parts[#parts + 1] = "Use your Hearthstone"
            elseif method == "taxi" then
                local info = type(leg.flight) == "table" and leg.flight
                flight = info or flight
                local target = info and info.destination and info.destination.name or label or "the next flight point"
                local detail = info and (info.measured and "Timed flight: "
                    or info.unconfirmed and "Published estimate: " or "Estimated flight: ")
                if detail and finite(info.flightSeconds) then detail = detail .. ns.FormatTravelDuration(info.flightSeconds) end
                parts[#parts + 1] = "Fly to " .. target .. (detail and (" (" .. detail .. ")") or "")
            elseif method == "ship" or method == "zeppelin" or method == "tram" then
                parts[#parts + 1] = transportAction(method) .. (label and (" to " .. label) or "")
            else
                parts[#parts + 1] = transportAction(method) .. (label and (" to " .. label) or "")
            end
        end
    end
    flushWalk()
    if #parts == 0 then return end
    parts[1] = string.upper(string.sub(parts[1], 1, 1)) .. string.sub(parts[1], 2)
    local summary = table.concat(parts, ", then ")
    if flight and finite(path.seconds) then summary = summary .. " (journey ~" .. ns.FormatTravelDuration(path.seconds) .. ")" end
    return summary
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
    local summary = summarizedLegs(path)
    if summary then return summary .. "." end
    if stop.travelLeg then return "Travel towards " .. ns.MapName(stop.goal.mapID) .. "." end
end

-- The furthest upcoming proven-ground node that a straight walk from the
-- player still reaches without leaving the recorded path, so the arrow does
-- not flick between 12-yard samples on a straight road.
local function smoothedTarget(path, position)
    local leg = path.legs[path.cursor]
    local target = leg.to
    if not position or leg.method ~= "walk" or not leg.to.trail or position.mapID ~= leg.to.mapID then return target end
    for ahead = path.cursor + 1, math.min(#path.legs, path.cursor + 12) do
        local candidate = path.legs[ahead]
        if candidate.method ~= "walk" or not candidate.to.trail then break end
        local distance = ns.TravelPointDistance(position, candidate.to)
        if not distance or distance > 150 then break end
        local straight = true
        for between = path.cursor, ahead - 1 do
            local off = ns.TravelSegmentDistance(path.legs[between].to, position, candidate.to)
            if not off or off > 25 then straight = false; break end
        end
        if not straight or ns.TerrainWalkCrossing(position, candidate.to)
            or ns.HostileWalkCrossing(position, candidate.to, nil, true, false) then break end
        target = candidate.to
    end
    return target
end

-- The place the current run of waypoints is heading for, for labels.
local function runDestination(path, stop)
    for index = path.cursor, #path.legs do
        local leg = path.legs[index]
        if leg.toID == "GOAL" then return ns.SafeTitle(stop.title) and "your destination" or ns.MapName(stop.mapID) end
        if leg.method ~= "walk" then return nodeName(leg.fromID, leg.from) end
        if not leg.to.trail and not leg.to.terrain then return leg.name end
    end
    return "your destination"
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
        ns.TravelWalkSpeed(), ns.PersonalTransportSignature and ns.PersonalTransportSignature() or ""}, ":")
    local now = ns.ReadPublic(GetTime)
    local checkMovement = not holding and path and (not finite(now) or not ns.travelPathChecked or now - ns.travelPathChecked >= 2)
    -- Reaching any of the next few recorded points counts as progress along
    -- the path, including corners cut on open ground.
    if path and position and not holding then
        local reached
        for index = path.cursor, math.min(#path.legs, path.cursor + 8) do
            local leg = path.legs[index]
            if leg.method ~= "walk" or not leg.to.trail then break end
            local distance = position.mapID == leg.to.mapID and ns.TravelPointDistance(position, leg.to)
            if distance and distance <= 25 then reached = index end
        end
        if reached then path.cursor, path.transportIndex = reached + 1, nil end
    end
    local moved = checkMovement and ns.TravelPointDistance(position, path.origin)
    local detour = moved and moved > 250
    if checkMovement and (path.hasTerrain or path.hasTrail) then
        local leg = path.legs[path.cursor]
        local distance = leg and leg.method == "walk" and ns.TravelSegmentDistance(position, leg.from, leg.to)
        -- Following the same segment is progress, not a reason to replace a
        -- corner waypoint. Reattach only after a real departure from it.
        if distance then detour = distance > 90 end
    end
    if checkMovement then ns.travelPathChecked = finite(now) and now or nil end
    local signatureChanged = ns.travelPathSignature ~= signature
    local lastReplan = ns.travelPathReplanned
    local detourReady = finite(now) and (not finite(lastReplan) or now < lastReplan or now - lastReplan >= 5)
        or not finite(now) and lastReplan == nil
    if not holding and (signatureChanged or detour and detourReady
        or not path and (not finite(now) or not ns.travelPathChecked or now - ns.travelPathChecked >= 1)) then
        ns.travelPathSignature = signature
        ns.travelPathChecked = finite(now) and now or nil
        ns.travelPathReplanned = finite(now) and now or false
        ns.travelPath = ns.FindTravelPath(position, stop, ns.Option("suggestFlights"))
        if ns.travelPath then ns.travelPath.selectionKey = ns.routeSelection and ns.routeSelection.key end
        ns.travelNetworkStatus = ns.travelPath and (ns.travelPath.hasTrail
            and "Dijkstra directions along recorded/bundled ground; chords off it are estimates."
            or ns.travelPath.hasTerrain
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
            or (path.hasTrail and "Dijkstra directions along recorded/bundled ground; chords off it are estimates."
                or path.hasTerrain and "Dijkstra directions around mapped terrain; footprints are estimates."
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
            local personal = leg.method == "hearth" or leg.method == "teleport"
            local transport = leg.method ~= "walk" and not personal
            local target = transport and leg.from or personal and leg.to or smoothedTarget(path, position)
            local instruction
            if personal then instruction = ns.PersonalTransportLabel(leg)
            elseif transport then instruction = transportAction(leg.method) .. " to " .. leg.name
            elseif following and following.flight then instruction = "Walk to " .. following.flight.source.name .. " (flight master)"
            elseif leg.to.trail then instruction = "Follow the " .. (leg.to.bundled and "road" or "known path") .. " towards " .. runDestination(path, stop)
            else instruction = (leg.waypoint and "Go to " or "Head to ") .. leg.name end
            local result = {id = stop.id, kind = "travel", title = stop.title, mapID = target.mapID, x = target.x, y = target.y,
                action = "travel", label = instruction, travelLeg = leg, goal = stop, guideStep = stop.guideStep}
            if following and following.flight then result.flightMasterTarget = following.flight.source end
            if personal then result.personalTransport = true end
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
    if ns.TravelTrailDiagnostics then ns.TravelTrailDiagnostics(output) end
    if ns.PersonalTransportDiagnostics then ns.PersonalTransportDiagnostics(output) end
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
