local addonName, ns = ...

-- Reuse the published travel graph for complete-guide comparisons. Personal
-- flights/hearths/mounts never enter a generic plan. Local attachments and
-- uncovered roads remain estimates; transport weights are published estimates.
function ns.NewFixedTravelCost(fallback, cooperative, onYield, options)
    local policy = {faction = ns.profile and ns.profile.faction, safety = ns.TravelSafetyContext(),
        terrain = options and options.terrain == false and {maps = {}, projection = {}}
            or ns.TravelTerrainContext(), metrics = {}, nodes = {}}
    local nearest, memo, count, nearestCount = {}, {}, 0, 0
    local work = 0
    local function tick()
        work = work + 1
        if cooperative and work % 100 == 0 then coroutine.yield(); if onYield then onYield() end end
    end
    policy.tick = tick
    local maps = {}
    local function add(id, point)
        if ns.ValidTravelPoint(point) and ns.TravelNodeAllowed(id, point, nil, policy.safety) then
            policy.nodes[id] = point
            if point.container and (string.find(point.container, "wizards_sanctum", 1, true)
                or string.find(point.container, "blackrock_mountain", 1, true)) then return end
            maps[point.mapID] = maps[point.mapID] or {}
            maps[point.mapID][#maps[point.mapID] + 1] = {id = id, point = point}
        end
    end
    for id, point in pairs(ns.travelData and ns.travelData.nodes or {}) do add(id, point) end
    for _, map in pairs(policy.terrain.maps) do
        for id, point in pairs(map.nodes) do add(id, point) end
    end
    for _, list in pairs(maps) do table.sort(list, function(a, b) return a.id < b.id end) end
    local function anchors(point)
        if nearest[point] then return nearest[point] end
        local result = {}
        for _, node in ipairs(maps[point.mapID] or {}) do
            if not ns.HostileWalkCrossing(point, node.point, policy.safety, true, false)
                and not ns.TerrainWalkCrossing(point, node.point, policy.terrain) then
                local length = fallback(point, node.point)
                if length <= 1500 then
                    local cost = length * 1.25
                    local index = #result + 1
                    -- Retain the established seed's prices only when explicitly
                    -- requested. Corrected comparisons use one scale throughout.
                    local rank = options and options.legacyAnchorOrder and length or cost
                    for i, old in ipairs(result) do if rank < old.cost then index = i; break end end
                    table.insert(result, index, {id = node.id, cost = cost})
                    if #result > 3 then table.remove(result) end
                end
            end
            tick()
        end
        if nearestCount >= 2048 then nearest, nearestCount = {}, 0 end
        nearest[point], nearestCount = result, nearestCount + 1
        return result
    end
    local function distance(a, b)
        if a and a.unknownLocation or b.unknownLocation or not ns.ValidTravelPoint(a) or not ns.ValidTravelPoint(b) then
            return fallback(a, b), "unmapped-estimate"
        end
        if memo[a] and memo[a][b] then return unpack(memo[a][b]) end
        local sameMap = a.mapID == b.mapID
        local direct = fallback(a, b)
        local blocked = ns.HostileWalkCrossing(a, b, policy.safety, true, true)
            or ns.TerrainWalkCrossing(a, b, policy.terrain)
        local best, basis
        if sameMap and not blocked and direct <= 400 then best, basis = direct, "local-estimate"
        else
            for _, from in ipairs(anchors(a)) do
                for _, to in ipairs(anchors(b)) do
                    local road = ns.PublishedTravelDistance(from.id, to.id, policy)
                    local value = road and from.cost + road + to.cost
                    if value and (not best or value < best) then best, basis = value, "network-estimate" end
                end
            end
            if sameMap and not blocked and best then best = math.max(best, direct) end
        end
        if not best then best, basis = math.max(direct, blocked and 20000 or 0), blocked and "blocked" or "unmapped-estimate" end
        if count >= 4096 then memo, count = {}, 0 end
        memo[a] = memo[a] or {}; memo[a][b] = {best, basis}; count = count + 1
        return best, basis
    end
    local function reset(checkpoint)
        -- Published graph/profile/guide points are the compilation snapshot.
        -- Both caches have fixed limits above, so keep repeated attachments
        -- and leg costs across loading frames. Explicit reset() still clears
        -- them; world-projection scratch data is released at each checkpoint.
        if checkpoint then
            policy.metrics, policy.safety.projection, policy.terrain.projection = {}, {}, {}
            return
        end
        nearest, memo, count, nearestCount = {}, {}, 0, 0
        policy.metrics, policy.safety.projection, policy.terrain.projection = {}, {}, {}
    end
    return distance, reset
end
