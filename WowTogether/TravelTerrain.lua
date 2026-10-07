local addonName, ns = ...

-- A small visibility graph around mapped, convex terrain footprints. These
-- are map estimates, not a navmesh. Unknown ground remains unknown. Shared by
-- the arrow and map; it never changes quest steps or completion credit.
local cached, EPSILON = {}, 0.000000001
local function mapPoint(p)
    return ns.Public(p) and type(p) == "table" and ns.GuideInteger(p.mapID) and p.mapID > 0
        and ns.Public(p.x) and ns.Public(p.y) and type(p.x) == "number" and type(p.y) == "number"
        and p.x == p.x and p.y == p.y and math.abs(p.x) < 1000000 and math.abs(p.y) < 1000000
end
local function cross(a, b, p)
    return (b.x - a.x) * (p.y - a.y) - (b.y - a.y) * (p.x - a.x)
end
local function inside(p, area)
    if p.mapID ~= area.mapID then return false end
    for i, a in ipairs(area.polygon) do
        if cross(a, area.polygon[i % #area.polygon + 1], p) * area.sign <= EPSILON then return false end
    end
    return true
end
local function intersection(a, b, area)
    local low, high = 0, 1
    for i, p in ipairs(area.polygon) do
        local q = area.polygon[i % #area.polygon + 1]
        local first, last = cross(p, q, a) * area.sign, cross(p, q, b) * area.sign
        local delta = last - first
        if math.abs(delta) <= EPSILON then
            if first <= EPSILON then return false end
        else
            local t = (EPSILON - first) / delta
            if delta > 0 then low = math.max(low, t) else high = math.min(high, t) end
            if low >= high then return false end
        end
    end
    return low < high and high > EPSILON and low < 1 - EPSILON
end

local function compile(mapID, source)
    local result = {areas = {}, nodes = {}, edges = {}}
    local padding = type(source.padding) == "number" and math.max(0.001, math.min(0.02, source.padding)) or 0.005
    for index, row in ipairs(source.obstacles or {}) do
        local polygon, cx, cy, sign, valid = {}, 0, 0, nil, true
        for _, pair in ipairs(row.polygon or {}) do
            local p = {mapID = mapID, x = pair[1], y = pair[2]}
            if not ns.ValidTravelPoint(p) then valid = false; break end
            polygon[#polygon + 1], cx, cy = p, cx + p.x, cy + p.y
        end
        if valid and #polygon >= 3 and #polygon <= 16 then
            for i, a in ipairs(polygon) do
                local turn = cross(a, polygon[i % #polygon + 1], polygon[(i + 1) % #polygon + 1])
                if math.abs(turn) <= EPSILON or sign and sign * turn <= 0 then valid = false; break end
                sign = turn > 0 and 1 or -1
            end
        else valid = false end
        if valid then
            local area = {mapID = mapID, polygon = polygon, sign = sign,
                name = ns.SafeTitle(row.name) or "the ridge", elevated = row.elevated == true}
            result.areas[#result.areas + 1] = area
            cx, cy = cx / #polygon, cy / #polygon
            for i, p in ipairs(polygon) do
                local dx, dy = p.x - cx, p.y - cy
                local length = math.sqrt(dx * dx + dy * dy)
                local node = {mapID = mapID, x = p.x + dx / length * padding,
                    y = p.y + dy / length * padding, terrain = area, name = "Valley waypoint"}
                if ns.ValidTravelPoint(node) then result.nodes["TERRAIN_" .. mapID .. "_" .. index .. "_" .. i] = node end
            end
        end
    end
    local ids = {}; for id in pairs(result.nodes) do ids[#ids + 1] = id end; table.sort(ids)
    for i, id in ipairs(ids) do
        for j = i + 1, #ids do
            local a, b, blocked = result.nodes[id], result.nodes[ids[j]], false
            for _, area in ipairs(result.areas) do
                if intersection(a, b, area) then blocked = true; break end
            end
            if not blocked then result.edges[#result.edges + 1] = {from = id, to = ids[j]} end
        end
    end
    return result
end

function ns.TravelTerrainContext()
    local data = ns.travelTerrainData
    if cached.data ~= data then
        cached = {data = data, maps = {}}
        for mapID, source in pairs(data and data.maps or {}) do
            if ns.GuideInteger(mapID) and mapID > 0 then cached.maps[mapID] = compile(mapID, source) end
        end
    end
    -- Public coordinate transforms belong to this read, never a previous
    -- combat state or map layout. Static polygon visibility alone is cached.
    return {maps = cached.maps, projection = {}}
end

function ns.TerrainTravelArea(p, context)
    if not ns.ValidTravelPoint(p) then return end
    context = context or ns.TravelTerrainContext()
    local map = context.maps[p.mapID]
    for _, area in ipairs(map and map.areas or {}) do if inside(p, area) then return area end end
end

function ns.TerrainWalkCrossing(a, b, context)
    if not mapPoint(a) or not mapPoint(b) then return end
    context = context or ns.TravelTerrainContext()
    local maps = {a.mapID}; if b.mapID ~= a.mapID then maps[2] = b.mapID end
    for _, mapID in ipairs(maps) do
        local map = context.maps[mapID]
        if map then
            local p = ns.ProjectMapPoint(a, mapID, context.projection)
            local q = ns.ProjectMapPoint(b, mapID, context.projection)
            if p and q then
                for _, area in ipairs(map.areas) do
                    -- An endpoint atop a mesa needs a ramp/lift approach.
                    -- Don't invent that approach from a 2D map silhouette.
                    if not (inside(p, area) and inside(q, area)) and intersection(p, q, area) then return area end
                end
            end
        end
    end
end

function ns.TravelSegmentDistance(p, a, b)
    if not ns.ValidTravelPoint(p) or not ns.ValidTravelPoint(a) or not ns.ValidTravelPoint(b)
        or p.mapID ~= a.mapID or a.mapID ~= b.mapID then return end
    local w, h
    if C_Map then w, h = ns.ReadPublic(C_Map.GetMapWorldSize, p.mapID) end
    if not ns.Public(w) or not ns.Public(h) or type(w) ~= "number" or type(h) ~= "number"
        or w <= 0 or h <= 0 or w >= 1000000 or h >= 1000000 or w ~= w or h ~= h then return end
    local dx, dy = (b.x - a.x) * w, (b.y - a.y) * h
    local px, py = (p.x - a.x) * w, (p.y - a.y) * h
    local square = dx * dx + dy * dy
    local t = square > 0 and math.max(0, math.min(1, (px * dx + py * dy) / square)) or 0
    return math.sqrt((px - t * dx)^2 + (py - t * dy)^2), t
end
