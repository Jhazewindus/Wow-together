local addonName, ns = ...

-- Proven ground for every zone. A trail graph per map holds two kinds of
-- walkable edges: ground this character actually walked (recorded passively
-- while playing, saved per character) and roads bundled in TravelRoadData.lua
-- (which /wt roads export produces from recorded ground). The router prefers
-- these edges to straight chords, so a route follows a road around a ridge
-- instead of cutting through it, in any zone that has been walked once.
--
-- Nothing here changes quest steps, completion credit, flight unlocks or the
-- fixed-guide comparison; it only shapes the live arrow and map line.
local SNAP, STEP, JUMP = 14, 20, 60         -- yards: merge radius, sample spacing, teleport/fall break
local SAMPLE, MAX_NODES, CELL = 0.5, 2500, 0.02 -- seconds, nodes per map, grid cell (normalized)
local ATTACH_RANGE, ATTACH_COUNT = 1200, 3   -- yards: how far a stop may be from the nearest proven ground
local MIN_COVERAGE = 12                      -- nodes before a map is considered to have usable ground

local SHARE_INTERVAL, SHARE_TRICKLE, SHARE_MAP_MESSAGES, SHARE_PENDING = 30, 3, 80, 400
local graphs, scales, last, elapsed, status = {}, {}, nil, 0, "Not started."
local pendingShare, sentEdges, sharedMaps, shareClock, shareStats = {}, {}, {}, 0, {sent = 0, received = 0, points = 0}
local currentPoint = {}

local function finite(value)
    return ns.Public(value) and type(value) == "number" and value == value and value > -math.huge and value < math.huge
end
local function saved() return ns.db and ns.db.trails end
local function cellKey(x, y) return math.floor(x / CELL) .. ":" .. math.floor(y / CELL) end

local function scale(mapID)
    local known = scales[mapID]
    if known then return known[1], known[2] end
    local w, h
    if C_Map then w, h = ns.ReadPublic(C_Map.GetMapWorldSize, mapID) end
    if finite(w) and finite(h) and w > 0 and h > 0 and w < 1000000 and h < 1000000 then
        scales[mapID] = {w, h}
        return w, h
    end
end

local function yards(mapID, a, b)
    local w, h = scale(mapID)
    if not w then return end
    return math.sqrt(((a.x - b.x) * w)^2 + ((a.y - b.y) * h)^2)
end

local function newGraph(mapID)
    return {mapID = mapID, nodes = {}, links = {}, edges = {}, usable = {}, cells = {}, count = 0, learned = 0, bundled = 0, revision = 0}
end

local function addNode(map, id, x, y, bundled)
    local point = {mapID = map.mapID, x = x, y = y, trail = true, bundled = bundled or nil,
        name = bundled and "Road waypoint" or "Path waypoint"}
    map.nodes[id], map.links[id] = point, {}
    local key = cellKey(x, y)
    map.cells[key] = map.cells[key] or {}
    table.insert(map.cells[key], id)
    map.count = map.count + 1
    if bundled then map.bundled = map.bundled + 1 else map.learned = map.learned + 1 end
    return id
end

local function addLink(map, a, b)
    if a == b or not map.links[a] or not map.links[b] or map.links[a][b] then return false end
    map.links[a][b], map.links[b][a] = true, true
    map.edges[#map.edges + 1] = {a = a, b = b, length = yards(map.mapID, map.nodes[a], map.nodes[b])}
    return true
end

local function scan(map, p, radius, count, w, h)
    local rx, ry = radius / w, radius / h
    local x0, x1 = math.floor((p.x - rx) / CELL), math.floor((p.x + rx) / CELL)
    local y0, y1 = math.floor((p.y - ry) / CELL), math.floor((p.y + ry) / CELL)
    if x1 - x0 > 60 then x0, x1 = math.floor(p.x / CELL) - 30, math.floor(p.x / CELL) + 30 end
    if y1 - y0 > 60 then y0, y1 = math.floor(p.y / CELL) - 30, math.floor(p.y / CELL) + 30 end
    local found = {}
    for cx = x0, x1 do
        for cy = y0, y1 do
            for _, id in ipairs(map.cells[cx .. ":" .. cy] or {}) do
                local node = map.nodes[id]
                local distance = yards(map.mapID, p, node)
                if distance and distance <= radius then found[#found + 1] = {id = id, point = node, distance = distance} end
            end
        end
    end
    table.sort(found, function(a, b) return a.distance < b.distance or a.distance == b.distance and a.id < b.id end)
    while #found > (count or 1) do table.remove(found) end
    return found
end

-- Nearest proven-ground nodes within `radius` yards of p (same map). Rings
-- keep the common nearby case cheap; the full radius is only scanned when
-- the near rings are empty.
local function nearest(map, p, radius, count)
    local w, h = scale(map.mapID)
    if not w or map.count == 0 then return {} end
    for _, ring in ipairs({100, 400}) do
        if ring < radius then
            local found = scan(map, p, ring, count, w, h)
            if #found >= (count or 1) then return found end
        end
    end
    return scan(map, p, radius, count, w, h)
end

local function nearestOne(map, p, radius)
    local w, h = scale(map.mapID)
    if not w or map.count == 0 then return end
    local rx, ry = radius / w, radius / h
    local x0, x1 = math.floor((p.x - rx) / CELL), math.floor((p.x + rx) / CELL)
    local y0, y1 = math.floor((p.y - ry) / CELL), math.floor((p.y + ry) / CELL)
    if x1 - x0 > 60 then x0, x1 = math.floor(p.x / CELL) - 30, math.floor(p.x / CELL) + 30 end
    if y1 - y0 > 60 then y0, y1 = math.floor(p.y / CELL) - 30, math.floor(p.y / CELL) + 30 end
    local best, bestDistance
    for cx = x0, x1 do
        for cy = y0, y1 do
            for _, id in ipairs(map.cells[cx .. ":" .. cy] or {}) do
                local node = map.nodes[id]
                local distance = yards(map.mapID, p, node)
                if distance and distance <= radius and (not bestDistance or distance < bestDistance
                    or distance == bestDistance and id < best) then
                    best, bestDistance = id, distance
                end
            end
        end
    end
    return best
end

local function compileBundled(map, source)
    local w, h = scale(map.mapID)
    w, h = w or 5000, h or 3333 -- spacing estimate only; coordinates stay normalized
    for _, road in ipairs(source and source.roads or {}) do
        local previous
        for _, pair in ipairs(road.points or {}) do
            local x, y = pair[1], pair[2]
            if finite(x) and finite(y) and x >= 0 and x <= 1 and y >= 0 and y <= 1 then
                local here = {mapID = map.mapID, x = x, y = y}
                -- Interpolate long segments so stops can attach along the road.
                local steps = 1
                if previous then
                    local length = math.sqrt(((x - previous.x) * w)^2 + ((y - previous.y) * h)^2)
                    steps = math.max(1, math.ceil(length / (STEP * 2)))
                end
                for step = 1, steps do
                    local px = previous and previous.x + (x - previous.x) * step / steps or x
                    local py = previous and previous.y + (y - previous.y) * step / steps or y
                    local sample = {mapID = map.mapID, x = px, y = py}
                    local near = nearest(map, sample, SNAP, 1)[1]
                    local id = near and near.id or addNode(map, "TRAIL_" .. map.mapID .. "_B" .. (map.bundled + 1), px, py, true)
                    if previous and previous.id then addLink(map, previous.id, id) end
                    previous = {x = px, y = py, id = id}
                end
                previous.x, previous.y = x, y
            end
        end
    end
end

local function compileLearned(map, record)
    for index, pair in ipairs(record and record.n or {}) do
        local x, y = pair[1], pair[2]
        if finite(x) and finite(y) and x >= 0 and x <= 1 and y >= 0 and y <= 1 then
            addNode(map, "TRAIL_" .. map.mapID .. "_L" .. index, x, y, false)
        else map.learned = map.learned + 1 end -- keep saved indices stable
    end
    for _, pair in ipairs(record and record.e or {}) do
        addLink(map, "TRAIL_" .. map.mapID .. "_L" .. tostring(pair[1]), "TRAIL_" .. map.mapID .. "_L" .. tostring(pair[2]))
    end
end

local function graph(mapID)
    local map = graphs[mapID]
    if map then return map end
    map = newGraph(mapID)
    local store = saved()
    compileLearned(map, store and store[mapID])
    local bundled = ns.travelRoadData and ns.travelRoadData.maps and ns.travelRoadData.maps[mapID]
    if bundled then compileBundled(map, bundled) end
    graphs[mapID] = map
    return map
end

function ns.TravelTrailContext()
    local maps = {}
    for mapID in pairs(saved() or {}) do if ns.GuideInteger(mapID) and mapID > 0 then maps[mapID] = graph(mapID) end end
    for mapID in pairs(ns.travelRoadData and ns.travelRoadData.maps or {}) do
        if ns.GuideInteger(mapID) and mapID > 0 then maps[mapID] = graph(mapID) end
    end
    return {maps = maps}
end

function ns.TrailMapCovered(mapID, context)
    local map = context and context.maps[mapID] or graphs[mapID]
    return map ~= nil and map.count >= MIN_COVERAGE
end

function ns.NearestTrailNodes(mapID, point, count, radius, context)
    local map = context and context.maps[mapID] or graphs[mapID]
    if not map or not ns.ValidTravelPoint(point) or point.mapID ~= mapID then return {} end
    return nearest(map, point, radius or ATTACH_RANGE, count or ATTACH_COUNT)
end

function ns.TrailYards(mapID, a, b) return yards(mapID, a, b) end

-- Walkable edges for this character's faction, each once, with lengths.
-- Hostile-settlement checks run once per edge and are cached across route
-- computations; only edges recorded since the last call are re-checked.
function ns.TrailUsableEdges(mapID, safety, context)
    local map = context and context.maps[mapID] or graphs[mapID]
    if not map then return {} end
    local faction = safety and safety.faction or "none"
    local cache = map.usable[faction]
    if not cache then cache = {count = 0, edges = {}}; map.usable[faction] = cache end
    for index = cache.count + 1, #map.edges do
        local edge = map.edges[index]
        if not edge.length then edge.length = yards(mapID, map.nodes[edge.a], map.nodes[edge.b]) end
        if edge.length and not ns.HostileWalkCrossing(map.nodes[edge.a], map.nodes[edge.b], safety) then
            cache.edges[#cache.edges + 1] = edge
        end
    end
    cache.count = #map.edges
    return cache.edges
end

local function inParty()
    if not ns.PartyFeaturesEnabled or not ns.PartyFeaturesEnabled() then return false end
    local raid, grouped = ns.ReadPublic(IsInRaid), ns.ReadPublic(IsInGroup)
    return raid == false and grouped == true
end

-- Passive recording -------------------------------------------------------

local function recordable()
    if not ns.Option("learnRoads") or not saved() then return false, "Road learning is off." end
    if ns.ReadPublic(UnitOnTaxi, "player") == true then return false, "On a flight." end
    if ns.ReadPublic(UnitIsDeadOrGhost, "player") == true then return false, "Dead or ghost." end
    if type(IsFalling) == "function" and ns.ReadPublic(IsFalling) == true then return false, "Falling." end
    local inside, kind = ns.ReadPublic(IsInInstance)
    if inside == true and kind ~= "none" then return false, "Inside an instance." end
    return true
end

local function sample()
    local okay, reason = recordable()
    if not okay then last = nil; status = reason; return end
    -- A transport (ship, zeppelin, tram) moves the player at zero own speed.
    -- Those crossings are not ground; the published transport edges cover them.
    local speed = ns.ReadPublic(GetUnitSpeed, "player")
    if not finite(speed) or speed <= 0 then return end
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    local p = ns.GuideInteger(mapID) and mapID > 0 and ns.PlayerPoint(mapID, currentPoint)
    if not p then last = nil; status = "Position unavailable."; return end
    if not scale(mapID) then last = nil; status = "Map scale unavailable for map " .. mapID .. "."; return end
    local map = graph(mapID)
    if last and last.mapID ~= mapID then last = nil end
    if not sharedMaps[mapID] and inParty() then sharedMaps[mapID] = true; ns.ShareTrails(mapID, true) end
    if last then
        local moved = yards(mapID, p, last)
        if moved and moved > JUMP then last = nil
        elseif moved and moved < STEP then return end
    end
    local id = nearestOne(map, p, SNAP)
    local store = saved()
    local record = store[mapID]
    if not id then
        if map.learned >= MAX_NODES then
            status = ns.MapName(mapID) .. " has reached " .. MAX_NODES .. " recorded points; existing ground stays in use."
            last = last or {}
            last.mapID, last.x, last.y, last.id = mapID, p.x, p.y, nil
            return
        end
        record = record or {n = {}, e = {}}
        store[mapID] = record
        local x, y = math.floor(p.x * 10000 + 0.5) / 10000, math.floor(p.y * 10000 + 0.5) / 10000
        record.n[#record.n + 1] = {x, y}
        id = addNode(map, "TRAIL_" .. mapID .. "_L" .. #record.n, x, y, false)
    end
    if last and last.id and last.id ~= id and addLink(map, last.id, id) then
        local a, b = tonumber(string.match(last.id, "_L(%d+)$")), tonumber(string.match(id, "_L(%d+)$"))
        -- Learned-to-bundled joins live only in this session's graph; the
        -- bundled road is rebuilt from data on load, and the join recurs.
        if a and b then record = record or store[mapID]; record.e[#record.e + 1] = {a, b} end
        -- New ground joins the next route computation (a detour or a new
        -- goal); bumping the travel revision here would re-plan every sample.
        map.revision = map.revision + 1
    end
    last = last or {}
    last.mapID, last.id, last.x, last.y = mapID, id, p.x, p.y
    status = "Recording ground in " .. ns.MapName(mapID) .. ": " .. map.learned .. " points, " .. map.bundled .. " bundled."
end

function ns.InitializeTravelTrails()
    ns.db.trails = type(ns.db.trails) == "table" and ns.db.trails or {}
    graphs, last = {}, nil
    -- Saved history reaches peers through the per-map share on arrival; the
    -- periodic pass only sends edges recorded in this session.
    sentEdges, sharedMaps, pendingShare = {}, {}, {}
    for mapID, record in pairs(ns.db.trails) do sentEdges[mapID] = #(type(record) == "table" and record.e or {}) end
    if ns.trailFrame then return end
    local frame = CreateFrame("Frame")
    ns.trailFrame = frame
    frame:SetScript("OnUpdate", function(_, dt)
        elapsed = elapsed + (finite(dt) and dt or 0)
        if elapsed < SAMPLE then return end
        elapsed = 0
        local before = ns.StartMemorySample and ns.StartMemorySample(ns.MemorySampleSection.recorders)
        local okay, err = pcall(sample)
        if ns.EndMemorySample then ns.EndMemorySample(ns.MemorySampleSection.recorders, before) end
        if not okay then status = "Recorder error: " .. tostring(err); last = nil end
        shareClock = shareClock + SAMPLE
        if shareClock >= 2 then
            shareClock = 0
            okay, err = pcall(ns.PumpTrailSharing)
            if not okay then status = "Share error: " .. tostring(err) end
        end
    end)
end

-- Party sharing -----------------------------------------------------------
-- "1|W|<mapID>|x,y;x,y;.../x,y;..." carries runs of connected points in
-- 1/10000 map units. Receivers merge them exactly like their own samples
-- (snap within SNAP yards, link consecutive points), so one member's walk
-- becomes proven ground for everyone, and resends only cost bandwidth.
local function encodeShare(mapID, record, from, to)
    local runs, run = {}, nil
    for index = from, to do
        local edge = record.e[index]
        local a, b = edge[1], edge[2]
        local na, nb = record.n[a], record.n[b]
        -- Ground received from peers is not echoed back; a join between a
        -- received point and an own point still travels.
        if na and nb and not (na[3] == 1 and nb[3] == 1) then
            if run and run[#run] == a then run[#run + 1] = b
            elseif run and run[#run] == b then run[#run + 1] = a
            else run = {a, b}; runs[#runs + 1] = run end
        end
    end
    local function token(index)
        local node = record.n[index]
        return math.floor(node[1] * 10000 + 0.5) .. "," .. math.floor(node[2] * 10000 + 0.5)
    end
    local head = "1|W|" .. mapID .. "|"
    local messages, text, runsInText = {}, head, 0
    for _, chain in ipairs(runs) do
        local pointsInRun = 0
        for position, index in ipairs(chain) do
            local separator = pointsInRun == 0 and (runsInText == 0 and "" or "/") or ";"
            local piece = separator .. token(index)
            if #text + #piece > 255 then
                messages[#messages + 1] = text
                -- Continue a split run from its previous point so the edge survives.
                text, runsInText = head .. (pointsInRun > 0 and (token(chain[position - 1]) .. ";") or "") .. token(index), 1
                pointsInRun = pointsInRun > 0 and 2 or 1
            else
                text = text .. piece
                pointsInRun = pointsInRun + 1
                if pointsInRun == 1 then runsInText = runsInText + 1 end
            end
        end
    end
    if text ~= head then messages[#messages + 1] = text end
    return messages
end

function ns.ShareTrails(mapID, full)
    local store = saved()
    local record = store and store[mapID]
    if not ns.Option("shareObservations") or not record or not inParty() then return 0 end
    local from, to = full and 1 or (sentEdges[mapID] or 0) + 1, #record.e
    if from > to then return 0 end
    local messages = encodeShare(mapID, record, from, to)
    while full and #messages > SHARE_MAP_MESSAGES do table.remove(messages, 1) end
    for _, message in ipairs(messages) do pendingShare[#pendingShare + 1] = message end
    while #pendingShare > SHARE_PENDING do table.remove(pendingShare, 1) end
    sentEdges[mapID] = to
    return #messages
end

local shareTimer = 0
function ns.PumpTrailSharing()
    if not inParty() then
        if #pendingShare > 0 or next(sharedMaps) then pendingShare, sharedMaps = {}, {} end
        return
    end
    shareTimer = shareTimer + 2
    if shareTimer >= SHARE_INTERVAL then
        shareTimer = 0
        for mapID, record in pairs(saved() or {}) do
            -- Existing history travels with the per-map share on arrival;
            -- the periodic pass only sends edges recorded since the last one.
            if ns.GuideInteger(mapID) then ns.ShareTrails(mapID, false) end
        end
    end
    local transport = ns.TransportState and ns.TransportState() or {queued = 0}
    local room = transport.queued < 4 and SHARE_TRICKLE or 0
    if ns.ObjectiveLearningSharePump then room = ns.ObjectiveLearningSharePump(room) or room end
    while room > 0 and pendingShare[1] do
        if not ns.QueueMessage(pendingShare[1]) then break end
        table.remove(pendingShare, 1)
        shareStats.sent, room = shareStats.sent + 1, room - 1
    end
end

-- A new or refreshed peer gets the current map's ground again.
function ns.ResetTrailSharing()
    sharedMaps = {}
end

function ns.ReceiveTrailMessage(message, sender)
    if string.sub(message, 1, 4) ~= "1|W|" then return false end
    if not ns.Option("shareObservations") then return true, false, "observation sharing off" end
    local store = saved()
    if not store then return true, false, "no trail store" end
    local mapText, body = string.match(message, "^1|W|(%d+)|(.+)$")
    local mapID = tonumber(mapText)
    if not ns.GuideInteger(mapID, 1000000) or mapID <= 0 or not body or #body > 250 then return true, false, "invalid ground message" end
    if not scale(mapID) then return true, false, "map scale unavailable for shared ground" end
    local map = graph(mapID)
    local record = store[mapID]
    if not record then record = {n = {}, e = {}}; store[mapID] = record end
    local runs, points, added = 0, 0, 0
    for run in string.gmatch(body, "[^/]+") do
        runs = runs + 1
        if runs > 12 then break end
        local previous
        for xs, ys in string.gmatch(run, "(%d+),(%d+)") do
            points = points + 1
            if points > 40 then break end
            local x, y = tonumber(xs) / 10000, tonumber(ys) / 10000
            if x > 1 or y > 1 then return true, false, "invalid shared coordinate" end
            local p = {mapID = mapID, x = x, y = y}
            local near = nearest(map, p, SNAP, 1)[1]
            local id = near and near.id
            if not id and map.learned < MAX_NODES then
                record.n[#record.n + 1] = {x, y, 1}
                id = addNode(map, "TRAIL_" .. mapID .. "_L" .. #record.n, x, y, false)
                added = added + 1
            end
            if id and previous and previous ~= id and addLink(map, previous, id) then
                local a, b = tonumber(string.match(previous, "_L(%d+)$")), tonumber(string.match(id, "_L(%d+)$"))
                if a and b then record.e[#record.e + 1] = {a, b} end
                map.revision = map.revision + 1
            end
            previous = id
        end
    end
    shareStats.received, shareStats.points = shareStats.received + 1, shareStats.points + added
    return true, true
end

-- Export / maintenance ----------------------------------------------------

local function polylines(map)
    -- Walk unvisited learned edges into chains for the bundled data format.
    local visited, chains = {}, {}
    local ids = {}
    for id in pairs(map.nodes) do if not map.nodes[id].bundled then ids[#ids + 1] = id end end
    table.sort(ids)
    local function degree(id) local n = 0; for _ in pairs(map.links[id]) do n = n + 1 end; return n end
    local function edgeKey(a, b) return a < b and a .. "|" .. b or b .. "|" .. a end
    local function extend(start)
        local chain, cursor = {start}, start
        while true do
            local nextID
            local options = {}
            for other in pairs(map.links[cursor]) do if not visited[edgeKey(cursor, other)] then options[#options + 1] = other end end
            table.sort(options)
            nextID = options[1]
            if not nextID then break end
            visited[edgeKey(cursor, nextID)] = true
            chain[#chain + 1], cursor = nextID, nextID
            if #chain >= 400 then break end
        end
        return chain
    end
    for pass = 1, 2 do
        for _, id in ipairs(ids) do
            if (pass == 1 and degree(id) == 1 or pass == 2) then
                while true do
                    local pending = false
                    for other in pairs(map.links[id]) do if not visited[edgeKey(id, other)] then pending = true; break end end
                    if not pending then break end
                    local chain = extend(id)
                    if #chain >= 2 then chains[#chains + 1] = chain end
                end
            end
        end
    end
    return chains
end

function ns.ExportTrails(mapID)
    local map = graph(mapID)
    local chains = polylines(map)
    local lines = {string.format("    [%d] = {name = %q, roads = {", mapID, ns.MapName(mapID))}
    for index, chain in ipairs(chains) do
        lines[#lines + 1] = string.format("        {id = \"walked-%d\", source = \"recorded\", points = {", index)
        local row = {}
        for _, id in ipairs(chain) do
            local node = map.nodes[id]
            row[#row + 1] = string.format("{%.4f, %.4f}", node.x, node.y)
            if #row == 4 then lines[#lines + 1] = "            " .. table.concat(row, ", ") .. ","; row = {} end
        end
        if #row > 0 then lines[#lines + 1] = "            " .. table.concat(row, ", ") .. "," end
        lines[#lines + 1] = "        }},"
    end
    lines[#lines + 1] = "    }},"
    return table.concat(lines, "\n"), #chains, map.learned
end

function ns.ClearTrails(mapID)
    local store = saved()
    if not store then return end
    if mapID then store[mapID] = nil; graphs[mapID] = nil else
        for key in pairs(store) do store[key] = nil end
        graphs = {}
    end
    last, pendingShare, sentEdges, sharedMaps = nil, {}, {}, {}
    ns.travelRevision = (ns.travelRevision or 0) + 1
    ns.ResetTravelPath()
end

function ns.TravelTrailDiagnostics(output)
    local store = saved() or {}
    local maps, learned = 0, 0
    for mapID, record in pairs(store) do maps, learned = maps + 1, learned + #(record.n or {}) end
    local bundled = 0
    for _, source in pairs(ns.travelRoadData and ns.travelRoadData.maps or {}) do bundled = bundled + #(source.roads or {}) end
    output("Proven ground: " .. learned .. " recorded points in " .. maps .. " map(s); " .. bundled
        .. " bundled road polyline(s). Recorder: " .. status)
    output("Ground sharing: " .. (ns.Option("shareObservations") and "on" or "off") .. "; " .. shareStats.sent .. " message(s) sent, "
        .. shareStats.received .. " received (" .. shareStats.points .. " new points), " .. #pendingShare .. " pending.")
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    if ns.GuideInteger(mapID) and mapID > 0 then
        local map = graph(mapID)
        output("Current map " .. mapID .. " (" .. ns.MapName(mapID) .. "): " .. map.learned .. " recorded + " .. map.bundled
            .. " bundled points; " .. (map.count >= MIN_COVERAGE and "routes prefer this ground." or "below the " .. MIN_COVERAGE .. "-point minimum, straight estimates remain."))
    end
end

function ns.TravelTrailCommand(argument)
    argument = string.lower(argument or "")
    local mapID = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    if argument == "export" then
        if not ns.GuideInteger(mapID) or mapID <= 0 then ns.Print("Current map unavailable."); return end
        local text, chains, points = ns.ExportTrails(mapID)
        ns.ShowLuaConsole()
        if ns.luaConsole and ns.luaConsole.output then
            ns.luaConsole.output:SetText("-- Paste into TravelRoadData.lua under ns.travelRoadData.maps\n" .. text)
        end
        ns.Print("Exported " .. chains .. " walked path(s) from " .. points .. " recorded points in " .. ns.MapName(mapID) .. " to the Lua console output.")
    elseif argument == "clear" then
        if not ns.GuideInteger(mapID) or mapID <= 0 then ns.Print("Current map unavailable."); return end
        ns.ClearTrails(mapID)
        ns.Print("Recorded ground cleared for " .. ns.MapName(mapID) .. ". Bundled roads remain.")
    elseif argument == "clear all" then
        ns.ClearTrails()
        ns.Print("All recorded ground cleared for this character. Bundled roads remain.")
    elseif argument == "share" then
        if not ns.GuideInteger(mapID) or mapID <= 0 then ns.Print("Current map unavailable."); return end
        local count = ns.ShareTrails(mapID, true)
        ns.Print(count > 0 and (count .. " ground message(s) queued for your party from " .. ns.MapName(mapID) .. ".")
            or "Nothing to share: no recorded ground here, sharing off, or not in a party.")
    elseif argument == "on" or argument == "off" then
        ns.SetOption("learnRoads", argument == "on")
        ns.Print("Road learning " .. argument .. ".")
    else
        local lines = {}
        ns.TravelTrailDiagnostics(function(line) lines[#lines + 1] = line end)
        for _, line in ipairs(lines) do ns.Print(line) end
        ns.Print("Commands: /wt roads export • /wt roads share • /wt roads clear • /wt roads clear all • /wt roads on|off")
    end
end
