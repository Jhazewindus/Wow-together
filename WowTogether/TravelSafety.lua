local addonName, ns = ...

local MARGIN = 100 -- Estimated game yards around published occupied locations.
local function number(value)
    return ns.Public(value) and type(value) == "number" and value == value and math.abs(value) < 1000000
end
local function point(p)
    return ns.Public(p) and type(p) == "table" and ns.GuideInteger(p.mapID) and p.mapID > 0
        and number(p.x) and number(p.y)
end
local function inside(p, area)
    return p.x >= area.minX and p.x <= area.maxX and p.y >= area.minY and p.y <= area.maxY
end

local function crossesOnMap(a, b, mapID, context, allowDeparture, allowArrival)
    local areas = context.areas[mapID]
    if not areas then return end
    local p = a.mapID == mapID and a or ns.ProjectMapPoint(a, mapID, context.projection)
    local q = b.mapID == mapID and b or ns.ProjectMapPoint(b, mapID, context.projection)
    if not p or not q then return end
    for _, area in ipairs(areas) do
        if not (allowDeparture and inside(p, area) and not inside(q, area))
            and not (allowArrival and inside(q, area)) then
            local low, high = 0, 1
            local delta, lo, hi = q.x - p.x, area.minX, area.maxX
            if delta == 0 then
                if p.x < lo or p.x > hi then high = -1 end
            else
                local first, last = (lo - p.x) / delta, (hi - p.x) / delta
                if first > last then first, last = last, first end
                low, high = math.max(low, first), math.min(high, last)
            end
            if low <= high then
                delta, lo, hi = q.y - p.y, area.minY, area.maxY
                if delta == 0 then
                    if p.y < lo or p.y > hi then high = -1 end
                else
                    local first, last = (lo - p.y) / delta, (hi - p.y) / delta
                    if first > last then first, last = last, first end
                    low, high = math.max(low, first), math.min(high, last)
                end
            end
            if low <= high then return area end
        end
    end
end

function ns.TravelSafetyContext()
    local context = {areas = {}, projection = {}, faction = ns.profile and ns.SafeTitle(ns.profile.faction)}
    if context.faction ~= "Horde" and context.faction ~= "Alliance" then return context end
    local scales = {}
    for _, source in ipairs(ns.travelData and ns.travelData.settlements or {}) do
        if (source.faction == "Horde" or source.faction == "Alliance") and source.faction ~= context.faction
            and ns.GuideInteger(source.mapID) and source.mapID > 0 and ns.SafeTitle(source.name)
            and number(source.minX) and number(source.maxX) and number(source.minY) and number(source.maxY)
            and source.minX <= source.maxX and source.minY <= source.maxY then
            local scale = scales[source.mapID]
            if not scale then
                local w, h
                if C_Map then w, h = ns.ReadPublic(C_Map.GetMapWorldSize, source.mapID) end
                scale = {number(w) and w > 0 and MARGIN / w or 0, number(h) and h > 0 and MARGIN / h or 0}
                scales[source.mapID] = scale
            end
            local area = {name = source.name, faction = source.faction, mapID = source.mapID,
                minX = source.minX - scale[1], maxX = source.maxX + scale[1],
                minY = source.minY - scale[2], maxY = source.maxY + scale[2]}
            context.areas[source.mapID] = context.areas[source.mapID] or {}
            table.insert(context.areas[source.mapID], area)
        end
    end
    return context
end

function ns.HostileTravelArea(p, context)
    if not point(p) then return end
    context = context or ns.TravelSafetyContext()
    for _, area in ipairs(context.areas[p.mapID] or {}) do if inside(p, area) then return area end end
end

-- Exact segment/rectangle intersection over the approximate source footprint.
-- Projection uses public map/world transforms; normalized maps are not mixed.
function ns.HostileWalkCrossing(a, b, context, allowDeparture, allowArrival)
    if not point(a) or not point(b) then return end
    context = context or ns.TravelSafetyContext()
    local area = crossesOnMap(a, b, a.mapID, context, allowDeparture, allowArrival)
    if area then return area end
    if b.mapID ~= a.mapID then return crossesOnMap(a, b, b.mapID, context, allowDeparture, allowArrival) end
end

function ns.TravelNodeAllowed(id, p, owned, context)
    local faction = context and context.faction or ns.profile and ns.SafeTitle(ns.profile.faction)
    local taxi = tonumber(string.match(id, "^TAXI_(%d+)$"))
    local metadata = taxi and ns.guideServiceData and ns.guideServiceData.taxis and ns.guideServiceData.taxis[taxi]
    local published = ns.travelData and ns.travelData.nodes[id]
    for _, value in ipairs({p or {}, owned or {}, published or {}, metadata or {}}) do
        local owner = ns.SafeTitle(value.faction)
        if owner and owner ~= "Both" and owner ~= faction then return false end
    end
    return not ns.HostileTravelArea(p, context)
end
